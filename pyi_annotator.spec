# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['starter.py'],
             pathex=[],
             binaries=[],
             datas=[('templates', 'templates')],
             hiddenimports=['flask'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='annotator',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
app = BUNDLE(exe,
             name='annotator.app',
             icon=None,
             bundle_identifier=None)

# Only x86_64 app will be built for macOS since rosetta2 is equipped on M1 chip macOS.
# This is too avoid the case that some packages only support x86_64 and fail to run on arm64.
# https://pyinstaller.readthedocs.io/en/stable/feature-notes.html#macos-multi-arch-support
