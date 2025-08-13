# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['miner_detector_gui.py'],
    pathex=['/workspace'],
    binaries=[],
    datas=[
        ('*.ttf', '.'),  # Include all font files
        ('*.html', '.'), # Include HTML files
        ('.env', '.') if os.path.exists('.env') else None,
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtWebEngineWidgets',
        'sklearn.ensemble',
        'sklearn.model_selection',
        'rtlsdr',
        'serial',
        'flask',
        'flask_socketio',
        'paho.mqtt.client',
        'telegram',
        'scapy.all',
        'win32com.client',
        'geoip2.database',
        'whois',
        'folium',
        'cryptography.fernet',
        'aiocoap',
        'httpx'
    ],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MinerDetector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI application
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path if you have one
)

# For creating a directory distribution instead of a single file
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='MinerDetector'
# )