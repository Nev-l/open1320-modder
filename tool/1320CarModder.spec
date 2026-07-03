# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['car_modder.py'],
    pathex=[],
    binaries=[],
    datas=[('swf_utils.py', '.'), ('color_utils.py', '.')],
    hiddenimports=['PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageEnhance', 'numpy',
                   'swf_utils', 'color_utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='1320CarModder',
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
)
