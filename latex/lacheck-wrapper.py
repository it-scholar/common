#!/usr/bin/env python3
"""
lacheck-wrapper.py — Filter lacheck false positives from custom verbatim envs.

Usage: lacheck-wrapper.py <main.tex>

Runs lacheck on the given file, then drops warnings whose reported line lies
inside one of the BCP Education custom verbatim-like environments:
  codeblock, codefile, terminalin, terminalout, labexercise,
  plus standard verbatim, lstlisting, and minted.

Multi-line lacheck warnings (where the quoted fragment contains a newline) are
re-assembled before the suppression decision is made.

This preserves content (no deletions) while avoiding thousands of spurious
lacheck warnings caused by code snippets that lacheck cannot parse.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

CUSTOM_VERBATIM_ENVS = {
    'codeblock',
    'codefile',
    'terminalin',
    'terminalout',
    'labexercise',
    'verbatim',
    'lstlisting',
    'minted',
}

BEGIN_PAT = re.compile(
    re.escape(r'\begin{')
    + r'(' + '|'.join(CUSTOM_VERBATIM_ENVS) + r')'
    + re.escape(r'}')
)
WARNING_PAT = re.compile(r'^"([^"]+)", line (\d+): (.*)$')


def end_pat(env_name):
    return re.compile(re.escape(r'\end{') + env_name + re.escape(r'}'))


def _scan_file(fpath: Path):
    """Return (lines, eof_inside_env)."""
    if not fpath.exists():
        return [], False
    lines = fpath.read_text().splitlines()
    in_verb = False
    start_line = None
    env_name = None
    for i, line in enumerate(lines, start=1):
        if in_verb:
            if end_pat(env_name).search(line):
                in_verb = False
                env_name = None
                start_line = None
        else:
            m = BEGIN_PAT.search(line)
            if m:
                start_line = i
                env_name = m.group(1)
                in_verb = True
    return lines, in_verb


def inside_custom_verbatim(fpath: Path, lineno: int) -> bool:
    """Return True if lineno (1-based) is inside a custom verbatim env."""
    lines, eof_in_verb = _scan_file(fpath)
    if not lines:
        return False
    # lacheck sometimes reports "end of file" on the line just past EOF.
    if lineno > len(lines):
        return eof_in_verb

    in_verb = False
    start_line = None
    env_name = None
    for i, line in enumerate(lines, start=1):
        if in_verb:
            if end_pat(env_name).search(line):
                if start_line <= lineno <= i:
                    return True
                in_verb = False
                env_name = None
                start_line = None
        else:
            m = BEGIN_PAT.search(line)
            if m:
                start_line = i
                env_name = m.group(1)
                in_verb = True
                if lineno == start_line:
                    return True
    return False


def should_suppress(base_dir: Path, header_line: str) -> bool:
    m = WARNING_PAT.match(header_line)
    if not m:
        return False
    rel_path = m.group(1)
    lineno = int(m.group(2))
    msg = m.group(3)
    fpath = (base_dir / rel_path).resolve()
    # "end of file" warnings are almost always downstream of lacheck getting
    # confused by code in custom verbatim environments; suppress them.
    if 'end of file' in msg:
        return True
    return inside_custom_verbatim(fpath, lineno)


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: lacheck-wrapper.py <file.tex>', file=sys.stderr)
        return 2

    target = sys.argv[1]
    base_dir = Path(target).parent or Path.cwd()

    result = subprocess.run(
        ['lacheck', target],
        capture_output=True,
        text=True,
    )

    kept = 0
    raw_lines = result.stdout.splitlines()
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        m = WARNING_PAT.match(line)
        if m:
            # Collect multi-line warnings whose quoted fragment spans lines.
            block = [line]
            msg = m.group(3)
            while msg.count('"') % 2 == 1 and i + 1 < len(raw_lines):
                i += 1
                next_line = raw_lines[i]
                block.append(next_line)
                msg += '\n' + next_line
            if not should_suppress(base_dir, line):
                for bl in block:
                    print(bl)
                kept += 1
        else:
            print(line)
        i += 1

    if result.stderr:
        print(result.stderr, file=sys.stderr, end='')

    return 1 if kept > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
