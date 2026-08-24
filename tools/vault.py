"""Турникет с журналом для закрытых наборов и решений (решение 51).

**Что это и чем это не является.** Это не сейф. Ключ лежит в этом же
репозитории, и человек, прочитавший тридцать строк ниже, откроет любой
файл руками за минуту. Это турникет: пройти можно только через него, и
проход записывается. Разница между «сверился после попытки» и
«подсмотрел вместо неё» после этого перестаёт быть вопросом памяти —
она становится строкой в `research/attempts.md` с датой.

Задача, которую турникет решает, — дефект CG-4 внешнего аудита
`audit/independent-audit-2026-08-24.md`: «эталонные ответы содержат
решения и открыты до попытки». Единственный студент программы учится
один, без ментора и без внешней отчётности; программа при этом целиком
построена на механической проверяемости — и ровно там, где она решает,
её не было.

**Что закрывается и что остаётся открытым.**

| Остаётся открытым | Закрывается |
|---|---|
| `ref_*.csv` — ожидаемый вывод, без него не работает `compare_csv.py` | решения: запросы и код, которыми этот вывод получен |
| числа в разделе 1.5 каждого шага — эталон, порог, допуск | закрытые наборы: `exam.py`, банки вопросов, ключ разметки вакансий |
| контрольные точки датасета (sha256, число строк) | разобранные ответы на ловушки и доменные вопросы |

Правило деления простое: **ожидаемый результат открыт всегда, способ его
получить — после попытки.**

**Шифр.** Ключ выводится из соли репозитория и имени файла через
`hashlib.scrypt`, гамма — из `hashlib.shake_256`, наложение — XOR. Это
настоящий поточный шифр, а не base64: без ключа содержимое не читается
ни глазами, ни поиском по репозиторию, и `git grep` по ответу ничего не
находит. Стойкость к тому, кто читает этот файл, не заявляется и не
нужна.

Команды:

    python tools\\vault.py list
    python tools\\vault.py lock   <путь>            # положить в турникет
    python tools\\vault.py open   <путь> --attempt <файл своей попытки>
    python tools\\vault.py status <путь>

`open` отказывает, если файла попытки нет или он короче 40 значащих
символов: смотреть решение, ничего не написав, — ровно то, что турникет
и должен остановить. После проверки он дописывает строку в
`research/attempts.md` и печатает содержимое в консоль, не создавая
расшифрованного файла на диске.

**Исключение `--to` (решение 53).** Эталон, который читает не человек, а
скрипт, в консоли бесполезен: `compare_csv.py` сверяет файл с файлом.
Для таких случаев `--to` записывает содержимое по указанному пути после
той же проверки попытки и той же записи в журнал. Каталоги `unlocked/`
внесены в `.gitignore`: расшифрованный эталон живёт на диске одного
человека и в репозиторий не попадает.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "research" / "attempts.md"

# Соль репозитория. Публичная по устройству: см. докстроку — это турникет,
# а не сейф. Меняется только вместе с перешифровкой всех .enc.
SALT = b"data-analyst-program/2026-08-24/vault"
MIN_ATTEMPT_CHARS = 40

JOURNAL_HEADER = """# Журнал обращений к закрытым материалам

Заводится турникетом `tools/vault.py` (решение 51). Одна строка — один
проход: что открыто, к какой попытке, когда. Файл нужен не для отчётности
перед кем-то — он нужен на выпускной точке R5 и при сборке резюме:
умение, решение которого открывалось до попытки, заявляется с оговоркой
или пересдаётся.

