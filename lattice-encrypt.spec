# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Runner.py'],
    pathex=[],
    binaries=[],
    datas=[('reglas', 'reglas'), ('core', 'core'), ('lattice.le', '.'), ('cifrado.le', '.')],
    hiddenimports=['reglas.ReglasBase', 'reglas.ReglasRuido', 'reglas.ReglasTexto', 'reglas.ReglasLattice', 'reglas.ReglasAritmetica', 'reglas.ReglasComparacion', 'core.cripto.frodo', 'core.cripto.mlkem', 'core.cripto.valores'],
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
    name='lattice-encrypt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
