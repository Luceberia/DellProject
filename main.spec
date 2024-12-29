# -*- mode: python ; coding: utf-8 -*-

import os
import re

def get_version():
    with open('version.py', 'r', encoding='utf-8') as f:
        content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
    return '0.0.0'

VERSION = get_version()

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
    bundle_identifier='com.yourcompany.DellIDRACMonitor',
    version=VERSION,
    info_plist={
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSAppleEventsUsageDescription': '앱 업데이트 및 시스템 관리를 위해 권한이 필요합니다.',
        'NSSystemAdministrationUsageDescription': '시스템 모니터링을 위해 관리자 권한이 필요합니다.',
        'LSUIElement': False,
        'LSBackgroundOnly': False,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDisplayName': 'DellIDRACMonitor',
        'CFBundleName': 'DellIDRACMonitor',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        # 추가할 설정
        'NSMainNibFile': '',  # 메인 nib 파일 없음을 명시
        'NSSupportsAutomaticTermination': False,  # 자동 종료 비활성화
        'NSHumanReadableCopyright': f'© 2024 DellIDRACMonitor {VERSION}',  # 저작권 정보
        'CFBundleDocumentTypes': [],  # 문서 타입 명시
        'CFBundleURLTypes': []  # URL 스킴 명시
    }
)