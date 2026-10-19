
import argparse
import csv
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROMPT_NAMES = ('1A.txt', '1B.txt', '1C.txt', '2A.txt', '2B.txt', '2C.txt')
COLUMNS = ('prompt_name', 'text_name', 'response')


def read_utf8(path):
    return path.read_text(encoding='utf-8-sig')


def parse_response(name, response):
    response = response.strip()
    if name.startswith('1'):
        match = re.fullmatch(r'([0-9]+(?:[.,][0-9]+)?)\s*%?', response)
        if match is None:
            raise ValueError(f'Invalid numeric response: {response!r}')
        number = float(match.group(1).replace(',', '.'))
        if not 0 <= number <= 100:
            raise ValueError(f'Probability outside 0-100: {response!r}')
        
        return f'{number:g}'
    if response.casefold() not in ('yes', 'no'):
        raise ValueError(f'Invalid Yes/No response: {response!r}')
    return response.title()


def collect(root, per_source, seed):
    prompt_dir = root / 'prompts'
    human_dir = root / 'data' / 'human-written corpora'
    ai_dir = root / 'data' / 'ai-written corpora' / 'texts_100'
    prompts = {}
    for name in PROMPT_NAMES:
        path = prompt_dir / name
        prompts[name] = read_utf8(path).rstrip('\r\n')

    human = sorted(p for p in human_dir.glob('*.txt') if p.name != 'principles.txt')
    ai = sorted(p for p in ai_dir.rglob('*.txt')
                if p.name.casefold() not in {'prompt.txt', 'principles.txt', 'info.txt'})
    if len(human) < per_source or len(ai) < per_source:
        raise ValueError(f'Not enough texts: human={len(human)}, AI={len(ai)}, requested={per_source} each')
    rng = random.Random(seed)
    selected = rng.sample(human, per_source) + rng.sample(ai, per_source)
    if len({p.name for p in selected}) != len(selected):
        raise ValueError('Two selected texts have the same filename; three CSV columns cannot distinguish them.')
    texts = [(p.name, read_utf8(p)) for p in selected]
    if any(not content.strip() for _, content in texts):
        raise ValueError('Empty text encountered')
    return prompts, texts, len(human), len(ai)


def claude_answer(message, model, timeout, root):
    cmd = ['claude', '-p', '--output-format', 'json', '--tools', '']
    if model:
        cmd += ['--model', model]
    proc = subprocess.run(cmd, input=message, text=True, encoding='utf-8',
                          capture_output=True, timeout=timeout, cwd=root)
    if proc.returncode:
        raise RuntimeError(f'Claude CLI returned {proc.returncode}: {proc.stderr[-800:]}')
    data = json.loads(proc.stdout)
    if data.get('is_error') or not isinstance(data.get('result'), str):
        raise RuntimeError(f'Unexpected Claude response: {str(data)[:500]}')
    return data['result']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', default='.', help='Project root')
    ap.add_argument('--per-source', type=int, default=10, help='Texts per class (default: 10)')
    ap.add_argument('--repeats', type=int, default=10, help='Independent calls for each pair (default: 10)')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--output', default='outputs/detector_results.csv')
    ap.add_argument('--model', default='', help='Pin detector model for research')
    ap.add_argument('--timeout', type=int, default=180)
    ap.add_argument('--dry-run', action='store_true', help='Preview without Claude calls or writing CSV')
    ap.add_argument('--execute', action='store_true', help='Actually call Claude')
    ap.add_argument('--max-calls', type=int, default=0, help='Limit calls, for testing only; 0 is unlimited')
    ap.add_argument('--overwrite', action='store_true', help='Replace an existing results CSV and start from scratch')
    args = ap.parse_args()
    if args.per_source < 1 or args.repeats < 1 or args.max_calls < 0 or args.timeout < 1:
        ap.error('Invalid numeric argument')
    if args.execute and args.dry_run:
        ap.error('Cannot combine --execute and --dry-run')
    root = Path(args.root).resolve()
    prompts, texts, human_count, ai_count = collect(root, args.per_source, args.seed)
    planned = len(prompts) * len(texts) * args.repeats
    print(f'Available texts: human={human_count}, AI={ai_count}; selected={len(texts)}')
    print(f'Prompts={len(prompts)}, repeats={args.repeats}, planned calls={planned}')
    example_name, example_text = texts[0]
    example_prompt_name = PROMPT_NAMES[0]
    example_message = prompts[example_prompt_name] + '\n\nText:\n' + example_text
    if args.dry_run:
        print(f'\nExample: {example_prompt_name} + {example_name}\n{example_message[:1800]}')
        return
    if not args.execute:
        print('No calls made. Use --dry-run or --execute --max-calls 1.')
        return
    if not shutil.which('claude'):
        raise FileNotFoundError('claude CLI not found; check claude --version')
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f'{output} already exists. Choose a new --output or use --overwrite to restart.')

    calls = 0
    rows = 0
    failed = 0
    
    with output.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        f.flush()
        for text_name, content in texts:
            for prompt_name, prompt in prompts.items():
                message = prompt + '\n\nText:\n' + content
                for run in range(1, args.repeats + 1):
                    if args.max_calls and calls >= args.max_calls:
                        print(f'Stopped after {calls} calls; {rows} CSV rows. File: {output}')
                        return
                    calls += 1
                    try:
                        raw = claude_answer(message, args.model, args.timeout, root)
                        answer = parse_response(prompt_name, raw)
                    except Exception as exc:
                        failed += 1
                        print(f'ERROR call={calls}, {prompt_name} + {text_name}, repeat={run}: {exc}', file=sys.stderr, flush=True)
                        continue
                    writer.writerow({'prompt_name': prompt_name, 'text_name': text_name, 'response': answer})
                    f.flush()
                    rows += 1
                    print(f'[{calls}/{planned}] {prompt_name} | {text_name} | repeat={run} | {answer}', flush=True)
    print(f'Done: calls={calls}, saved rows={rows}, failed calls={failed}. CSV: {output}')
    if failed:
        print('WARNING: Some requests failed. Their errors were printed to stderr; no additional files were created.')
    print('WARNING: This single-CSV format cannot reliably resume an interrupted run.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