| Когда (UTC) | Что открыто | Файл попытки | Значащих символов в попытке |
|---|---|---|---|
"""


def _key(name: str) -> bytes:
    return hashlib.scrypt(
        password=name.encode("utf-8"), salt=SALT, n=2**14, r=8, p=1, dklen=32
    )


def _keystream(name: str, length: int) -> bytes:
    return hashlib.shake_256(_key(name)).digest(length)


def _xor(data: bytes, name: str) -> bytes:
    stream = _keystream(name, len(data))
    return bytes(a ^ b for a, b in zip(data, stream))


def locked_path(path: Path) -> Path:
    return path.with_name(path.name + ".enc")


def is_locked(path: Path) -> bool:
    return locked_path(path).exists()


def read_text(path: Path) -> str:
    """Содержимое файла, открытого или закрытого, — для инструментов.

    `tools/check_consistency.py` читает эталонные запросы через эту
    функцию: проверка «эталон посчитан на состоянии базы своего шага»
    обязана продолжать работать после закрытия файла, иначе турникет
    ломает единственную машинную сверку эталонов в репозитории.
    """
    if path.exists():
        return path.read_text(encoding="utf-8")
    enc = locked_path(path)
    if enc.exists():
        rel = path.relative_to(ROOT).as_posix()
        # Универсальные переводы строк: файл шифруется байтами как есть,
        # а инструменты (регулярки check_consistency) ждут LF, как после
        # обычного read_text. Без нормализации CRLF молча ломает разбор:
        # маркер «Эталон:» находится, а блок ```sql после него — нет.
        raw = _xor(enc.read_bytes(), rel).decode('utf-8')
        return raw.replace(chr(13) + chr(10), chr(10))
    raise FileNotFoundError(path)


def lock(path: Path) -> int:
    if not path.exists():
        print(f"нет файла {path}")
        return 1
    rel = path.relative_to(ROOT).as_posix()
    enc = locked_path(path)
    enc.write_bytes(_xor(path.read_bytes(), rel))
    path.unlink()
    print(f"закрыт: {rel} -> {enc.relative_to(ROOT).as_posix()}")
    return 0


def _short(path: Path) -> str:
    """Путь относительно репозитория, если файл внутри него, иначе — как есть.

    Файл попытки обычно лежит в `program/*/work/`, но может лежать где
    угодно; журнал не должен падать из-за пути вне репозитория.
    """
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _significant(text: str) -> int:
    """Значащие символы попытки: без пробелов, без комментариев-строк."""
    lines = [
        line for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("#", "--", "//"))
    ]
    return len(re.sub(r"\s+", "", "\n".join(lines)))


def open_(path: Path, attempt: Path, to: Path | None = None) -> int:
    rel = path.relative_to(ROOT).as_posix()
    enc = locked_path(path)
    if not enc.exists():
        print(f"файл {rel} не закрыт турникетом — читайте его как есть")
        return 1
    if not attempt.exists():
        print(
            f"нет файла попытки {attempt}.\n"
            "Турникет открывает решение после попытки, а не вместо неё: "
            "сохраните то, что получилось, даже если оно не сходится."
        )
        return 1
    size = _significant(attempt.read_text(encoding="utf-8"))
    if size < MIN_ATTEMPT_CHARS:
        print(
            f"в {attempt} {size} значащих символов, нужно ≥{MIN_ATTEMPT_CHARS}.\n"
            "Пустой файл попыткой не считается."
        )
        return 1

    if not JOURNAL.exists():
        JOURNAL.write_text(JOURNAL_HEADER, encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    with JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(
            f"| {stamp} | `{rel}` | `{_short(attempt)}` | {size} |\n"
        )
    print(f"[журнал] запись добавлена в {JOURNAL.relative_to(ROOT).as_posix()}")
    payload = _xor(enc.read_bytes(), rel)
    if to is not None:
        to.parent.mkdir(parents=True, exist_ok=True)
        to.write_bytes(payload)
        print(f"[файл] содержимое записано в {_short(to)}")
        print(
            "Файл на диске нужен там, где эталон читает не человек, а скрипт "
            "(`compare_csv.py`). Каталог `**/unlocked/` в `.gitignore`: "
            "расшифрованный эталон не коммитится."
        )
        return 0
    print("=" * 72)
    print(payload.decode("utf-8"))
    return 0


def status(path: Path | None) -> int:
    targets = (
        [path] if path else sorted(p.with_name(p.name[:-4]) for p in ROOT.rglob("*.enc"))
    )
    for target in targets:
        rel = target.relative_to(ROOT).as_posix()
        print(f"{'закрыт ' if is_locked(target) else 'открыт '} {rel}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["list", "lock", "open", "status"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--attempt", help="файл вашей попытки")
    parser.add_argument(
        "--to",
        help="куда записать содержимое вместо печати в консоль — нужно там, "
             "где эталон читает скрипт, а не человек (каталог unlocked/)",
    )
    args = parser.parse_args()

    if args.command in {"list", "status"}:
        return status(Path(args.path).resolve() if args.path else None)
    if not args.path:
        print("нужен путь к файлу")
        return 1
    target = Path(args.path).resolve()
    if args.command == "lock":
        return lock(target)
    if not args.attempt:
        print("нужен --attempt <файл вашей попытки>")
        return 1
    return open_(
        target,
        Path(args.attempt).resolve(),
        Path(args.to).resolve() if args.to else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
