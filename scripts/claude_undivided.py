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
import time
from pathlib import Path

MODE = 'undivided'
AGENT = 'claude'
DEPTH = 2
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[DEPTH - 1] if DEPTH else HERE

COLUMNS = ('prompt_name', 'text_name', 'repeat', 'response')


def files_in(folder):
    if not folder.is_dir():
        raise ValueError(f'Missing directory: {folder}')
    return sorted((p for p in folder.rglob('*.txt') if p.is_file()), key=lambda p: str(p))


def choose(items, n, seed):
    if n is None:
        return sorted(items, key=lambda p: str(p))
    if len(items) < n:
        raise ValueError(f'Not enough texts in directory: available={len(items)} requested={n}')
    return sorted(random.Random(seed).sample(items, n), key=lambda p: str(p))


def dataset(mode, per_source, num_texts, seed):
    if mode == 'labeled':
        groups = [(ROOT / 'labeled_text_corpora' / 'AI', 'AI'),
                  (ROOT / 'labeled_text_corpora' / 'Human', 'Human')]
        n = per_source
    elif mode == 'unlabeled':
        groups = [(ROOT / 'unlabeled' / 'text_corpora' / 'A', 'A'),
                  (ROOT / 'unlabeled' / 'text_corpora' / 'B', 'B')]
        n = per_source
    else:
        groups = [(ROOT / 'unlabeled' / 'undivided' / 'C', None)]
        n = num_texts
    result = []
    for ix, (folder, group) in enumerate(groups):
        items = choose(files_in(folder), n, seed + ix * 1997)
        for path in items:
            result.append({'path': path, 'group': group, 'name': (group + '/' + path.name) if group else path.name})
    names = [x['name'] for x in result]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate text basenames across groups; cannot identify results in the CSV')
    return result


def locate_prompts(custom, mode):
    if custom:
        p = Path(custom).expanduser()
        return p if p.is_absolute() else (Path.cwd() / p)
    candidates = [ROOT / 'unlabeled' / 'undivided' / 'prompts', ROOT / 'prompts',
                  ROOT / 'unlabeled' / 'prompts', ROOT / mode / 'prompts']
    for p in candidates:
        if p.is_dir() and list(p.glob('*.txt')):
            return p
    raise ValueError('No prompt directory found. Supply --prompts-dir')


def prompt_files(directory):
    prompts = sorted(directory.glob('*.txt'), key=lambda p: p.name)
    if not prompts:
        raise ValueError(f'No TXT prompts in {directory}')
    return prompts


def examples_for_unlabeled(group_files, target_path, count=2):
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


def build_message(prompt, item, mode, sampled, context_examples):
    content = item['path'].read_text(encoding='utf-8-sig').strip()
    if not content:
        raise ValueError('Empty text: ' + str(item['path']))
    if mode == 'labeled':
        intro = 'Dataset folder name (source is disclosed): ' + item['group'] + '\n\n'
    elif mode == 'unlabeled':
        intro = ('Texts were organized into two groups called A and B. '
                 'The group labels do not reveal which group contains AI-written texts. '
                 'You may compare their textual characteristics, not filenames.\n'
                 f'Target group: {item["group"]}\n\n')
        if context_examples:
            intro += examples_for_unlabeled(sampled, item['path'], context_examples) + '\n\n'
    else:
        intro = ''
    return prompt.strip() + '\n\n' + intro + 'Text:\n' + content + '\n'


