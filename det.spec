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
