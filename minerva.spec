from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'src/minerva/__main__.py')],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=[(str(root / 'data'), 'data'),
           (str(root / 'THIRD_PARTY_LICENSES'), 'THIRD_PARTY_LICENSES'),
           (str(root / 'LICENSE'), '.'), (str(root / 'NOTICE.md'), '.'),
           (str(root / 'src/minerva/schema.sql'), 'minerva')]
          + collect_data_files('pyproj'),
    hiddenimports=['minerva.gui.map_canvas', 'minerva.gui.plan_editor', 'minerva.gui.conflict_panel', 'minerva.gui.live_panel', 'minerva.live', 'minerva.test_rig.sim',
                   'minerva.trl5.runner', 'minerva.trl5.gui_driver', 'minerva.trl5.scenarios', 'minerva.trl5.oracle_audit', 'minerva.trl5.report_writer', 'minerva.trl5.sitl_harness'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['pymavlink'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='minerva',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='minerva')
