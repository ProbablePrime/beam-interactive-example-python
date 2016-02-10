import asyncio
from requests import Session
from beam_interactive import start
from beam_interactive import proto
from random import random

path = "https://beam.pro/api/v1"
auth = {
    "username": "ProbablePrime",
    "password": ""
}

class AuthenticationException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

game_version = 329
share_code = 'ni8cdqmo'

def login(session, username, password):
    """Log into the Beam servers via the API."""
    auth = dict(username=username, password=password)
    return session.post(path + "/users/login", auth).json()

def get_tetris(session, channel):
    """Retrieve interactive connection information."""
    return session.get(path + "/tetris/{id}/robot".format(id=channel)).json()

def go_interactive(session, channel_id, version, code):
    interactiveDetails=dict(tetrisGameId=version, tetrisShareCode=code, interactive=1)
    return session.put(path + "/channels/{id}".format(id=channel_id), interactiveDetails).json()

def get_controls(session, channel_id):
    return session.get(path + "/tetris/{id}".format(id=channel_id)).json()

def on_handshake(line, conn):
    print("Shaking hands")

def on_handshake_ack(line, conn):
    print("Shaken hands")

def on_error(error, conn):
    """This is called when we get an Error packet. It contains
    a single attribute, 'message'.
    """
    print('Oh no, there was an error!')
    print(error.message)

def on_report(report, conn):
    """Periodically we'll get Report packets to let us know
    what our viewers are up to. We'll just print out that
    report, then send back a random progress update.

    The progress update, described in more details in the Talking
    to Beam Interactive section, updates the frontend with feedback
    about what the robot is doing. In this case, we'll hint that
    we're a random percentage of the way towards the up arrow
    button (code ) being fired.
    """
    print('We got a report:')
    print(report)

    #I haven't figured out the new progress reports in python yet
    # See the following link for working with protocol buffers in Python:
    # https://developers.google.com/protocol-buffers/docs/pythontutorial
    # update = proto.ProgressUpdate()
    # prog = update.progress.add()
    # prog.target = prog.TACTILE
    # prog.code = 38
    # prog.progress = random()

    # conn.send(update)


loop = asyncio.get_event_loop()


@asyncio.coroutine
def connect():
    # Initialize session, authenticate to Beam servers, and retrieve Tetris
    # address and key.
    session = Session()
    channel_data = login(session, **auth)
    if not "channel" in channel_data:
        raise AuthenticationException("Incorrect username or password")
    channel_id = channel_data["channel"]["id"]

    data = get_tetris(session, channel_id)

    interactiveData = go_interactive(session, channel_id, game_version, share_code)

    controls = get_controls(session, channel_id)
    tactiles = controls["version"]["controls"]["tactiles"]

    for tactile in tactiles:
        print("ID {} is key {}".format(tactile["id"],tactile["key"]))

    # start() takes the remote address of Beam Interactive, the channel
    # ID, and channel the auth key. This information can be obtained
    # via the backend API, which is documented at:
    # https://developer.beam.pro/api/v1/
    conn = yield from start(data['address'], channel_id, data['key'], loop)

    handlers = {
        proto.id.error: on_error,
        proto.id.report: on_report,
        proto.id.handshake: on_handshake,
        proto.id.handshake_ack: on_handshake_ack
    }

    # wait_message is a coroutine that will return True when we get
    # a complete message from Beam Interactive, or False if we
    # got disconnected.
    while (yield from conn.wait_message()):
        decoded, packet_bytes = conn.get_packet()
        packet_id = proto.id.get_packet_id(decoded)
        
        if decoded is None:
            print('We got a bunch of unknown bytes.')
        elif packet_id in handlers:
            handlers[packet_id](decoded, conn)
        else:
            print("We got packet {} but didn't handle it!".format(packet_id))
    print("Closing")
    conn.close()
try:
    loop.run_until_complete(connect())
except KeyboardInterrupt:
    print("Disconnected.")
finally:
    loop.close()
