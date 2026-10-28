import sys
from pathlib import Path


def data_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2])) / 'data'
