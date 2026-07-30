"""
Первый скрипт модуля: подтверждает, что Python установлен и запускается
из текущей рабочей папки. Не читает и не пишет никаких файлов датасета —
задача этого скрипта только показать, что "запустить готовый скрипт"
(умение I2) вообще работает на вашей машине, прежде чем переходить к
скриптам, которые открывают orders_log.csv.

Пример:
  python3 check_env.py
  python3 check_env.py --name Danylo
"""

import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None, help="если указано, скрипт напечатает приветствие с этим именем")
    args = ap.parse_args()

    # ASCII-вывод: M0/M1 на латинице по решению 17.
    print(f"python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"cwd: {os.getcwd()}")
    if args.name:
        print(f"hello, {args.name}")


if __name__ == "__main__":
    main()
