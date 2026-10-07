#!/usr/bin/env python3
"""Assemble lesson prompts and track reviewed PNGs. No API or image editing."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import unicodedata
import zlib


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be nonempty text')
    return value


def slug(value):
    value = unicodedata.normalize('NFKC', value).lower()
    value = re.sub(r'[^\w]+', '-', value, flags=re.UNICODE).replace('_', '-')
    return value.strip('-')[:70].rstrip('-') or 'untitled'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError('Plan must be an object')
    for field in ('lesson_title', 'audience', 'style'):
        nonempty(plan.get(field), field)
    if type(plan.get('allow_humans')) is not bool:
        raise ValueError('allow_humans must be a boolean')
    sections = plan.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError('sections must be a nonempty array')
    for index, row in enumerate(sections, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Section {index} must be an object')
        number = row.get('section_number')
        if type(number) not in (int, str) or not str(number).strip():
            raise ValueError(f'Section {index} needs a string or integer section_number')
        for field in ('section_title', 'transcript', 'learning_goal', 'visual_concept',
                      'composition', 'accuracy_notes'):
            nonempty(row.get(field), f'Section {index}: {field}')
        labels = row.get('labels')
        if not isinstance(labels, list):
            raise ValueError(f'Section {index}: labels must be an array')
        for label in labels:
            nonempty(label, 'label')


def filename(index, title, count):
    return f'{index:0{max(2, len(str(count)))}d}-{slug(title)}.png'


def make_prompt(plan, row):
    people = ('Human imagery is explicitly permitted when relevant to this section.'
              if plan['allow_humans'] else
              'No humans, human characters, faces, hands, silhouettes, or human-like mascots.')
    text = (json.dumps(row['labels'], ensure_ascii=False) if row['labels'] else 'None; no text.')
    return '\n'.join([
        'Create one educational video slide image as a PNG.',
        'Format: exact 16:9 widescreen, ideally 1920 x 1080. One separate image, no contact sheet.',
        f"Audience: {plan['audience']}",
        f"Learning goal: {row['learning_goal']}",
        f"Visual: {row['visual_concept']}",
        f"Composition: {row['composition']}",
        f"Shared lesson style: {plan['style']}",
        f"Accuracy constraints: {row['accuracy_notes']}",
        f'Allowed text, verbatim: {text}',
        'Use only these short labels where useful; no paragraphs, transcript, subtitles, or extra text.',
        people,
        'Keep key content and labels inside safe margins. No watermark or decorative branding.'
    ])


def atomic_text(path, content):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     delete=False, suffix='.tmp') as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def save_manifest(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    prompts = [f"# {data['lesson_title']}\n"]
    for row in data['sections']:
        prompts.append(f"## {row['order']:02d}. {row['section_title']}\n\n"
                       f"File: {row['image_filename']} | Status: {row['status']}\n\n"
                       f"{row['generated_image_prompt']}\n")
    atomic_text(Path(path).with_name('prompts.md'), '\n'.join(prompts))


def prepare(plan_path, output_root):
    plan = read_json(plan_path)
    validate_plan(plan)  # Validate everything before writing output.
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    base = slug(plan['lesson_title']) + '-images'
    version = 1
    while True:
        folder = root / (base if version == 1 else f'{base}-{version:02d}')
        try:
            folder.mkdir()
            break
        except FileExistsError:
            version += 1
    data = {**plan, 'schema_version': 1, 'aspect_ratio': '16:9'}
    for index, row in enumerate(data['sections'], 1):
        prompt = make_prompt(data, row)
        row.update(order=index, image_filename=filename(index, row['section_title'], len(data['sections'])),
                   generated_image_prompt=prompt, initial_prompt=prompt, status='planned')
    path = folder / 'manifest.json'
    save_manifest(path, data)
    return path


def load_manifest(path):
    data = read_json(path)
    validate_plan(data)
    if data.get('schema_version') != 1 or data.get('aspect_ratio') != '16:9':
        raise ValueError('Unsupported manifest schema or aspect ratio')
    for index, row in enumerate(data['sections'], 1):
        expected = filename(index, row['section_title'], len(data['sections']))
        if row.get('order') != index or row.get('image_filename') != expected:
            raise ValueError(f'Section {index}: invalid order or filename')
        if row.get('status') not in ('planned', 'blocked', 'complete'):
            raise ValueError(f'Section {index}: invalid status')
        nonempty(row.get('generated_image_prompt'), 'generated_image_prompt')
    return data


def png_size(path):
    with Path(path).open('rb') as stream:
        header = stream.read(33)
    if (len(header) != 33 or header[:8] != b'\x89PNG\r\n\x1a\n'
            or header[8:16] != b'\x00\x00\x00\rIHDR'
            or zlib.crc32(header[12:29]) != struct.unpack('>I', header[29:33])[0]):
        raise ValueError(f'Invalid PNG header: {path}')
    width, height = struct.unpack('>II', header[16:24])
    if not width or not height or width * 9 != height * 16:
        raise ValueError(f'Expected exact 16:9 PNG; found {width} x {height}: {path}')
    return width, height


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def select(data, order):
    if not 1 <= order <= len(data['sections']):
        raise ValueError('Order is outside the lesson')
    return data['sections'][order - 1]


def attach(manifest, order, image, reviewed, prompt_file=None):
    if not reviewed:
        raise ValueError('Visual review is required; pass --reviewed after inspection')
    manifest = Path(manifest)
    data = load_manifest(manifest)
    row = select(data, order)
    if row['status'] == 'complete':
        raise ValueError('Section is already complete; use a new output folder for revisions')
    prompt = (nonempty(Path(prompt_file).read_text(encoding='utf-8-sig'), 'final prompt')
              if prompt_file else row['generated_image_prompt'])
    width, height = png_size(image)
    target = manifest.parent / row['image_filename']
    # Exclusive creation protects existing user files, including interrupted prior copies.
    with Path(image).open('rb') as source, target.open('xb') as destination:
        shutil.copyfileobj(source, destination)
    row.update(status='complete', generated_image_prompt=prompt, width=width, height=height,
               sha256=digest(target), visually_reviewed=True)
    row.pop('error', None)
    save_manifest(manifest, data)
    return target


def block(manifest, order, reason):
    data = load_manifest(manifest)
    row = select(data, order)
    if row['status'] == 'complete':
        raise ValueError('Cannot mark an accepted section blocked')
    row.update(status='blocked', error=nonempty(reason, 'reason'))
    save_manifest(manifest, data)


def verify(manifest):
    manifest = Path(manifest)
    data = load_manifest(manifest)
    problems = []
    expected = set()
    for row in data['sections']:
        expected.add(row['image_filename'])
        path = manifest.parent / row['image_filename']
        if row['status'] != 'complete' or not row.get('visually_reviewed'):
            problems.append(f"{row['order']}: incomplete ({row['status']})")
            continue
        try:
            dimensions = png_size(path)
            if dimensions != (row.get('width'), row.get('height')) or digest(path) != row.get('sha256'):
                raise ValueError('Image differs from accepted file')
        except (OSError, ValueError) as error:
            problems.append(f"{row['order']}: {error}")
    extras = {p.name for p in manifest.parent.iterdir() if p.suffix.lower() == '.png'} - expected
    if extras:
        problems.append('Unexpected PNG files: ' + ', '.join(sorted(extras)))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('plan')
    prep.add_argument('--output-root', required=True)
    for name in ('attach', 'block', 'verify'):
        command = commands.add_parser(name)
        command.add_argument('manifest')
        if name != 'verify':
            command.add_argument('--order', type=int, required=True)
        if name == 'attach':
            command.add_argument('--image', required=True)
            command.add_argument('--reviewed', action='store_true')
            command.add_argument('--prompt-file')
        elif name == 'block':
            command.add_argument('--reason', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            print(prepare(args.plan, args.output_root).resolve())
        elif args.command == 'attach':
            print(attach(args.manifest, args.order, args.image, args.reviewed, args.prompt_file).resolve())
        elif args.command == 'block':
            block(args.manifest, args.order, args.reason)
            print('Recorded blocked section')
        else:
            problems = verify(args.manifest)
            print('\n'.join(problems) if problems else 'All section images verified')
            return 1 if problems else 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
