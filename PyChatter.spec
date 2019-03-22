# -*- mode: python -*-

block_cipher = None


a = Analysis(['PyChatter.py'],
             pathex=['C:\\Users\\AIR41604\\Desktop\\Thomas Michiels\\mixitupbot_scripting_interface'],
             binaries=[],
             datas=[('.\\venv\\Lib\\site-packages\\_sounddevice_data\\portaudio-binaries\\libportaudio64bit.dll', '\\_sounddevice_data\\portaudio-binaries'), ('.\\venv\\Lib\\site-packages\\_soundfile_data\\libsndfile64bit.dll', '_soundfile_data'), ('clr.py', '.'), ('README.md', '.'), ('data/script_interface.key', 'data'), ('data/script_interface.crt', 'data')],
             hiddenimports=['sqlite3'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [('v', None, 'OPTION')],
          name='PyChatter',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
