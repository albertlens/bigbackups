# -*- mode: python ; coding: utf-8 -*-
"""
Archivo de especificación para PyInstaller
Genera BigBackups.exe standalone
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Recoger datos de customtkinter
ctk_datas = collect_data_files('customtkinter')

# Assets de la aplicación (logo e icono)
app_assets = [
    ('assets/logo.png', 'assets'),
    ('assets/icon.png', 'assets'),
    ('assets/icon.ico', 'assets'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=ctk_datas + app_assets,
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'setuptools',
    ],
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
    name='BigBackups',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sin consola, solo GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # Icono del EXE
    version=None,  # Puedes agregar info de versión
)
