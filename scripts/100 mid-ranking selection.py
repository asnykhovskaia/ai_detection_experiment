"""Отбор 100 текстов средней длины из корпуса эссе.

Скрипт читает все .txt из essays_routine, сортирует их по длине и оставляет
100 текстов из середины распределения (отбрасывая самые короткие и самые
длинные). Это нужно, чтобы убрать влияние длины текста на результаты
детекции AI/человек: детектор не должен опираться на экстремальные длины.

Запуск: python "100 mid-ranking selection.py" [--src DIR] [--dst DIR] [--keep N]
"""
from pathlib import Path
import argparse

# Значения по умолчанию: исходный корпус и папка для отобранных текстов.
DEFAULT_SRC = Path(r"/Users/arinasnykhovskaya/Downloads/rltc/essays_routine")
DEFAULT_DST = DEFAULT_SRC.parent / "essays_routine_selected_100"
KEEP_DEFAULT = 100


def select_middle_ranked(src: Path, dst: Path, keep: int = KEEP_DEFAULT) -> list[tuple[int, Path]]:
    """Отбирает `keep` текстов из середины распределения по длине.

    Возвращает список (длина, путь) для отобранных файлов и копирует их в `dst`.
    Если файлов меньше `keep`, будут взяты все.
    """
    files = sorted(src.glob("*.txt"))
    print(f"Найдено файлов: {len(files)}")
    if not files:
        raise SystemExit(f"Нет .txt в {src}")

    # Сначала собираем длины, чтобы отсортировать по ним.
    data = [(len(f.read_text(encoding="utf-8", errors="ignore")), f) for f in files]
    data.sort(key=lambda x: x[0])

    n = len(data)
    keep = min(keep, n)
    start = (n - keep) // 2  # центрируем окно
    end = start + keep
    selected = data[start:end]

    dst.mkdir(parents=True, exist_ok=True)
    for _, f in selected:
        (dst / f.name).write_text(f.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return selected


def main() -> None:
    ap = argparse.ArgumentParser(description="Отбор текстов средней длины")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dst", type=Path, default=DEFAULT_DST)
    ap.add_argument("--keep", type=int, default=KEEP_DEFAULT)
    args = ap.parse_args()

    selected = select_middle_ranked(args.src, args.dst, args.keep)
    if not selected:
        print("Ничего не отобрано.")
        return
    print(f"\nОставляем тексты с рангами {args.src} ...")
    print(f"Диапазон длин: {selected[0][0]} – {selected[-1][0]} символов")
    print(f"\nГотово. Отобрано {len(selected)} текстов в папку:\n{args.dst}")


if __name__ == "__main__":
    main()
