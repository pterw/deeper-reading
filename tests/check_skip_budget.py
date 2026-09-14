"""CI gate: allow only named environment gaps within explicit per-job budgets."""
import argparse
import sys
import xml.etree.ElementTree as ET


def violations(report, *, symlink_budget):
    counts = {'symlinks':0, 'pdftotext':0}
    errors = []
    for skip in report.iter('skipped'):
        reason = skip.get('message', '')
        if any(text in reason for text in ('directory symlinks unavailable',
                                           'file symlinks unavailable', 'symlinks unavailable on this platform')):
            counts['symlinks'] += 1
        elif 'optional PDF backend pdftotext unavailable;' in reason:
            counts['pdftotext'] += 1
        else:
            errors.append(f'unbudgeted skip: {reason}')
    for name, budget in [('symlinks',symlink_budget), ('pdftotext',1)]:
        if counts[name] > budget:
            errors.append(f'{name} skips {counts[name]} exceed budget {budget}')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report')
    parser.add_argument('--symlink-budget', type=int, default=0)
    args = parser.parse_args()
    errors = violations(ET.parse(args.report), symlink_budget=args.symlink_budget)
    for error in errors:
        print(f'FAIL: {error}')
    sys.exit(bool(errors))
