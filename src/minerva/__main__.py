import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='MINERVA simulation prototype')
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--gui-smoke', action='store_true')
    parser.add_argument('--marker-file', type=Path)
    parser.add_argument('--run-test-rig', action='store_true')
    parser.add_argument('--report-dir', type=Path, default=Path('reports'))
    args = parser.parse_args()
    if args.self_check:
        from minerva.test_rig.runner import self_check
        return self_check()
    if args.run_test_rig:
        parser.error('Full T1–T7 test rig is scheduled for Slice 11; only --self-check is available')
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from minerva.gui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    if args.gui_smoke:
        def finish():
            if args.marker_file:
                args.marker_file.parent.mkdir(parents=True, exist_ok=True)
                args.marker_file.write_text('MINERVA GUI smoke passed\n')
            app.quit()
        QTimer.singleShot(2000, finish)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
