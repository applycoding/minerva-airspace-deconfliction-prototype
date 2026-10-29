import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='MINERVA simulation prototype')
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--gui-smoke', action='store_true')
    parser.add_argument('--marker-file', type=Path)
    parser.add_argument('--run-test-rig', action='store_true')
    parser.add_argument('--run-trl5', action='store_true')
    parser.add_argument('--scenarios', help='Comma-separated scenario IDs, for example S1,S3')
    parser.add_argument('--require-sitl', action='store_true')
    parser.add_argument('--sitl-dir', type=Path)
    parser.add_argument('--report-dir', type=Path, default=Path('reports'))
    args = parser.parse_args()
    if args.run_trl5:
        from minerva.trl5.runner import run_campaign
        return run_campaign(args.report_dir,args.scenarios.split(',') if args.scenarios else None,args.require_sitl,args.sitl_dir)
    if args.self_check:
        from minerva.test_rig.runner import self_check
        return self_check()
    if args.run_test_rig:
        from minerva.test_rig.runner import run_test_rig
        return run_test_rig(args.report_dir)
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
                args.marker_file.write_text('MINERVA GUI smoke passed\n', encoding='utf-8')
            app.quit()
        QTimer.singleShot(2000, finish)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
