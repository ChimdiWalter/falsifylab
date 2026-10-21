"""Retired legacy PDF entry point; prevent mixing v1 numbers with v3 figures."""
if __name__ == '__main__':
    raise SystemExit(
        'The supplied PDF generator mixed hard-coded v1 metrics with current figures. '
        'Its original source is preserved in baseline/original_make_onepager.py. '
        'Use submission/MOMENT_WRITEUP_FINAL.md, generated from frozen metrics with '
        'python -m falsifylab.submission. No current PDF is claimed.'
    )
