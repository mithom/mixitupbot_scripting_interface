# -*- mode: python -*-

block_cipher = None


a = Analysis(['PyChatter.py'],
             pathex=['C:\\Users\\AIR41604\\Desktop\\Thomas Michiels\\mixitupbot_scripting_interface'],
             binaries=[],
             datas=[('README.md', '.'), ('data/script_interface.key', 'data'), ('data/script_interface.crt', 'data')],
             hiddenimports=[],
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
