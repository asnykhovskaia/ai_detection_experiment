"""Детектор AI/человек — режим UNDIVIDED (без групп).

Корпус:
  <ROOT>/unlabeled/undivided/C/*.txt

Выбираются --num-texts текстов. Никакого A/B и никаких контекстных
примеров: модель решает по самому тексту и промпту. Это "чистая" проверка
детектора без подсказок о структуре корпуса.

DEPTH = 2 => ROOT = HERE.parents[1] (файл лежит на 2 уровня глубже корня).

Примеры:
  python claude_undivided.py --num-texts 20 --repeats 3
  python claude_undivided.py --num-texts 20 --repeats 3 --execute
"""
import argparse
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MODE = 'undivided'
AGENT = 'claude'
DEPTH = 2
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[DEPTH - 1] if DEPTH else HERE

COLUMNS = ('prompt_name', 'text_name', 'repeat', 'response')


def files_in(folder: Path) -> list[Path]:
    """Все .txt рекурсивно, отсортированные по строковому пути (детерминизм)."""
    if not folder.is_dir():
        raise ValueError(f'Missing directory: {folder}')
    return sorted((p for p in folder.rglob('*.txt') if p.is_file()), key=lambda p: str(p))


def choose(items: list[Path], n: int | None, seed: int) -> list[Path]:
    """n случайных элементов с фиксированным seed; n=None — вернуть все."""
    if n is None:
        return sorted(items, key=lambda p: str(p))
    if len(items) < n:
        raise ValueError(f'Not enough texts in directory: available={len(items)} requested={n}')
    return sorted(random.Random(seed).sample(items, n), key=lambda p: str(p))


def dataset(mode: str, per_source: int, num_texts: int, seed: int) -> list[dict]:
    """Собирает выборку {path, group, name}.

    В undivided режиме group=None, берём num_texts из корпуса C.
    """
    if mode == 'labeled':
        groups = [(ROOT / 'labeled_text_corpora' / 'AI', 'AI'),
                  (ROOT / 'labeled_text_corpora' / 'Human', 'Human')]
        n = per_source
    elif mode == 'unlabeled':
        groups = [(ROOT / 'unlabeled' / 'text_corpora' / 'A', 'A'),
                  (ROOT / 'unlabeled' / 'text_corpora' / 'B', 'B')]
        n = per_source
    else:  # undivided
        groups = [(ROOT / 'unlabeled' / 'undivided' / 'C', None)]
        n = num_texts

    result = []
    for ix, (folder, group) in enumerate(groups):
        items = choose(files_in(folder), n, seed + ix * 1997)
        for path in items:
            result.append({
                'path': path,
                'group': group,
                'name': (group + '/' + path.name) if group else path.name,
            })
    names = [x['name'] for x in result]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate text basenames across groups; cannot identify results in the CSV')
    return result


def locate_prompts(custom: str | None, mode: str) -> Path:
    """Ищет папку с промптами; --prompts-dir имеет приоритет."""
    if custom:
        p = Path(custom).expanduser()
        return p if p.is_absolute() else (Path.cwd() / p)
    candidates = [ROOT / 'unlabeled' / 'undivided' / 'prompts', ROOT / 'prompts',
                  ROOT / 'unlabeled' / 'prompts', ROOT / mode / 'prompts']
    for p in candidates:
        if p.is_dir() and list(p.glob('*.txt')):
            return p
    raise ValueError('No prompt directory found. Supply --prompts-dir')


def prompt_files(directory: Path) -> list[Path]:
    prompts = sorted(directory.glob('*.txt'), key=lambda p: p.name)
    if not prompts:
        raise ValueError(f'No TXT prompts in {directory}')
    return prompts


def examples_for_unlabeled(group_files: list[dict], target_path: Path, count: int = 2) -> str:
    """Заглушка для совместимости; в undivided не используется (групп нет)."""
    lines = []
    for group in ('A', 'B'):
        candidates = [x for x in group_files if x['group'] == group and x['path'] != target_path]
        if not candidates:
            continue
        lines.append(f'Group {group} reference texts (group identity is unknown):')
        for item in candidates[:count]:
            excerpt = item['path'].read_text(encoding='utf-8-sig').strip()[:850]
            lines.append('---\n' + excerpt + '\n---')
    return '\n'.join(lines)


def build_message(prompt: str, item: dict, mode: str, sampled: list[dict], context_examples: int) -> str:
    """Промпт + (пустое интро для undivided) + текст.

    В undivided НЕ добавляем ни метку, ни A/B-контекст — только текст.
    """
    content = item['path'].read_text(encoding='utf-8-sig').strip()
    if not content:
        raise ValueError('Empty text: ' + str(item['path']))

    if mode == 'labeled':
        intro = 'Dataset folder name (source is disclosed): ' + item['group'] + '\n\n'
    elif mode ==
