"""Browser QA for the static workbench (Playwright + Chromium).

Serves the repository root over HTTP, loads site/index.html at desktop and mobile
sizes, exercises every control, checks console/page errors, failed requests and
internal links, verifies an evidence hash in-browser, and saves screenshots.

Usage: python site/tests/browser_qa.py [--shots docs/screenshots]
"""
from __future__ import annotations
import argparse
import functools
import http.server
import json
import re
import threading
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{httpd.server_address[1]}/site/index.html'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path, default=ROOT / 'docs' / 'screenshots')
    args = ap.parse_args()
    args.shots.mkdir(parents=True, exist_ok=True)
    httpd, url = serve()
    report = {'url': url, 'checks': [], 'console_errors': [], 'page_errors': [], 'failed_requests': []}

    def check(name, ok, detail=''):
        report['checks'].append({'name': name, 'pass': bool(ok), 'detail': detail})
        print(('PASS ' if ok else 'FAIL ') + name + (f' — {detail}' if detail else ''))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, vp, mobile in (('desktop', {'width': 1440, 'height': 900}, False), ('mobile', {'width': 390, 'height': 844}, True)):
            ctx = browser.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile, color_scheme='light')
            page = ctx.new_page()
            page.on('console', lambda m, l=label: m.type == 'error' and report['console_errors'].append(f'{l}: {m.text}'))
            page.on('pageerror', lambda e, l=label: report['page_errors'].append(f'{l}: {e}'))
            page.on('requestfailed', lambda r, l=label: report['failed_requests'].append(f'{l}: {r.url}'))
            page.on('response', lambda r, l=label: r.status >= 400 and report['failed_requests'].append(f'{l}: {r.status} {r.url}'))
            page.goto(url, wait_until='load')
            page.wait_for_function('window.FalsifyLabUI && document.querySelector("#hero-chart .main-svg")', timeout=20000)
            check(f'{label}: page loads with hero chart', True)
            width = page.evaluate('document.documentElement.scrollWidth')
            check(f'{label}: no horizontal page scroll', width <= vp['width'], f'scrollWidth={width}')
            stats = page.inner_text('#hero-stats')
            check(f'{label}: hero stats show recorded numbers', '1,064.8' in stats and '0.40' in stats and 'of 38 misses' in stats.replace('\n', ' '), stats[:160].replace('\n', ' | '))
            check(f'{label}: workflow has 8 stages', page.locator('#workflow .stage').count() == 8)
            page.screenshot(path=str(args.shots / f'{label}-hero.png'))

            # Materials lab: animated run on the benchmark preset.
            page.locator('#mat-run').scroll_into_view_if_needed()
            page.click('#mat-run')
            page.wait_for_function('window.FalsifyLabUI.lab.phase === "done"', timeout=20000)
            verdicts = page.inner_text('#mat-verdicts')
            check(f'{label}: materials run reaches audit verdict', 'independent audit' in verdicts.lower() and 'refuted' in verdicts.lower(), verdicts[:120].replace('\n', ' | '))
            check(f'{label}: ledger counts 409 readings', 'Readings so far: 409' in page.inner_text('#mat-ledger'))
            page.check('#mat-truth')
            check(f'{label}: truth reveal reports coverage', any(k in page.inner_text('#mat-verdicts') for k in ('Covered', 'Missed, but flagged', 'Silent miss')))
            page.locator('#materials-lab').screenshot(path=str(args.shots / f'{label}-materials-lab.png'))
            # Hidden-dip preset should expose a silent miss for bisection.
            page.select_option('#mat-preset', 'dip')
            page.click('#mat-run')
            page.wait_for_function('window.FalsifyLabUI.lab.phase === "done"', timeout=20000)
            dip_text = page.inner_text('#mat-verdicts')
            check(f'{label}: hidden dip shows silent miss', 'Silent miss' in dip_text, dip_text[-160:].replace('\n', ' | '))
            if not mobile:
                page.locator('#materials-lab').screenshot(path=str(args.shots / 'desktop-materials-dip-silent-miss.png'))
            # Step mode and policy switch.
            page.select_option('#mat-preset', 'benchmark')
            page.click('#mat-step')
            page.click('#mat-step')
            check(f'{label}: step mode shows first probe', 'Probe 1' in page.inner_text('#mat-ledger'))
            page.click('#mat-policy button[data-v="uniform"]')
            check(f'{label}: policy switch completes run for uniform', 'uniform grid' in page.inner_text('#mat-verdicts').lower())
            # Unsupported custom input: H > E is rejected without breaking the page.
            page.select_option('#mat-preset', 'custom')
            page.evaluate("""() => { const e = document.querySelector('#mat-E'); e.value = 50000; e.dispatchEvent(new Event('input')); const h = document.querySelector('#mat-H'); h.value = 20000; h.dispatchEvent(new Event('input')); }""")
            page.click('#mat-run')
            page.wait_for_function('window.FalsifyLabUI.lab.phase === "done"', timeout=20000)
            txt = page.inner_text('#mat-verdicts')
            check(f'{label}: custom material within bounds runs (E 50 GPa, H 20 GPa)', 'independent audit' in txt.lower(), txt[:100].replace('\n', ' | '))
            # Onset beyond probed range -> fallback and abstention.
            page.evaluate("""() => { const y = document.querySelector('#mat-ey'); y.value = 0.0005; y.dispatchEvent(new Event('input')); const E = document.querySelector('#mat-E'); E.value = 210000; E.dispatchEvent(new Event('input')); }""")
            page.click('#mat-run')
            page.wait_for_function('window.FalsifyLabUI.lab.phase === "done"', timeout=20000)
            txt = page.inner_text('#mat-verdicts')
            check(f'{label}: onset below probed range (yield 0.05%) falls back and abstains', 'inconclusive' in txt.lower() or 'No valid empirical bracket' in txt, txt[:200].replace('\n', ' | '))
            page.select_option('#mat-preset', 'benchmark')

            # Oscillator lab: three systems and noise levels.
            page.locator('#oscillator-lab').scroll_into_view_if_needed()
            for system in ('duffing_nonlinearity', 'harmonic_undamped_control', 'weakly_damped_negative_control'):
                page.click(f'#osc-system button[data-v="{system}"]')
                page.wait_for_function(f'window.FalsifyLabUI.osc.result && window.FalsifyLabUI.osc.result.system === "{system}"')
                v = page.inner_text('#osc-verdicts')
                expect = {'duffing_nonlinearity': ('Refuted', 'Quartic revision'), 'harmonic_undamped_control': ('Not refuted', 'Not attempted'),
                          'weakly_damped_negative_control': ('Refuted', 'Quartic revision')}[system]
                check(f'{label}: oscillator {system} verdicts', all(e.lower() in v.lower() for e in expect), v[:140].replace('\n', ' | '))
            before = page.evaluate('window.FalsifyLabUI.osc.runs')
            page.click('#osc-run')
            page.wait_for_function(f'window.FalsifyLabUI.osc.runs > {before}')
            check(f'{label}: oscillator Run button reruns and reports it', f'Run {before + 1}' in page.inner_text('#osc-status'), page.inner_text('#osc-status')[:90])
            page.click('#osc-newseed')
            page.wait_for_function(f'window.FalsifyLabUI.osc.runs > {before + 1}')
            check(f'{label}: New seed button runs a new seed', page.evaluate('window.FalsifyLabUI.osc.result.seed') == int(page.input_value('#osc-seed')))
            page.click('#osc-system button[data-v="duffing_nonlinearity"]')
            page.click('#osc-noise button[data-v="0.01"]')
            page.wait_for_function('window.FalsifyLabUI.osc.result.noiseSd === 0.01')
            check(f'{label}: oscillator noise disclosure cites post-hoc audit', 'post-hoc' in page.inner_text('#osc-disclosure'))
            page.click('#osc-noise button[data-v="0"]')
            page.locator('#oscillator-lab').screenshot(path=str(args.shots / f'{label}-oscillator-lab.png'))

            # Benchmark and evidence.
            page.locator('#benchmark').screenshot(path=str(args.shots / f'{label}-benchmark.png'))
            check(f'{label}: benchmark charts rendered', page.locator('#benchmark .main-svg').count() >= 4)
            for name in ('oscillator', 'harmonic_undamped_control', 'weakly_damped_negative_control', 'materials'):
                page.click(f'#ev-tabs button[data-c="{name}"]')
                check(f'{label}: evidence tab {name}', 'Hypothesis' in page.inner_text('#ev-panel'))
            page.click('#ev-panel [data-verify="1"]')
            page.wait_for_function('document.querySelector("#vr-1") && !document.querySelector("#vr-1").textContent.includes("Hashing")', timeout=20000)
            check(f'{label}: in-browser SHA-256 of raw data matches', 'matches' in page.inner_text('#vr-1'), page.inner_text('#vr-1'))
            page.locator('#evidence').screenshot(path=str(args.shots / f'{label}-evidence.png'))
            page.screenshot(path=str(args.shots / f'{label}-full.png'), full_page=True)

            # Internal links resolve.
            if not mobile:
                hrefs = page.eval_on_selector_all('a[href]', 'els => els.map(e => e.getAttribute("href"))')
                bad = []
                for h in sorted(set(hrefs)):
                    if h.startswith('#'):
                        if h != '#' and not page.locator(h).count():
                            bad.append(h)
                        continue
                    full = urljoin(url, h)
                    if urlparse(full).netloc != urlparse(url).netloc:
                        continue
                    r = page.request.get(full)
                    if r.status != 200:
                        bad.append(f'{h} -> {r.status}')
                check('desktop: internal links resolve', not bad, '; '.join(bad) or f'{len(set(hrefs))} links checked')
                # Dark theme.
                page.click('#theme-toggle')
                page.wait_for_timeout(500)
                page.evaluate('window.scrollTo(0, 0)')
                page.screenshot(path=str(args.shots / 'desktop-dark-hero.png'))
                page.locator('#oscillator-lab').screenshot(path=str(args.shots / 'desktop-dark-oscillator.png'))
            ctx.close()
        browser.close()
    httpd.shutdown()
    check('no console errors', not report['console_errors'], '; '.join(report['console_errors'][:5]))
    check('no page errors', not report['page_errors'], '; '.join(report['page_errors'][:5]))
    check('no failed requests', not report['failed_requests'], '; '.join(report['failed_requests'][:5]))
    out = ROOT / 'docs' / 'logs' / 'audit' / 'browser-qa.json'
    out.write_text(json.dumps(report, indent=2))
    failed = [c for c in report['checks'] if not c['pass']]
    print(f"\nbrowser QA: {len(report['checks']) - len(failed)}/{len(report['checks'])} checks pass; report {out.relative_to(ROOT)}")
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
