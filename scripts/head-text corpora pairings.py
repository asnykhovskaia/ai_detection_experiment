"""Сопоставление head-версий и полных текстов.

В essays_heads лежат файлы вида NNN.head.txt. Для каждого такого номера
NNN скрипт находит в корне проекта файл NNN.* (полный текст) и переносит
его в essays/. Итог — папка essays/ с только теми текстами, у которых
есть head-версия.

ВНИМАНИЕ: используется move — файлы исчезают из исходной папки.
Запуск: python "head-text corpora pairings.py"
"""
import shutil
from pathlib import Path

ROOT = Path(r"/Users/arinasnykhovskaya/Downloads/rltc")
HEADS_DIR = ROOT / "essays_heads"
TARGET_DIR = ROOT / "essays"


def collect_head_numbers(heads_dir: Path) -> set[str]:
    """Собирает префиксы NNN из файлов вида NNN.head.*."""
    numbers = set()
    for file in heads_dir.iterdir():
        if ".head." in file.name:
            numbers.add(file.name.split(".head.")[0])
    return numbers


def move_matching(root: Path, heads: set[str], target: Path) -> int:
    """Переносит файлы root/<NNN>.* в target/, если NNN есть в heads. Возвращает число переносов."""
    target.mkdir(parents=True, exist_ok=True)
    moved = 0
    for path in root.iterdir():
        if not path.is_file():
            continue
        if path.stem in heads:
            shutil.move(str(path), target / path.name)
            moved += 1
    return moved


def main() -> None:
    head_numbers = collect_head_numbers(HEADS_DIR)
    moved = move_matching(ROOT, head_numbers, TARGET_DIR)
    print(f"Найдено head-номеров: {len(head_numbers)}; перенесено файлов: {moved}")


if __name__ == "__main__":
    main()
