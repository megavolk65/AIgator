# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for AI Helper
Build with: pyinstaller build.spec
"""

import os

# Пути
block_cipher = None
ROOT_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('config.py', '.'),
        ('version.py', '.'),
        ('settings.default.json', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'keyboard',
        'win32gui',
        'win32process',
        'psutil',
        'mss',
        'PIL',
        'requests',
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
    name='AI Helper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Без консольного окна
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists(os.path.join(ROOT_DIR, 'assets', 'icon.ico')) else None,
)
