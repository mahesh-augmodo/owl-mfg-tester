# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ( 'resources', 'resources' ),
    ( 'config', 'config' ),
    ( 'locale', 'locale' ),
    ( 'platform_utils', 'platform_utils')
]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- CHANGES START HERE ---
# 1. We removed exclude_binaries=True
# 2. We added a.binaries, a.zipfiles, and a.datas directly into EXE
# 3. We removed the COLLECT block completely

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='owl_mfg_tester',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources\\OwlCheckIcon.ico'
)