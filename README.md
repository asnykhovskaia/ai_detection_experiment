**Студенческий проект по курсу «Лингвистическая интерпретация языковых моделей».**
Выполнили студенты 3 курса ОП "Фундаментальная и компьютерная лингвистика" Илья Степанов, Арина Сныховская, Анна Федина и Адриан Стивен Франко Канья с опорой на статью Distinguishing Artificial from Authentic: Evaluating LLMs for Detecting 
LLM-Generated Content Juho Leinonen & Paul Denny Aalto University University of Auckland 13 may 2026.

**Инструкция по запуску кода детекции AI/человек**
Один файл — от установки до получения результатов. Все команды выполняются в терминале (macOS / Linux).

1. Требования
Python 3.10+ — скрипты используют list[Path], str | None.

Claude Code CLI — обязателен для claude_*.py и run_detection.py.

Codex CLI — опционально, только если хотите агента codex.

Аккаунт Claude (Pro/Max/Team) или API-ключ для авторизации CLI.

Проверка Python:

bash
python3 --version
2. Установка Claude Code CLI
bash
curl -fsSL https://claude.ai/install.sh | bash
Откройте новый терминал и проверьте:

bash
claude --version
Если claude не найден — добавьте в PATH:

bash
export PATH="$HOME/.local/bin:$PATH"
(чтобы сохранить навсегда — добавьте строку в ~/.zshrc или ~/.bashrc).

Альтернатива через Homebrew (не автообновляется):

bash
brew install --cask claude-code
Первая авторизация: запустите claude в любом каталоге — откроется браузер для входа в аккаунт Claude. Токен сохранится, повторно логиниться не нужно.

Опционально: Codex CLI
bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
Первый запуск codex попросит войти через ChatGPT (Plus/Pro/Business). В скриптах claude_*.py агент задаётся константой AGENT = 'claude' — замените на 'codex', чтобы переключиться. run_detection.py поддерживает только claude.

3. Скачивание данных
bash
git clone https://github.com/asnykhovskaia/ai_detection_experiment.git
cd ai_detection_experiment
Данные лежат в data/. Скрипты claude_*.py ожидают примерно такую структуру (зависит от режима):

text
ai_detection_experiment/
├── data/
│   ├── labeled_text_corpora/
│   │   ├── AI/*.txt
│   │   └── Human/*.txt
│   ├── unlabeled/
│   │   ├── text_corpora/
│   │   │   ├── A/*.txt
│   │   │   └── B/*.txt
│   │   └── undivided/
│   │       ├── C/*.txt
│   │       └── prompts/*.txt
│   ├── human-written corpora/*.txt
│   └── ai-written corpora/texts_100/**/*.txt
├── claude_labeled.py
├── claude_unlabeled.py
├── claude_undivided.py
└── run_detection.py
Если структура в репозитории отличается — скрипт упадёт с Missing directory. Тогда либо приведите папки к ожидаемому виду, либо передайте --prompts-dir (для промптов), либо отредактируйте ROOT/DEPTH в начале файла. Для run_detection.py достаточно указать --root.

4. Подготовка данных (однократно, если нужно)
4.1. Отбор 100 текстов средней длины
Скрипт 100 mid-ranking selection.py берёт из essays_routine 100 текстов из середины распределения по длине (убирает влияние длины на детекцию). Пути в оригинале захардкожены под macOS — откройте файл и замените:

python
TEXT_DIR = Path("/Users/ваше_имя/.../data/essays_routine")
Затем:

bash
python3 "100 mid-ranking selection.py"
Результат — папка essays_routine_selected_100 рядом с исходной.

4.2. Парные head-тексты
Скрипт head-text corpora pairings.py переносит в essays/ только файлы, у которых есть .head.-версия. Использует shutil.move — файлы исчезают из исходной папки. Сделайте бэкап или замените move на copy2. Отредактируйте total_folder и folder_x под себя, затем:

bash
python3 "head-text corpora pairings.py"
5. Запуск основного эксперимента
Все четыре скрипта по умолчанию работают в dry-run: без --execute они только печатают превью сообщения и ничего не вызывают. Это защита от случайной траты токенов.

5.1. claude_labeled.py — режим labeled (метка раскрыта)
Корпуса: labeled_text_corpora/AI, labeled_text_corpora/Human. ROOT = HERE (файл в корне проекта).

