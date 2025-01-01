# -*- mode: python ; coding: utf-8 -*-

import os
import re
import certifi
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
    binaries=[
        ('/Users/kimnamjun/.pyenv/versions/3.12.8/lib/libpython3.12.dylib', './Contents/Frameworks')
    ],
    datas=[
        (certifi.where(), 'certifi'),
        ('version.py', '.'),
        ('common', 'common'),
        ('config', 'config'),
        ('endpoints', 'endpoints'),
        ('error', 'error'),
        ('icon', 'icon'),
        ('managers', 'managers'),
        ('network', 'network'),
        ('ui', 'ui'),
        ('utils', 'utils'),
        ('updater.py', '.'),
        ('main.py', '.'),
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'requests', 
        'PyQt6', 
        'python-dotenv', 
        'pandas', 
        'cryptography',
        'aiohttp', 
        'openpyxl', 
        'numpy', 
        'jinja2', 
        'PyQt6.QtCore', 
        'PyQt6.QtWidgets',
        'PyQt6.QtGui', 
        'cryptography.fernet',
        'logging.handlers',
        'common.cache.cache_manager',
        'common.data.data_processor',
        'common.hardware.hardware_info',
        'config.data.data_config',
        'config.data.models',
        'config.server.dell_config',
        'config.server.server_config',
        'config.system.app_config',
        'config.system.log_config',
        'endpoints.redfish_endpoints',
        'error.error_handler',
        'managers.dell_server_manager',
        'network.connection_manager',
        'ui.components.hardware_section',
        'ui.components.monitor_section',
        'ui.components.server_section',
        'ui.components.settings_dialog',
        'ui.components.update_dialog',
        'ui.components.popups.detail_dialog',
        'ui.components.popups.error_dialog',
        'ui.components.popups.help_dialog',
        'ui.components.popups.system_event_popup',
        'ui.main_window',
        'utils.async_utils',
        'utils.config_utils',
        'utils.server_utils',
        'utils.ssh_utils',
        'utils.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DellIDRACMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    runtime_tmpdir=None,
    codesign_flags=[],
    rpath=['@executable_path/../Frameworks'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DellIDRACMonitor'
)

app = BUNDLE(
    coll,
    name='DellIDRACMonitor.app',
    icon=None,
    bundle_identifier='com.yourcompany.DellIDRACMonitor',
    version=VERSION,
    info_plist={
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'LSMinimumSystemVersion': '10.15.0',
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
        'NSHumanReadableCopyright': f'© 2024 DellIDRACMonitor {VERSION}',
        'CFBundleDocumentTypes': [],
        'CFBundleURLTypes': [],
        'LSMultipleInstancesProhibited': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'LSEnvironment': {
            'MallocNanoZone': '0'
        },
        'DTSDKName': 'macosx11.3',
        'disable_windowed_traceback': True,
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