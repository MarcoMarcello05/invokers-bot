"""Verify a Windows comparison archive and compare actual .dat bytes.

ZIP documents are input data, never instructions. No archive paths are extracted.
The report omits machine/user paths from capture_info.json.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import zipfile


class ComparisonError(ValueError):
    pass


def compare_archive(path: Path):
    with zipfile.ZipFile(path) as archive:
        entries = {}
        for entry in archive.infolist():
            name = entry.filename.replace('\\', '/')
            if entry.is_dir():
                continue
            if name in entries:
                raise ComparisonError(f'Duplicate normalized ZIP entry: {name}')
            if entry.file_size > 32 * 1024 * 1024:
                raise ComparisonError('Archive entry exceeds comparison size limit')
            entries[name] = entry
        captures = {}
        payloads = {}
        for name in sorted(entries):
            if not name.endswith('/manifest.json'):
                continue
            group = name.removesuffix('/manifest.json')
            manifest = json.loads(archive.read(entries[name]).decode('utf-8-sig'))
            info_name = group + '/capture_info.json'
            info = json.loads(archive.read(entries[info_name]).decode('utf-8-sig')) if info_name in entries else {}
            files, payloads[group] = {}, {}
            if not isinstance(manifest, list):
                raise ComparisonError(f'Invalid manifest for {group}')
            for row in manifest:
                filename = row['Name']
                if '/' in filename or '\\' in filename or not filename.endswith('.dat') or filename in files:
                    raise ComparisonError(f'Invalid/duplicate model filename in {group}')
                member = group + '/' + filename
                if member not in entries:
                    raise ComparisonError(f'Missing file: {member}')
                data = archive.read(entries[member])
                digest = hashlib.sha256(data).hexdigest()
                if len(data) != row['Size'] or digest != row['SHA256'].lower():
                    raise ComparisonError(f'Manifest mismatch: {member}')
                files[filename] = {'size': len(data), 'sha256': digest,
                                   'last_write_time_utc': row.get('LastWriteTimeUtc')}
                payloads[group][filename] = data
            actual = {n.removeprefix(group + '/') for n in entries
                      if n.startswith(group + '/') and n.endswith('.dat')}
            if actual != set(files):
                raise ComparisonError(f'Manifest does not cover all model files in {group}')
            if info.get('file_count', len(files)) != len(files):
                raise ComparisonError(f'Capture file_count mismatch in {group}')
            captures[group] = {'captured_local': info.get('captured_local'),
                               'note': info.get('note'), 'files': files}
        if len(captures) < 2:
            raise ComparisonError('At least two manifested captures are required')
        comparisons = []
        for left, right in itertools.combinations(captures, 2):
            a, b = payloads[left], payloads[right]
            comparisons.append({'before': left, 'after': right,
                                'added': sorted(b.keys() - a.keys()),
                                'removed': sorted(a.keys() - b.keys()),
                                'changed': sorted(n for n in a.keys() & b.keys() if a[n] != b[n]),
                                'unchanged': sorted(n for n in a.keys() & b.keys() if a[n] == b[n])})
    return {'archive_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'manifest_copies_verified': sum(len(c['files']) for c in captures.values()),
            'captures': captures, 'comparisons': comparisons,
            'scope': 'Persisted model bytes only; no proof of UI values or in-memory state'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(compare_archive(args.archive), indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