Проверка без вызовов:

bash
python3 claude_labeled.py --per-source 10 --repeats 3
Реальный запуск:

bash
python3 claude_labeled.py --per-source 10 --repeats 3 --execute
5.2. claude_unlabeled.py — режим unlabeled (метка скрыта)
Корпуса: unlabeled/text_corpora/A, .../B. ROOT = HERE.parent — файл должен лежать на уровень глубже корня.

bash
python3 claude_unlabeled.py --per-source 10 --repeats 3 --context-examples 2
python3 claude_unlabeled.py --per-source 10 --repeats 3 --context-examples 2 --execute
--context-examples N — сколько примеров из каждой группы A/B подмешать (по умолчанию 2; 0 — отключить).

5.3. claude_undivided.py — режим undivided (без групп)
Корпус: unlabeled/undivided/C. ROOT = HERE.parents[1] — файл на два уровня глубже корня.

bash
python3 claude_undivided.py --num-texts 20 --repeats 3
python3 claude_undivided.py --num-texts 20 --repeats 3 --execute
--num-texts N — сколько текстов взять из C (по умолчанию 20). --per-source игнорируется.

5.4. run_detection.py — упрощённый запуск
Ожидает prompts/1A..2C.txt, data/human-written corpora/, data/ai-written corpora/texts_100/.

bash
python3 run_detection.py --dry-run
python3 run_detection.py --root /путь/к/ai_detection_experiment --per-source 10 --repeats 10 --execute
Быстрый тест на одном вызове:

bash
python3 run_detection.py --root /путь/к/проекту --max-calls 1 --execute
Ограничение: run_detection.py не сохраняет номер повтора в CSV (колонки prompt_name, text_name, response). При --repeats > 1 повторы неотличимы от разных текстов. Для анализа повторов используйте claude_*.py (там есть колонка repeat) или добавьте 'repeat' в COLUMNS.

6. Полезные флаги (общие для claude_*.py)
Флаг	Значение
--per-source N	Текстов с каждого источника (по умолчанию 10)
--num-texts N	Текстов в undivided (по умолчанию 10 или 20)
--repeats N	Повторов на (текст, промпт) (по умолчанию 3)
--max-calls N	Лимит вызовов для теста
--seed N	Seed перемешивания (по умолчанию 42)
--timeout N	Таймаут одного вызова, сек (по умолчанию 180)
--output PATH	Свой путь к CSV
--overwrite	Перезаписать существующий CSV
--execute	Реально вызывать CLI
--prompts-dir PATH	Своя папка с промптами
--context-examples N	Примеров A/B (только unlabeled)
7. Где результаты
claude_*.py → <ROOT>/unlabeled/undivided/outputs/<agent>_<mode>.csv (путь одинаковый для всех трёх режимов — используйте --output, чтобы не перезаписать).

run_detection.py → <root>/outputs/detector_results.csv (UTF-8-sig, корректно открывается в Excel).

Колонки CSV: prompt_name, text_name, repeat, response (в run_detection.py — без repeat).

8. Типичные ошибки
Ошибка	Причина	Решение
Missing directory: ...	ROOT не совпадает со структурой	Проверить DEPTH/ROOT или передать --prompts-dir / --root
claude CLI not installed	CLI не в PATH	Переустановить / добавить ~/.local/bin в PATH
Invalid numeric response	Модель ответила не числом	Проверить, что промпт 1*.txt явно просит число 0–100
output already exists	CSV уже есть	--overwrite или новый --output
Empty text: ...	Пустой .txt	Удалить/исправить файл
Not enough texts: available=... requested=...	Текстов меньше, чем --per-source	Уменьшить --per-source или добавить тексты
9. Рекомендуемый порядок первого запуска
claude --version — CLI работает.

git clone репозитория, проверить структуру data/.

Dry-run каждого нужного скрипта без --execute — проверить пути и превью.

--max-calls 1 --execute — один реальный вызов, убедиться, что CSV создаётся и строка пишется.

Полный запуск с нужными --per-source / --repeats.

Если dry-run показывает несовпадение путей — не запускайте --execute. Сначала исправьте ROOT/DEPTH или структуру папок.

**Где найти результаты:**
в директории outputs
