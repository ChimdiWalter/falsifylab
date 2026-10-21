"""Live UI test of the marimo notebook: start `marimo run`, change controls, check outputs.

Usage (repo root, environment with marimo + playwright):
    python site/tests/marimo_ui_qa.py [--shot docs/screenshots/marimo-notebook.png]
"""
from __future__ import annotations
import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shot', type=Path, default=ROOT / 'docs' / 'screenshots' / 'marimo-notebook.png')
    args = ap.parse_args()
    port = free_port()
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    proc = subprocess.Popen([sys.executable, '-m', 'marimo', 'run', 'notebooks/explore.py', '--headless', '--host', '127.0.0.1',
                             '--port', str(port), '--no-token'], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    results = []

    def check(name, ok, detail=''):
        results.append(ok)
        print(('PASS ' if ok else 'FAIL ') + name + (f' — {detail}' if detail else ''))

    try:
        for _ in range(60):
            try:
                socket.create_connection(('127.0.0.1', port), timeout=1).close()
                break
            except OSError:
                time.sleep(.5)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{port}', wait_until='load')
            page.wait_for_selector('text=Candidate law fitted on 40 discovery readings', timeout=90000)
            page.wait_for_selector('text=Counterexamples in the 15-condition catalog', timeout=90000)
            body = page.inner_text('body')
            check('notebook renders materials and oscillator results', 'Readings used in this run: 409' in body and 'REFUTED' in body)
            check('no cell error output', 'Traceback' not in body and 'An internal error occurred' not in body)
            # Change the hidden material to the nonmonotone dip and expect the documented silent miss.
            page.locator('select').first.select_option(label='Hidden softening dip (breaks monotonicity)')
            page.wait_for_selector('text=Silent miss:', timeout=60000)
            check('material dropdown reruns engine; dip shows silent miss', True)
            # Switch the oscillator system to the harmonic control.
            selects = page.locator('select')
            idx = next(i for i in range(selects.count()) if 'duffing_nonlinearity' in selects.nth(i).inner_text())
            selects.nth(idx).select_option(label='harmonic_undamped_control')
            page.wait_for_selector('text=not attempted', timeout=60000)
            check('system dropdown reruns oscillator; harmonic control not revised', True)
            page.screenshot(path=str(args.shot), full_page=True)
            check('no page errors', not errors, '; '.join(errors[:3]))
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f'marimo UI QA: {sum(results)}/{len(results)} checks pass')
    raise SystemExit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
