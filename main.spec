# -*- mode: python ; coding: utf-8 -*-

import os
import re
from subprocess import call

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
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'requests', 'cryptography.fernet', 
                'asyncio', 'aiohttp', 'pandas', 'numpy', 'openpyxl', 'python-dotenv',
                'multidict', 'yarl', 'aiosignal', 'frozenlist', 'charset_normalizer', 'attrs'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'distutils'],
    noarchive=False,
    optimize=2,
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
    strip=True,
    upx=True,
    upx_exclude=['PyQt6', 'cryptography'],
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
        'NSMainNibFile': '',
        'NSSupportsAutomaticTermination': False,
        'NSHumanReadableCopyright': f' 2024 DellIDRACMonitor {VERSION}',
        'CFBundleDocumentTypes': [],
        'CFBundleURLTypes': [],
        'LSMultipleInstancesProhibited': True,
    }
)

# 현재 작업 디렉토리와 dist 폴더 경로 설정
current_dir = os.getcwd()
dist_dir = os.path.join(current_dir, 'dist')

# DMG 파일 경로 지정
dmg_path = os.path.join(dist_dir, 'DellIDRACMonitor.dmg')
app_path = os.path.join(dist_dir, 'DellIDRACMonitor.app')

# 기존 DMG 파일이 있다면 제거
if os.path.exists(dmg_path):
    os.remove(dmg_path)

# DMG 생성
call([
    'create-dmg',
    '--volname', 'DellIDRACMonitor',
    '--window-pos', '200', '120',
    '--window-size', '600', '300',
    '--icon-size', '100',
    '--icon', 'DellIDRACMonitor.app', '175', '120',
    '--hide-extension', 'DellIDRACMonitor.app',
    '--app-drop-link', '425', '120',
    dmg_path,
    app_path
])

# DMG 파일이 생성되면 자동으로 언마운트
if os.path.exists(dmg_path):
    call(['hdiutil', 'detach', '/Volumes/DellIDRACMonitor', '-force'])