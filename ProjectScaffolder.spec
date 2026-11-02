# -*- mode: python ; coding: utf-8 -*-
import PyInstaller.config

# Keine Nachfrage beim Überschreiben bestehender Builds
PyInstaller.config.CONF['noconfirm'] = True

a = Analysis(
    ['src/py_project_init/ui/main_window.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('assets', 'assets'),
        ('hooks', 'hooks'),
    ],
    hiddenimports=['keyring.backends.Windows'],
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
    name='ProjectScaffolder',
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
