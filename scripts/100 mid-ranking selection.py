from pathlib import Path

TEXT_DIR = Path(r"/Users/arinasnykhovskaya/Downloads/rltc/essays_routine")
OUTPUT_DIR = TEXT_DIR.parent / "essays_routine_selected_100"
OUTPUT_DIR.mkdir(exist_ok=True)

files = sorted(TEXT_DIR.glob("*.txt"))
print(f"Найдено файлов: {len(files)}")

data = []
for f in files:
    text = f.read_text(encoding="utf-8", errors="ignore")
    data.append((len(text), f))

data.sort(key=lambda x: x[0])

n = len(data)
keep = 100
start = (n - keep) // 2
end = start + keep
selected = data[start:end]

print(f"\nОставляем тексты с рангами {start+1}–{end} из {n}")
print(f"Диапазон длин: {selected[0][0]} – {selected[-1][0]} символов")

for length, f in selected:
    (OUTPUT_DIR / f.name).write_text(
        f.read_text(encoding="utf-8", errors="ignore"),
        encoding="utf-8"
    )

print(f"\nГотово. Отобрано {len(selected)} текстов в папку:\n{OUTPUT_DIR}")