def cli_call(agent, message, timeout):
    command_name = 'claude' if agent == 'claude' else 'codex'
    if not shutil.which(command_name):
        raise RuntimeError(f'{command_name} CLI not installed or unavailable on PATH')
    with tempfile.TemporaryDirectory(prefix='detector_answer_') as temp:
        if agent == 'claude':
            args = ['claude', '-p', '--output-format', 'json', '--tools', '']
            result = subprocess.run(args, input=message, capture_output=True, text=True,
                                    timeout=timeout, cwd=HERE)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout)[-800:])
            response = json.loads(result.stdout)
            if response.get('is_error'):
                raise RuntimeError(str(response.get('result', 'Claude error')))
            answer = response.get('result', '')
        else:
            target = Path(temp) / 'answer.txt'
            args = ['codex', 'exec', '--skip-git-repo-check',
                    '--output-last-message', str(target), '-']
            result = subprocess.run(args, input=message, capture_output=True, text=True,
                                    timeout=timeout, cwd=HERE)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout)[-800:])
            answer = target.read_text(encoding='utf-8').strip() if target.exists() else ''
    return answer.strip()


def validate(prompt_name, answer):
    name = prompt_name.lower()
    numeric = name.startswith('1') or 'likelihood' in name or 'likelyhood' in name
    yesno = name.startswith('2') or 'yes' in name
    if numeric:
        value = answer.strip().removesuffix('%').strip()
        if not re.fullmatch(r'(?:\d+(?:\.\d+)?|\.\d+)', value) or not 0 <= float(value) <= 100:
            raise ValueError(f'Invalid numeric response: {answer!r}')
    elif yesno:
        if answer.strip().lower() not in ('yes', 'no'):
            raise ValueError(f'Invalid Yes/No response: {answer!r}')
    elif not answer:
        raise ValueError('Empty response')
    return answer


def run():
    mode, agent = MODE, AGENT
    parser = argparse.ArgumentParser(description=f'{agent} {mode} detector')
    parser.add_argument('--per-source', type=int, default=10)
    parser.add_argument('--num-texts', type=int, default=20)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--prompts-dir')
    parser.add_argument('--output')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--max-calls', type=int)
    parser.add_argument('--context-examples', type=int, default=2)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if min(args.per_source, args.num_texts, args.repeats, args.timeout) < 1 or args.context_examples < 0:
        parser.error('Counts must be positive (context-examples may be zero)')
    prompts_dir = locate_prompts(args.prompts_dir, mode)
    prompts = prompt_files(prompts_dir)
    data = dataset(mode, args.per_source, args.num_texts, args.seed)
    output = Path(args.output) if args.output else ROOT / 'unlabeled' / 'undivided' / 'outputs' / f'{agent}_{mode}.csv'
    if not output.is_absolute():
        output = HERE / output
    jobs = [(item, p, i) for item in data for p in prompts for i in range(args.repeats)]
    random.Random(args.seed + 501).shuffle(jobs)
    if args.max_calls is not None:
        jobs = jobs[:args.max_calls]
    print(f'MODE={mode} AGENT={agent} texts={len(data)} prompts={len(prompts)} '
          f'repeats={args.repeats} calls={len(jobs)}')
    print('Prompts:', prompts_dir)
    print('Output:', output)
    if not args.execute:
        example = build_message(prompts[0].read_text(encoding='utf-8-sig'), data[0], mode,
                                data, args.context_examples)
        print('DRY RUN (no requests). Message preview:\n', example[:1200])
        return
    if output.exists() and not args.overwrite:
        parser.error(f'{output} already exists; use a different --output, or --overwrite to reset')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        stream.flush()
        completed = 0
        for number, (item, prompt, repeat) in enumerate(jobs, start=1):
            try:
                message = build_message(prompt.read_text(encoding='utf-8-sig'), item,
                                        mode, data, args.context_examples)
                answer = validate(prompt.name, cli_call(agent, message, args.timeout))
                writer.writerow([prompt.name, item['name'], repeat + 1, answer])
                stream.flush()
                os.fsync(stream.fileno())
                completed += 1
                print(f'[{number}/{len(jobs)}] OK {prompt.name} {item["name"]} repeat={repeat+1} => {answer}', flush=True)
            except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
                print(f'[{number}/{len(jobs)}] ERROR {prompt.name} {item["name"]} repeat={repeat+1}: {exc}',
                      file=sys.stderr, flush=True)
    print(f'DONE: {completed}/{len(jobs)} successful; {output}')


if __name__ == "__main__":
    run()
