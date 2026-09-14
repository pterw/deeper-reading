"""Strict host-list parsers. Unknown formats cannot prove discovery.

Copilot: documented `skill list --json` array (name, enabled fields).
Gemini: packages/cli/src/commands/skills/list.ts records, including ANSI SGR.
See installer/USAGE.md for the source contracts and compatibility policy.
"""
import json
import re


def discovery_state(host: str, output: str, skill_name: str) -> str:
    if host == 'copilot':
        try:
            rows = json.loads(output)
        except (ValueError, TypeError):
            return 'failed'
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or not isinstance(row.get('name'), str)
            or not row['name'] or not isinstance(row.get('enabled'), bool) for row in rows
        ):
            return 'failed'
        return 'verified' if any(row['name'] == skill_name and row['enabled'] for row in rows) else 'missing'

    lines = re.sub(r'\x1b\[[0-9;]*m', '', output).splitlines()
    if lines == ['No skills discovered.']:
        return 'missing'
    if not lines or lines[0] != 'Discovered Agent Skills:':
        return 'failed'
    found = False
    count = 0
    index = 1
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        record = re.fullmatch(r'(\S+) \[(Enabled|Disabled)\](?: \[Built-in\])?', lines[index])
        if not record or index + 2 >= len(lines) or not lines[index + 1].startswith('  Description: '):
            return 'failed'
        index += 2
        # A description may span lines; consume it as data, never as a record.
        while index < len(lines) and not lines[index].startswith('  Location:    '):
            index += 1
        if index == len(lines) or not lines[index][15:].strip():
            return 'failed'
        found |= record[1] == skill_name and record[2] == 'Enabled'
        count += 1
        index += 1
        if index < len(lines) and lines[index].strip():
            return 'failed'
    return ('verified' if found else 'missing') if count else 'failed'
