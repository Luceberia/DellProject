# -*- mode: python ; coding: utf-8 -*-

import os

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('version.py', '.'),
        ('common', 'common'),
        ('config', 'config'),
        ('dell_logging', 'dell_logging'),
        ('endpoints', 'endpoints'),
        ('error', 'error'),
        ('icon', 'icon'),
        ('managers', 'managers'),
        ('network', 'network'),
        ('ui', 'ui'),
        ('utils', 'utils'),
        ('updater.py', '.'),
        ('main.py', '.'),
    ],
    hiddenimports=['requests', 'PyQt6', 'python-dotenv', 'pandas', 'cryptography', 
                'aiohttp', 'openpyxl', 'numpy', 'jinja2', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 
                'PyQt6.QtGui', 'cryptography.fernet'],
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
    name='DellIDRACMonitor',
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

app = BUNDLE(
    exe,
    name='DellIDRACMonitor.app',
    icon=None,
    bundle_identifier=None,
)
