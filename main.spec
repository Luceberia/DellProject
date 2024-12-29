# -*- mode: python ; coding: utf-8 -*-

import os

VERSION = '1.0.0'

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
    bundle_identifier='com.yourcompany.DellIDRACMonitor',  # 고유 번들 식별자
    version=VERSION,
    info_plist={
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        # 필요한 권한 설정
        'NSAppleEventsUsageDescription': '앱 업데이트를 위해 관리자 권한이 필요합니다.',
        'NSSystemAdministrationUsageDescription': '시스템 관리 작업을 수행하기 위해 권한이 필요합니다.',
        # 앱 실행 권한 설정
        'LSUIElement': False,  # Dock에 아이콘 표시
        'LSBackgroundOnly': False,  # 백그라운드 전용 여부
    }
)