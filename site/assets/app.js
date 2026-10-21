/* FalsifyLab workbench UI. RECORDED panels read window.FALSIFYLAB_EVIDENCE (built by
 * site/build.py from committed outputs). LIVE panels call window.FalsifyEngine. */
(function () {
  'use strict';
  const D = window.FALSIFYLAB_EVIDENCE;
  const FE = window.FalsifyEngine;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const REF = 'REFUTED', OK = 'NOT_REFUTED_UNDER_TESTED_CONDITIONS', INC = 'INCONCLUSIVE';
  const POL = { active: 'Adaptive bisection', uniform: 'Uniform grid', random: 'Random' };

  // ---------- formatting ----------
  const SUP = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };
  function sci(x, s = 3) {
    if (x === null || x === undefined || !isFinite(x)) return '—';
    if (x === 0) return '0';
    const e = Math.floor(Math.log10(Math.abs(x)));
    if (e >= -2 && e < 5) return sig(x, s);
    const m = x / 10 ** e;
    return `${m.toFixed(s - 1)} × 10${String(e).split('').map(c => SUP[c]).join('')}`;
  }
  function sig(x, s = 4) {
    if (x === null || x === undefined || !isFinite(x)) return '—';
    const v = Number(Number(x).toPrecision(s));
    return Math.abs(v) >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 1 }) : String(v);
  }
  const fixed = (x, d) => (x === null || x === undefined || !isFinite(x) ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));
  const pctStrain = (e, d = 4) => (e === null || e === undefined ? '—' : `${(e * 100).toFixed(d)}%`);
  const pct = (f, d = 0) => (f === null || f === undefined ? '—' : `${(f * 100).toFixed(d)}%`);
  function chip(status, label) {
    if (status === REF) return `<span class="chip refuted">✕ ${esc(label || 'Refuted')}</span>`;
    if (status === OK) return `<span class="chip survives">✓ ${esc(label || 'Not refuted')}</span>`;
    if (status === INC) return `<span class="chip inconclusive">? ${esc(label || 'Inconclusive')}</span>`;
    return `<span class="chip neutral">${esc(label || status || '—')}</span>`;
  }
  const boundaryChip = s => (s === OK ? chip(OK, 'Bracket resolved') : chip(INC, 'Bracket inconclusive'));

  // ---------- plotting ----------
  function merge(a, b) {
    const out = Array.isArray(a) ? a.slice() : { ...a };
    for (const [k, v] of Object.entries(b || {})) out[k] = v && typeof v === 'object' && !Array.isArray(v) && a && typeof a[k] === 'object' && !Array.isArray(a[k]) ? merge(a[k], v) : v;
    return out;
  }
  function axis(extra) {
    return merge({ gridcolor: css('--grid'), zeroline: false, linecolor: css('--line-strong'), tickcolor: css('--line-strong'), ticks: 'outside', ticklen: 4, automargin: true, title: { font: { size: 12, color: css('--ink-2') }, standoff: 8 }, tickfont: { size: 11.5, color: css('--ink-2') } }, extra);
  }
  function layout(extra) {
    return merge({
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: css('--sans'), size: 12, color: css('--ink-2') },
      margin: { l: 58, r: 14, t: 8, b: 44 }, xaxis: axis(), yaxis: axis(),
      legend: { orientation: 'h', x: 0, y: -0.2, yanchor: 'top', font: { size: 11.5, color: css('--ink-2') }, bgcolor: 'rgba(0,0,0,0)' },
      hoverlabel: { bgcolor: css('--surface'), bordercolor: css('--line-strong'), font: { color: css('--ink'), family: css('--sans'), size: 12 } },
      hovermode: 'closest', showlegend: true,
    }, extra);
  }
  const CONFIG = { responsive: true, displaylogo: false, displayModeBar: window.matchMedia('(hover: none), (max-width: 640px)').matches ? false : 'hover', modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toggleSpikelines', 'hoverCompareCartesian', 'hoverClosestCartesian'] };
  function plot(id, traces, lay) {
    const el = document.getElementById(id);
    if (!window.Plotly) { el.innerHTML = '<div class="error-box">Chart library failed to load (assets/vendor/plotly-3.5.0.min.js).</div>'; return; }
    Plotly.react(el, traces, lay, CONFIG);
  }
  const statusMarker = s => (s === REF ? { symbol: 'x-thin-open', color: css('--critical'), line: { width: 2.5, color: css('--critical') } }
    : s === OK ? { symbol: 'circle', color: css('--good'), line: { width: 2, color: css('--surface') } }
      : { symbol: 'diamond', color: css('--warning'), line: { width: 2, color: css('--surface') } });
  const statusText = s => (s === REF ? 'law refuted' : s === OK ? 'law holds' : 'inconclusive');

  // Every panel renders independently; one failure never blanks the page.
  const renderers = [];
  function panel(id, fn) {
    const run = () => {
      try { fn(); } catch (err) {
        console.error(err);
        const el = document.getElementById(id);
        if (el) el.innerHTML = `<div class="error-box">This panel failed to render: ${esc(err.message)}</div>`;
      }
    };
    renderers.push(run);
    run();
  }

  // ======================= HERO =======================
  const M = D.materials;
  const meanOf = a => a.reduce((s, v) => s + v, 0) / a.length;
  function bilinear(e, E, ey, H) { return E * Math.min(e, ey) + H * Math.max(e - ey, 0); }

  function renderHero() {
    const act = M.policies.active, fit = act.fit, E = M.ehat_mpa;
    const disc = M.discovery.strain.map((e, i) => [e, meanOf(M.discovery.readings_mpa[i])]);
    const xs = FE.linspace(0, 0.0145, 300);
    const groups = [REF, OK, INC].map(st => act.observations.filter(o => o.status === st));
    const narrow = document.getElementById('hero-chart').clientWidth < 560;
    const traces = [
      { x: disc.map(d => d[0] * 100), y: disc.map(d => d[1]), mode: 'markers', name: 'Discovery means (40 readings)', marker: { size: 7, color: css('--ink-2') }, hovertemplate: 'Discovery<br>strain %{x:.3f}%<br>%{y:.1f} MPa<extra></extra>' },
      { x: xs.map(e => e * 100), y: xs.map(e => E * e), mode: 'lines', name: 'Candidate: Hooke law σ = Ê·ε', line: { color: css('--initial'), width: 2, dash: 'dash' }, hovertemplate: 'Hooke prediction<br>%{x:.3f}% → %{y:.0f} MPa<extra></extra>' },
      { x: xs.map(e => e * 100), y: xs.map(e => bilinear(e, E, fit.yield_strain, fit.hardening_modulus_mpa)), mode: 'lines', name: 'Revision: bilinear (frozen)', line: { color: css('--revised'), width: 2 }, hovertemplate: 'Bilinear revision<br>%{x:.3f}% → %{y:.1f} MPa<extra></extra>' },
      { x: M.holdout.strain.map(e => e * 100), y: M.holdout.mean_mpa, mode: 'markers', name: 'Independent audit means (249 readings)', marker: { size: 5, color: 'rgba(0,0,0,0)', line: { color: css('--audit'), width: 1.4 } }, hovertemplate: 'Audit<br>%{x:.3f}%<br>%{y:.1f} MPa<extra></extra>' },
      ...groups.filter(g => g.length).map(g => ({
        x: g.map(o => o.strain * 100), y: g.map(o => o.mean_mpa), mode: 'markers', name: `Probe: ${statusText(g[0].status)}`,
        marker: { size: 11, ...statusMarker(g[0].status) }, customdata: g.map(o => [o.deviation_mpa, o.allowance_mpa]),
        hovertemplate: 'Probe at %{x:.4f}%<br>mean %{y:.1f} MPa<br>|error| %{customdata[0]:.1f} ± %{customdata[1]:.1f} MPa<extra></extra>',
      })),
    ];
    const lay = layout({
      xaxis: axis({ title: { text: 'Engineering strain (%)' }, range: [-0.02, 1.45] }),
      yaxis: axis({ title: { text: 'Engineering stress (MPa)' }, range: [-40, 1650] }),
      legend: { y: -0.16 }, margin: { b: 30 },
      annotations: [{ x: 1600 / E * 100 - 0.03, y: 1600, xanchor: 'right', yanchor: 'middle', showarrow: false,
        text: `Hooke prediction keeps rising:<br>${fixed(E * 0.014, 0)} MPa at 1.4% strain`, align: 'right', font: { size: 11, color: css('--initial') } }],
    });
    if (!narrow && act.interval) {
      const win = [0.00185, 0.00225];
      const near = act.observations.filter(o => o.strain >= win[0] && o.strain <= win[1]);
      traces.push({ x: near.map(o => o.strain * 100), y: near.map(o => o.deviation_mpa), xaxis: 'x2', yaxis: 'y2', mode: 'markers', showlegend: false,
        marker: { size: 9, color: near.map(o => (o.status === REF ? css('--critical') : css('--good'))), symbol: near.map(o => (o.status === REF ? 'x-thin-open' : 'circle')), line: { width: 2, color: near.map(o => (o.status === REF ? css('--critical') : css('--surface'))) } },
        error_y: { type: 'data', array: near.map(o => o.allowance_mpa), color: css('--ink-3'), thickness: 1, width: 3 },
        hovertemplate: '%{x:.4f}%: |error| %{y:.1f} MPa<extra></extra>' });
      lay.xaxis2 = axis({ domain: [0.69, 0.98], anchor: 'y2', range: [win[0] * 100, win[1] * 100], title: { text: 'strain (%)', font: { size: 10.5 } }, tickfont: { size: 10 }, nticks: 5 });
      lay.yaxis2 = axis({ domain: [0.44, 0.8], anchor: 'x2', range: [-4, 40], title: { text: '|error| (MPa)', font: { size: 10.5 } }, tickfont: { size: 10 }, nticks: 5 });
      lay.shapes = [
        { type: 'rect', xref: 'paper', yref: 'paper', x0: 0.6, x1: 0.995, y0: 0.33, y1: 0.97, fillcolor: css('--surface'), line: { color: css('--line-strong'), width: 1 }, layer: 'below' },
        { type: 'rect', xref: 'x2', yref: 'y2', x0: act.interval[0] * 100, x1: act.interval[1] * 100, y0: -4, y1: 40, fillcolor: css('--bracket'), opacity: 0.18, line: { width: 0 } },
        { type: 'line', xref: 'x2', yref: 'y2', x0: win[0] * 100, x1: win[1] * 100, y0: 10, y1: 10, line: { color: css('--critical'), width: 1.2, dash: 'dot' } },
      ];
      lay.annotations = [...lay.annotations,
        { xref: 'paper', yref: 'paper', x: 0.615, y: 0.955, xanchor: 'left', yanchor: 'top', showarrow: false, align: 'left', text: `<b>Zoom: observed 10 MPa onset bracket</b><br>[${pctStrain(act.interval[0])}, ${pctStrain(act.interval[1])}]`, font: { size: 11, color: css('--ink') } },
        { xref: 'x2', yref: 'y2', x: win[0] * 100, y: 10, xanchor: 'left', yanchor: 'bottom', showarrow: false, text: ' 10 MPa tolerance', font: { size: 10, color: css('--critical-ink') } },
      ];
    }
    plot('hero-chart', traces, lay);
  }

  function renderStats() {
    const agg = M.aggregate, a = agg.methods.active;
    const mi = D.posthoc_audit.misses;
    const floor = D.posthoc_audit.noise_floor.expected_mae_of_true_model_mpa;
    const duff = D.oscillator.cases.find(c => c.system === 'duffing_nonlinearity');
    const covered = Math.round(a.reference_onset_coverage_fraction * a.coverage_denominator);
    $('#hero-stats').innerHTML = `
      <div class="stat"><div class="label">Observed onset bracket, 10 probes</div>
        <div class="value">${sci(a.median_bracket_width_strain, 2)} <small>strain</small></div>
        <div class="note">Design resolution of bisection (0.013 / 2⁸), about 28× finer than an equal-budget uniform grid. Contained the noiseless onset in ${covered}/${a.coverage_denominator} recorded seeds. The onset is a 10 MPa error threshold, not the physical yield point.</div></div>
      <div class="stat"><div class="label">Independent audit error, median of ${agg.seed_count} seeds</div>
        <div class="value">${fixed(agg.median_holdout_linear_mae_mpa, 1)} → ${fixed(agg.median_holdout_revised_mae_mpa, 2)} <small>MPa</small></div>
        <div class="note">Uniform and random policies reach the same ${fixed(agg.methods.uniform.holdout_revised_mae_mpa.median, 2)}/${fixed(agg.methods.random.holdout_revised_mae_mpa.median, 2)} MPa: the gain comes from the declared bilinear family. A perfect model scores ${fixed(floor, 2)} MPa at this noise.</div></div>
      <div class="stat"><div class="label">Misses reported as settled, noise 0.8–16 MPa <span class="badge posthoc" style="margin-left:6px">Post-hoc</span></div>
        <div class="value">${mi.missed_reported_resolved} <small>of ${mi.missed} misses</small></div>
        <div class="note">${mi.missed} of ${mi.evaluable_brackets} brackets missed the onset, all in settings where the engine abstained on every run. Abstention is blunt, not discriminating: at 2 MPa bisection also abstained on ${mi.active_2mpa_abstained_while_covering}/30 correct brackets.</div></div>
      <div class="stat"><div class="label">Oscillator: quadratic invariant refuted, quartic revision</div>
        <div class="value mono" style="font-size:18px">Q = v² + ${duff.frozen_models.revised.quadratic.toFixed(3)}x² + ${duff.frozen_models.revised.quartic.toFixed(3)}x⁴</div>
        <div class="note">Recovers the physical ω² = 4 and α/2 = 0.5 noise-free. The damped control is correctly refused a conservation law.</div></div>`;
  }

  function renderWorkflow() {
    const act = M.policies.active, fit = act.fit;
    const firstRef = act.observations.find(o => o.status === REF);
    const stages = [
      ['Observe', `40 readings at strain ${pctStrain(M.discovery.strain[0], 2)}–${pctStrain(M.discovery.strain.at(-1), 2)}`],
      ['Candidate law', `<code>σ = ${sig(M.ehat_mpa, 6)} MPa · ε</code>`],
      ['Choose experiments', 'Bisection: 10 probes × 4 readings, equal budget for every policy'],
      ['Counterexample', `At ${pctStrain(firstRef.strain, 2)} the error is ${sig(firstRef.deviation_mpa, 4)} MPa, far above 10 MPa ${chip(REF)}`],
      ['Validity boundary', `10 MPa onset in [${pctStrain(act.interval[0])}, ${pctStrain(act.interval[1])}] ${boundaryChip(act.boundary_status)}`],
      ['Revise and freeze', `Bilinear: ε<sub>y</sub> = ${pctStrain(fit.yield_strain)}, H = ${sig(fit.hardening_modulus_mpa, 4)} MPa; frozen before audit`],
      ['Independent audit', `249 new readings: MAE ${fixed(M.initial_audit_mae_mpa, 1)} → ${fixed(act.audit_mae_mpa, 2)} MPa ${chip(act.audit_decision.status)}`],
      ['Evidence record', 'Schema-validated JSON with SHA-256-linked raw data'],
    ];
    $('#workflow').innerHTML = stages.map(([t, d], i) => `<div class="stage" tabindex="0" role="link" data-i="${i}"><div class="n">${String(i + 1).padStart(2, '0')}</div><div class="t">${t}</div><div class="d">${d}</div></div>`).join('');
    $$('#workflow .stage').forEach(el => {
      const go = () => { openCertificate('materials'); $('#evidence').scrollIntoView(); };
      el.addEventListener('click', go);
      el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
  }

  // ======================= MATERIALS LAB (LIVE) =======================
  const PRESETS = {
    benchmark: { E: 210000, ey: 0.002, H: 1500 },
    alloy: { E: 70000, ey: 0.0045, H: 3000 },
    dip: { E: 210000, ey: 0.002, H: 1500, dip: { center: 0.0014, halfWidth: 0.0002, depth: 25 } },
  };
  const lab = { policy: 'active', result: null, reveal: 0, phase: 'idle', timer: null, ms: 0, stale: false };
  const PHASES = ['observe', 'probing', 'revise', 'audit', 'done'];

  function labParams() {
    const preset = $('#mat-preset').value;
    const p = preset === 'custom' ? { E: +$('#mat-E').value, ey: +$('#mat-ey').value, H: +$('#mat-H').value } : PRESETS[preset];
    return { ...p, noise: +$('#mat-noise').value, seed: Math.max(0, Math.floor(+$('#mat-seed').value || 0)), preset };
  }
  function syncLabOutputs() {
    $('#mat-noise-out').textContent = `${(+$('#mat-noise').value).toFixed(1)} MPa`;
    $('#mat-E-out').textContent = `${(+$('#mat-E').value / 1000).toFixed(0)} GPa`;
    $('#mat-ey-out').textContent = pctStrain(+$('#mat-ey').value, 2);
    $('#mat-H-out').textContent = `${(+$('#mat-H').value / 1000).toFixed(2)} GPa`;
    $('#mat-custom').open = $('#mat-preset').value === 'custom' || $('#mat-custom').open;
  }
  function compute() {
    const p = labParams();
    if (p.preset === 'custom' && p.H > p.E) throw new Error('Hardening modulus must not exceed the elastic modulus.');
    const t0 = performance.now();
    const sim = FE.material({ E: p.E, ey: p.ey, H: p.H, noise: p.noise, dip: p.dip || null });
    lab.result = FE.runMaterials({ seed: p.seed, sim, noiseSd: p.noise });
    lab.sim = sim;
    lab.ms = performance.now() - t0;
    lab.params = p;
    lab.stale = false;
  }
  function stopTimer() { if (lab.timer) { clearInterval(lab.timer); lab.timer = null; } }
  function advance() {
    if (!lab.result) return false;
    if (lab.phase === 'observe') { lab.phase = 'probing'; lab.reveal = 1; }
    else if (lab.phase === 'probing') { if (lab.reveal < lab.result.strategies[lab.policy].observations.length) lab.reveal++; else lab.phase = 'revise'; }
    else if (lab.phase === 'revise') lab.phase = 'audit';
    else if (lab.phase === 'audit') lab.phase = 'done';
    else return false;
    return true;
  }
  function labRun() {
    stopTimer();
    try { compute(); } catch (err) { labError(err); return; }
    lab.phase = 'observe'; lab.reveal = 0;
    renderLab();
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { while (advance()); renderLab(); return; }
    lab.timer = setInterval(() => { if (!advance()) stopTimer(); renderLab(); }, 380);
  }
  function labStep() {
    stopTimer();
    if (!lab.result || lab.stale || lab.phase === 'done' || lab.phase === 'idle') {
      try { compute(); } catch (err) { labError(err); return; }
      lab.phase = 'observe'; lab.reveal = 0;
    } else advance();
    renderLab();
  }
  function labReset() { stopTimer(); lab.result = null; lab.phase = 'idle'; lab.reveal = 0; renderLab(); }
  function labError(err) {
    $('#mat-verdicts').innerHTML = `<div class="alert bad"><b>Input rejected by the engine.</b> ${esc(err.message)}</div>`;
  }

  function renderLab() {
    const r = lab.result, pol = lab.policy;
    const idx = PHASES.indexOf(lab.phase);
    const s = r && r.strategies[pol];
    const shown = !r ? [] : lab.phase === 'observe' ? [] : lab.phase === 'probing' ? s.observations.slice(0, lab.reveal) : s.observations;
    const probesDone = r && idx >= 2;
    const truth = $('#mat-truth').checked && r && lab.phase === 'done';
    // pipeline chips
    const chips = [['observe', 'Observe 40 readings'], ['fit', 'Fit candidate law'], ['probing', `Probes ${shown.length}/10`], ['revise', 'Revise and freeze'], ['audit', 'Independent audit'], ['done', 'Verdict']];
    $('#mat-pipeline').innerHTML = chips.map(([k], i) => {
      const order = { observe: 0, fit: 0, probing: 1, revise: 2, audit: 3, done: 4 }[k];
      const cls = !r ? '' : idx > order || (k === 'fit' && idx >= 0) || lab.phase === 'done' ? 'done' : idx === order ? 'now' : '';
      return `<span class="${cls}">${chips[i][1]}</span>`;
    }).join('');
    // deviation chart
    const traces = [];
    const shapes = [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 10, y1: 10, line: { color: css('--critical'), width: 1.4, dash: 'dot' } }];
    const ann = [{ xref: 'paper', x: 1, y: Math.log10(10), xanchor: 'right', yanchor: 'bottom', showarrow: false, text: '10 MPa tolerance', font: { size: 11, color: css('--critical-ink') } }];
    if (r) {
      for (const st of [REF, OK, INC]) {
        const g = shown.filter(o => o.status === st);
        if (!g.length) continue;
        traces.push({ x: g.map(o => o.strain * 100), y: g.map(o => Math.max(o.deviation, 0.05)), mode: 'markers+text', name: `Probe: ${statusText(st)}`,
          text: g.map(o => String(o.index + 1)), textposition: 'top center', textfont: { size: 10.5, color: css('--ink-2') },
          marker: { size: 11, ...statusMarker(st) }, customdata: g.map(o => [o.index + 1, o.mean, o.allowance]),
          error_y: { type: 'data', symmetric: false, array: g.map(o => o.allowance), arrayminus: g.map(o => Math.min(o.allowance, Math.max(o.deviation, 0.05) - 0.03)), color: css('--ink-3'), thickness: 1, width: 3 },
          hovertemplate: 'Probe %{customdata[0]} at %{x:.4f}%<br>mean %{customdata[1]:.1f} MPa<br>|error| %{y:.2f} ± %{customdata[2]:.2f} MPa<extra></extra>' });
      }
      if (probesDone && s.interval) shapes.push({ type: 'rect', xref: 'x', yref: 'paper', x0: s.interval[0] * 100, x1: s.interval[1] * 100, y0: 0, y1: 1, fillcolor: css('--bracket'), opacity: 0.2, line: { width: 0 } });
      if (truth) {
        const xs = FE.linspace(0.0009, 0.0141, 500);
        traces.push({ x: xs.map(e => e * 100), y: xs.map(e => Math.max(Math.abs(lab.sim.noiseless(e) - r.ehat * e), 0.05)), mode: 'lines', name: 'Hidden truth: noiseless error (evaluator only)', line: { color: css('--truth'), width: 1.5, dash: 'dash' }, hoverinfo: 'skip' });
        if (r.evaluatorOnset) shapes.push({ type: 'line', xref: 'x', yref: 'paper', x0: r.evaluatorOnset * 100, x1: r.evaluatorOnset * 100, y0: 0, y1: 1, line: { color: css('--truth'), width: 1.2, dash: 'dot' } });
      }
    }
    plot('mat-dev-chart', traces, layout({
      xaxis: axis({ title: { text: 'Engineering strain (%)' }, range: [0.06, 1.46] }),
      yaxis: axis({ title: { text: '|mean − Hooke prediction| (MPa)' }, type: 'log', range: [-1.4, 3.7] }),
      shapes, annotations: ann, legend: { y: -0.22 },
    }));
    // stress-strain chart
    const ss = [];
    if (r) {
      ss.push({ x: r.discovery.strain.map(e => e * 100), y: r.discovery.readings.map(meanOf), mode: 'markers', name: 'Discovery means', marker: { size: 6, color: css('--ink-2') }, hovertemplate: '%{x:.3f}%: %{y:.1f} MPa<extra></extra>' });
      const xs = FE.linspace(0, 0.0145, 300);
      ss.push({ x: xs.map(e => e * 100), y: xs.map(e => r.ehat * e), mode: 'lines', name: 'Candidate: Hooke law', line: { color: css('--initial'), width: 2, dash: 'dash' }, hoverinfo: 'skip' });
      for (const st of [REF, OK, INC]) {
        const g = shown.filter(o => o.status === st);
        if (g.length) ss.push({ x: g.map(o => o.strain * 100), y: g.map(o => o.mean), mode: 'markers', name: `Probe: ${statusText(st)}`, showlegend: false, marker: { size: 10, ...statusMarker(st) }, hovertemplate: 'Probe %{x:.4f}%: %{y:.1f} MPa<extra></extra>' });
      }
      const f = r.fits[pol];
      if (idx >= 2 && f.status === 'FITTED') ss.push({ x: xs.map(e => e * 100), y: xs.map(e => FE.predictBilinear(e, r.ehat, f.ey, f.H)), mode: 'lines', name: 'Revision: bilinear (frozen)', line: { color: css('--revised'), width: 2 }, hoverinfo: 'skip' });
      if (idx >= 3) ss.push({ x: r.holdout.strain.map(e => e * 100), y: r.holdout.mean, mode: 'markers', name: 'Audit means (249 readings)', marker: { size: 5, color: 'rgba(0,0,0,0)', line: { color: css('--audit'), width: 1.3 } }, hovertemplate: 'Audit %{x:.3f}%: %{y:.1f} MPa<extra></extra>' });
      if (truth) ss.push({ x: xs.map(e => e * 100), y: xs.map(e => lab.sim.noiseless(Math.min(e, 0.03))), mode: 'lines', name: 'Hidden truth (evaluator only)', line: { color: css('--truth'), width: 1.5, dash: 'dot' }, hoverinfo: 'skip' });
    }
    const yMax = r ? Math.max(...r.holdout.mean, ...r.discovery.readings.map(meanOf)) * 1.25 + 40 : 600;
    plot('mat-ss-chart', ss, layout({ xaxis: axis({ title: { text: 'Engineering strain (%)' }, range: [-0.02, 1.46] }), yaxis: axis({ title: { text: 'Stress (MPa)' }, range: [-0.04 * yMax, yMax] }), legend: { y: -0.22 } }));
    renderLabVerdicts(shown, truth);
    renderLabLedger(shown);
    renderLabPolicies(truth);
  }

  function renderLabVerdicts(shown, truth) {
    const r = lab.result, pol = lab.policy;
    if (!r) { $('#mat-verdicts').innerHTML = `<div class="verdict"><div class="v muted small">${lab.stale ? 'Settings changed. ' : ''}Press <b>Run experiment</b> to animate a full run, or <b>Step</b> to advance one acquisition at a time.</div></div>`; return; }
    const s = r.strategies[pol], f = r.fits[pol], idx = PHASES.indexOf(lab.phase);
    const firstRef = shown.find(o => o.status === REF);
    const out = [];
    out.push(`<div class="verdict"><div class="k">Candidate law ${firstRef ? chip(REF) : idx >= 2 ? chip(OK, 'No resolved counterexample') : chip('', 'Under test')}</div>
      <div class="v"><span class="mono">σ = ${sig(r.ehat, 6)} MPa · ε</span><br><span class="tiny">Fitted on 40 discovery readings; slope SE ${sig(r.slopeSe, 3)} MPa.${firstRef ? ` First resolved counterexample: probe ${firstRef.index + 1} at ${pctStrain(firstRef.strain, 3)}, error ${sig(firstRef.deviation, 4)} ± ${sig(firstRef.allowance, 2)} MPa.` : ''}</span></div></div>`);
    if (idx >= 2) {
      const why = !s.initialBracketSatisfied ? 'The domain ends did not bracket a pass-to-fail transition, so the engine fell back to uniform probes.'
        : s.nonmonotone ? 'Observed passes and failures contradict the monotonic assumption.'
          : s.uncertainProbes ? `${s.uncertainProbes} probe(s) lie within their uncertainty allowance of the tolerance.` : 'Every probe is resolved beyond its uncertainty allowance.';
      out.push(`<div class="verdict"><div class="k">Validity boundary · ${esc(POL[pol])} ${boundaryChip(s.boundaryStatus)}</div>
        <div class="v">${s.interval ? `10 MPa onset in <b>[${pctStrain(s.interval[0])}, ${pctStrain(s.interval[1])}]</b>, width ${sci(s.width, 3)} strain` : 'No valid empirical bracket.'}<br><span class="tiny">${why} Not a confidence interval, and not the physical yield point.</span></div></div>`);
      out.push(`<div class="verdict"><div class="k">Revision (frozen before audit) ${f.status === 'FITTED' ? chip('', 'Fitted') : chip(INC, 'Declined')}</div>
        <div class="v">${f.status === 'FITTED' ? `Bilinear: ε<sub>y</sub> = ${pctStrain(f.ey)}, H = ${sig(f.H, 4)} MPa` : esc(f.reason)}</div></div>`);
    }
    if (idx >= 3) {
      const a = r.audit[pol];
      out.push(`<div class="verdict"><div class="k">Independent audit · 83 strains × 3 readings</div>
        <div class="v">Hooke law: MAE ${fixed(r.initialAudit.mae, 1)} MPa ${chip(r.initialAudit.status)}<br>Revision: MAE ${a.mae === null ? '—' : fixed(a.mae, 2)} MPa ${chip(a.status)}<br><span class="tiny">Tolerance 10 MPa; abstain if within ±${fixed(a.allowance, 2)} MPa (3·σ/√3). Heuristic, not a calibrated test.</span></div></div>`);
    }
    if (truth) {
      const on = r.evaluatorOnset;
      const missed = s.interval && on !== null && !(s.interval[0] <= on && on <= s.interval[1]);
      const flagged = s.boundaryStatus === INC;
      let box;
      if (on === null && r.evaluatorOnsetBelowRange) box = '<div class="alert info">The noiseless error already exceeds 10 MPa at the lowest probed strain (0.1%), so the true onset lies below the probed range.</div>';
      else if (on === null) box = '<div class="alert info">The noiseless error never exceeds 10 MPa inside the probed range.</div>';
      else if (!s.interval) box = `<div class="alert info">True first 10 MPa exceedance at ${pctStrain(on)}. The engine reported no bracket and abstained.</div>`;
      else if (!missed) box = `<div class="alert ok"><b>Covered.</b> The bracket contains the true first 10 MPa exceedance at ${pctStrain(on)}.</div>`;
      else if (flagged) box = `<div class="alert warn"><b>Missed, but flagged.</b> True onset ${pctStrain(on)} lies outside the bracket; the engine marked the boundary INCONCLUSIVE.</div>`;
      else box = `<div class="alert bad"><b>Silent miss.</b> True first exceedance at ${pctStrain(on)}, yet the engine reported a resolved bracket. Bisection assumed one pass-to-fail transition and never sampled the region where the law first fails. This is the documented monotonic-prior limitation.</div>`;
      const fe = r.fits[pol];
      if (fe.status === 'FITTED' && r.audit[pol].status === OK) {
        let worst = 0;
        for (const e of FE.linspace(0, 0.014, 2801)) worst = Math.max(worst, Math.abs(FE.predictBilinear(e, r.ehat, fe.ey, fe.H) - lab.sim.noiseless(e)));
        if (worst > 10) box += `<div class="alert bad" style="margin-top:8px"><b>The audit passed, but the revision is locally wrong.</b> It errs by up to ${sig(worst, 3)} MPa against the hidden truth. A mean-error audit over 249 readings averages a local failure away.</div>`;
      }
      out.push(`<div class="verdict"><div class="k">Evaluator-only check</div><div class="v">${box}</div></div>`);
    }
    if (lab.phase === 'done') out.push(`<div class="tiny">Live run computed in ${lab.ms.toFixed(0)} ms; the animation replays its acquisition order.</div>`);
    $('#mat-verdicts').innerHTML = out.join('');
  }

  function renderLabLedger(shown) {
    const r = lab.result;
    if (!r) { $('#mat-ledger').innerHTML = '<p class="tiny" style="padding:6px 0">Empty until the first acquisition.</p>'; return; }
    const idx = PHASES.indexOf(lab.phase);
    const rows = [`<tr><td>Setup</td><td>8 strains × 5</td><td class="r">40</td><td>${chip('', 'Shared')}</td></tr>`];
    shown.forEach(o => rows.push(`<tr class="${o.index === shown.length - 1 && lab.phase === 'probing' ? 'new' : ''}"><td>Probe ${o.index + 1}</td><td class="mono">${pctStrain(o.strain, 4)}</td><td class="r">4</td><td>${chip(o.status, o.status === REF ? 'Counterexample' : undefined)} <span class="tiny">${sig(o.deviation, 3)}±${sig(o.allowance, 2)}</span></td></tr>`));
    if (idx >= 2) rows.push(`<tr><td>Other policies</td><td>2 × 10 probes</td><td class="r">80</td><td>${chip('', 'Equal budget')}</td></tr>`, `<tr><td>Freeze</td><td colspan="3">All three revisions frozen; ledger now refuses search data</td></tr>`);
    if (idx >= 3) rows.push(`<tr><td>Audit</td><td>83 strains × 3</td><td class="r">249</td><td>${chip('', 'Holdout')}</td></tr>`);
    const total = 40 + shown.length * 4 + (idx >= 2 ? 80 : 0) + (idx >= 3 ? 249 : 0);
    $('#mat-ledger').innerHTML = `<table><thead><tr><th>Event</th><th>Strain</th><th class="r">Readings</th><th>Outcome (|error|±allowance, MPa)</th></tr></thead><tbody>${rows.join('')}</tbody></table><p class="tiny" style="margin:8px 0 0">Readings so far: <b>${total}</b></p>`;
  }

  function renderLabPolicies(truth) {
    const r = lab.result;
    if (!r || PHASES.indexOf(lab.phase) < 3) { $('#mat-policies').innerHTML = '<p class="tiny" style="padding:6px 0">Shown after the audit. Each policy gets 10 probes × 4 readings and its own measurement stream.</p>'; return; }
    const rows = FE.POLICIES.map(p => {
      const s = r.strategies[p], a = r.audit[p];
      const cov = truth ? (s.covered === null ? '—' : s.covered ? '✓ yes' : (s.boundaryStatus === INC ? '✕ no, flagged' : '✕ no, silent')) : '<span class="tiny">reveal truth</span>';
      return `<tr><td>${POL[p]}<div class="tiny mono">${s.interval ? `${pctStrain(s.interval[0], 3)}–${pctStrain(s.interval[1], 3)}` : 'no bracket'}</div></td><td>${s.boundaryStatus === OK ? chip(OK, 'Resolved') : chip(INC, 'Inconcl.')}</td><td class="r">${a.mae === null ? '—' : fixed(a.mae, 2)}</td><td>${cov}</td></tr>`;
    });
    $('#mat-policies').innerHTML = `<table><thead><tr><th>Policy, bracket</th><th>Status</th><th class="r">Audit MAE</th><th>Covers onset</th></tr></thead><tbody>${rows.join('')}</tbody></table>`;
  }

  function wireLab() {
    syncLabOutputs();
    const markStale = () => { syncLabOutputs(); if (lab.result) { stopTimer(); lab.result = null; lab.stale = true; lab.phase = 'idle'; renderLab(); } };
    ['#mat-preset', '#mat-noise', '#mat-seed', '#mat-E', '#mat-ey', '#mat-H'].forEach(s => $(s).addEventListener('input', markStale));
    $('#mat-preset').addEventListener('change', () => { $('#mat-custom').open = $('#mat-preset').value === 'custom'; });
    $('#mat-run').addEventListener('click', labRun);
    $('#mat-step').addEventListener('click', labStep);
    $('#mat-reset').addEventListener('click', labReset);
    $('#mat-truth').addEventListener('change', renderLab);
    $$('#mat-policy button').forEach(b => b.addEventListener('click', () => {
      $$('#mat-policy button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      lab.policy = b.dataset.v;
      if (lab.result && lab.phase === 'probing') { stopTimer(); lab.phase = 'done'; }
      renderLab();
    }));
  }

  // ======================= OSCILLATOR LAB (LIVE) =======================
  const osc = { system: 'duffing_nonlinearity', noise: 0, result: null };
  function oscRun() {
    const seed = Math.max(0, Math.floor(+$('#osc-seed').value || 0));
    const t0 = performance.now();
    osc.result = FE.runOscillator({ system: osc.system, seed, noiseSd: osc.noise });
    osc.ms = performance.now() - t0;
    renderOsc();
  }
  function decimateIdx(n, m = 700) { const step = Math.max(1, Math.ceil(n / m)); const out = []; for (let i = 0; i < n; i += step) out.push(i); if (out.at(-1) !== n - 1) out.push(n - 1); return out; }
  function renderOsc() {
    const r = osc.result;
    if (!r) return;
    const amps = [0.2, 0.5, 0.9, 1.3, 1.7], hors = [2, 6, 12];
    const z = amps.map(a => hors.map(h => { const c = r.catalog.find(s => s.amplitude === a && s.horizon === h); return c && c.drift !== null ? Math.log10(Math.max(c.drift, 1e-10)) : null; }));
    const dark = css('color-scheme') === 'dark';
    const scale = dark ? [[0, '#1b2a3d'], [0.35, '#184f95'], [0.7, '#3987e5'], [1, '#cde2fb']] : [[0, '#eef4fc'], [0.35, '#9ec5f4'], [0.7, '#3987e5'], [1, '#0d366b']];
    const zmin = -10, zmax = -0.5;
    const ann = [];
    amps.forEach((a, i) => hors.forEach((h, j) => {
      const c = r.catalog.find(s => s.amplitude === a && s.horizon === h);
      const frac = (z[i][j] - zmin) / (zmax - zmin);
      const light = dark ? frac > 0.62 : frac < 0.55;
      const icon = c.status === REF ? '✕ ' : c.status === INC ? '? ' : '';
      ann.push({ x: `${h} s`, y: `${a} m`, text: `${icon}${c.drift === null ? '—' : c.drift < 1e-4 ? sci(c.drift, 1) : (c.drift * 100).toFixed(1) + '%'}`, showarrow: false, font: { size: 11.5, color: light ? '#0b0b0b' : '#fcfcfb' } });
    }));
    const sel = r.counterexamples.length ? r.selected : null;
    const shapes = sel ? [{ type: 'rect', xref: 'x', yref: 'y', x0: hors.indexOf(sel.horizon) - 0.5, x1: hors.indexOf(sel.horizon) + 0.5, y0: amps.indexOf(sel.amplitude) - 0.5, y1: amps.indexOf(sel.amplitude) + 0.5, line: { color: css('--initial'), width: 3 } }] : [];
    plot('osc-catalog', [{ type: 'heatmap', x: hors.map(h => `${h} s`), y: amps.map(a => `${a} m`), z, zmin, zmax, colorscale: scale, xgap: 2, ygap: 2,
      colorbar: { title: { text: 'drift', side: 'right', font: { size: 11 } }, tickvals: [-10, -8, -6, -4, -2, -1], ticktext: ['10⁻¹⁰', '10⁻⁸', '10⁻⁶', '10⁻⁴', '1%', '10%'], thickness: 10, len: 0.9, tickfont: { size: 10.5, color: css('--ink-2') }, outlinewidth: 0 },
      hovertemplate: 'amplitude %{y}, horizon %{x}<br>log₁₀ drift %{z:.2f}<extra></extra>' }],
    layout({ xaxis: axis({ title: { text: 'Observation horizon' }, type: 'category', showgrid: false }), yaxis: axis({ title: { text: 'Initial amplitude' }, type: 'category', showgrid: false }), annotations: ann, shapes, showlegend: false, margin: { l: 70, r: 10, b: 44 } }));
    // phase portrait
    const ph = r.discovery.map((tr, i) => ({ x: tr.x, y: tr.v, mode: 'lines', name: 'Discovery (3 short runs)', legendgroup: 'd', showlegend: i === 0, line: { color: css('--ink-2'), width: 2 }, hoverinfo: 'skip' }));
    if (r.revisionTrajectory) { const ix = decimateIdx(r.revisionTrajectory.x.length, 500); ph.push({ x: ix.map(i => r.revisionTrajectory.x[i]), y: ix.map(i => r.revisionTrajectory.v[i]), mode: 'lines', name: 'Selected counterexample', line: { color: css('--initial'), width: 1.4 }, hoverinfo: 'skip' }); }
    const au = r.audits[0].trajectory, ia = decimateIdx(au.x.length, 600);
    ph.push({ x: ia.map(i => au.x[i]), y: ia.map(i => au.v[i]), mode: 'lines', name: 'Audit trajectory 1', line: { color: css('--audit'), width: 1.2, dash: 'dot' }, hoverinfo: 'skip' });
    plot('osc-phase', ph, layout({ xaxis: axis({ title: { text: 'x (m)' } }), yaxis: axis({ title: { text: 'v (m/s)' } }), legend: { y: -0.3 }, margin: { b: 30 } }));
    // audit drift
    const at = r.audits[0].trajectory, idx = decimateIdx(at.t.length, 800);
    const rel = law => { const q = law.evaluate(at); return idx.map(i => (q[i] - q[0]) / Math.abs(q[0])); };
    const tr = [{ x: idx.map(i => at.t[i]), y: rel(r.quadratic), mode: 'lines', name: 'Initial quadratic', line: { color: css('--initial'), width: 2 }, hovertemplate: 't %{x:.2f} s: %{y:.4f}<extra>quadratic</extra>' }];
    if (r.revised) tr.push({ x: idx.map(i => at.t[i]), y: rel(r.revised), mode: 'lines', name: 'Quartic revision (search-informed)', line: { color: css('--revised'), width: 2 }, hovertemplate: 't %{x:.2f} s: %{y:.2e}<extra>revision</extra>' });
    if (r.noSearch && r.system !== 'harmonic_undamped_control') tr.push({ x: idx.map(i => at.t[i]), y: rel(r.noSearch), mode: 'lines', name: 'Quartic from discovery only (ablation)', line: { color: css('--ink-3'), width: 1.5, dash: 'dash' }, hovertemplate: 't %{x:.2f} s: %{y:.2e}<extra>no-search quartic</extra>' });
    plot('osc-audit', tr, layout({ xaxis: axis({ title: { text: 'Time (s)' } }), yaxis: axis({ title: { text: '(Q − Q(0)) / |Q(0)|' }, zeroline: true, zerolinecolor: css('--line-strong') }), legend: { y: -0.25 } }));
    // verdicts
    const nCe = r.counterexamples.length;
    const auditRow = (name, key, verdict) => `<div>${name}: ${chip(verdict)} <span class="tiny">${r.audits.map(a => (a[key] && a[key].drift !== null ? (a[key].drift * 100 < 0.001 ? sci(a[key].drift, 1) : (a[key].drift * 100).toFixed(2) + '%') : '—')).join(' · ')}</span></div>`;
    const calls = r.ledger.length, readings = r.ledger.reduce((s, e) => s + e.measurements, 0), rhs = r.ledger.reduce((s, e) => s + e.rhs, 0);
    $('#osc-verdicts').innerHTML = `
      <div class="verdict"><div class="k">Candidate law ${chip(r.initialVerdict)}</div><div class="v"><span class="mono">${esc(r.quadratic.expression)}</span><br><span class="tiny">Fitted on 3 short low-amplitude runs; worst training drift ${(Math.max(...r.training.map(t => t.drift || 0)) * 100).toFixed(3)}%.</span></div></div>
      <div class="verdict"><div class="k">Stress catalog ${nCe ? chip(REF, `${nCe}/15 counterexamples`) : chip(OK, 'No counterexample')}</div><div class="v small">${sel ? `Largest drift ${(sel.drift * 100).toFixed(2)}% at ${sel.amplitude} m, ${sel.horizon} s (outlined).` : 'No condition exceeded the 2% threshold beyond its allowance.'}</div></div>
      <div class="verdict"><div class="k">Revision ${r.revised ? chip('', 'Quartic fitted, frozen') : chip('', r.params.revise ? (nCe ? 'Revision failed' : 'Not needed') : 'Not attempted (control)')}</div><div class="v">${r.revised ? `<span class="mono">${esc(r.revised.expression)}</span>` : `<span class="small muted">${r.revisionError ? esc(r.revisionError) : r.params.revise ? 'Revision is attempted only after a resolved counterexample.' : 'The valid control is not revised.'}</span>`}</div></div>
      <div class="verdict"><div class="k">Independent audit · 3 new trajectories</div><div class="v small">${auditRow('Quadratic', 'initial', r.initialVerdict)}${r.revised ? auditRow('Quartic revision', 'revised', r.revisedVerdict) : ''}${r.system !== 'harmonic_undamped_control' ? auditRow('Discovery-only quartic', 'noSearch', r.noSearchVerdict) : ''}</div></div>
      <div class="tiny">Ledger: ${calls} simulator calls, ${readings.toLocaleString('en-US')} state readings, ${rhs.toLocaleString('en-US')} RK4 right-hand-side evaluations. Computed live in ${osc.ms.toFixed(0)} ms.</div>`;
    // disclosure tied to recorded/post-hoc evidence
    const ex = D.posthoc_audit.excitation;
    let text;
    if (r.system === 'duffing_nonlinearity' && osc.noise === 0) text = 'Disclosure: without noise, a quartic fitted on the discovery runs alone also survives every audit (recorded: 30/30). Counterexample search exposes the failed quadratic claim but is not needed to fit the correct family here.';
    else if (r.system === 'duffing_nonlinearity') {
      const row = ex.find(e => e.noise_sd === osc.noise);
      text = row ? `Recorded post-hoc audit at noise ${osc.noise} (30 seeds): the discovery-only quartic was refuted in ${row.none.REFUTED}/30, a random catalog experiment in ${row.random.REFUTED}/30, the search-selected experiment in ${row.search.REFUTED}/30, and a simple "largest amplitude" rule in ${row.largest.REFUTED}/30. Search finds an informative experiment, but not one a physicist would miss. Under noise most verdicts abstain rather than survive.` : '';
    } else if (r.system === 'harmonic_undamped_control') {
      const hn = D.posthoc_audit.harmonic_noise.filter(h => h.noise_sd === 0.01);
      text = `The harmonic control has an exactly quadratic invariant, so the correct outcome is "not refuted". At noise 0.001 it is confirmed in nearly every run. At 0.01 it is never confirmed: the engine usually abstains, but it falsely refutes this valid law in ${hn.map(h => `${h.refuted}/${h.n}`).join(', ')} recorded post-hoc runs (horizon ×${hn.map(h => h.horizon_factor).join(', ×')}). Live seeds show the same failure.`;
    }
    else text = 'The damped control has no conserved polynomial: energy decays at dQ/dt = −2γv². The engine fits the same quartic family and the audit refutes it, so no conservation law is certified. (Drifts tie across amplitudes here because linear damping decays energy at an amplitude-independent rate.)';
    $('#osc-disclosure').textContent = text;
  }
  function wireOsc() {
    const seg = (sel, key, parse) => $$(sel + ' button').forEach(b => b.addEventListener('click', () => {
      $$(sel + ' button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      osc[key] = parse(b.dataset.v);
      oscRun();
    }));
    seg('#osc-system', 'system', v => v);
    seg('#osc-noise', 'noise', v => +v);
    $('#osc-run').addEventListener('click', oscRun);
    $('#osc-seed').addEventListener('change', oscRun);
  }

  // ======================= BENCHMARK (RECORDED) =======================
  const POLCOLOR = () => ({ active: css('--revised'), uniform: css('--initial'), random: css('--audit') });
  function jitter(i, k) { const v = Math.sin((i + 1) * 12.9898 + k * 78.233) * 43758.5453; return (v - Math.floor(v) - 0.5) * 0.36; }
  function renderBenchmark() {
    const seeds = M.per_seed, agg = M.aggregate, col = POLCOLOR();
    const rows = ['random', 'uniform', 'active'];
    plot('bm-width', rows.map((p, k) => ({
      x: seeds.map(s => s[p].width), y: seeds.map((s, i) => k + jitter(i, k)), mode: 'markers', name: POL[p], type: 'scatter',
      marker: { size: 8, color: col[p], line: { width: 1, color: css('--surface') } }, customdata: seeds.map(s => s.seed),
      hovertemplate: `${POL[p]}<br>seed %{customdata}<br>width %{x:.3e}<extra></extra>`,
    })), layout({ xaxis: axis({ title: { text: 'Bracket width (strain)' }, type: 'log', range: [-4.6, -2.4], tickvals: [3e-5, 1e-4, 3e-4, 1e-3, 3e-3], ticktext: ['3×10⁻⁵', '10⁻⁴', '3×10⁻⁴', '10⁻³', '3×10⁻³'] }), yaxis: axis({ tickvals: [0, 1, 2], ticktext: rows.map(p => POL[p]), range: [-0.6, 2.6], showgrid: false }), showlegend: false, margin: { l: 120 },
      annotations: [{ x: Math.log10(0.013 / 256), y: 2.42, text: '0.013 / 2⁸', showarrow: false, font: { size: 11, color: css('--ink-2') } }, { x: Math.log10(0.013 / 9), y: 1.42, text: '0.013 / 9', showarrow: false, font: { size: 11, color: css('--ink-2') } }] }));
    const m = agg.methods;
    $('#bm-width-table').innerHTML = `<table><thead><tr><th>Policy</th><th class="r">Median width</th><th class="r">IQR</th><th class="r">Covers onset</th><th class="r">Inconclusive</th></tr></thead><tbody>${['active', 'uniform', 'random'].map(p => `<tr><td>${POL[p]}</td><td class="r">${sci(m[p].bracket_width_summary.median, 3)}</td><td class="r">${sci(m[p].bracket_width_summary.iqr, 2)}</td><td class="r">${pct(m[p].reference_onset_coverage_fraction)} (n=${m[p].coverage_denominator})</td><td class="r">${pct(m[p].inconclusive_boundary_fraction)}</td></tr>`).join('')}</tbody></table><p class="tiny" style="margin-top:8px">Bisection's width is fixed by design whenever its monotonic assumption holds; the measured outcome is coverage and abstention.</p>`;
    const floor = D.posthoc_audit.noise_floor.expected_mae_of_true_model_mpa;
    const maeRows = [['Initial Hooke law', seeds.map(s => s.linear_mae), css('--initial')], ...['random', 'uniform', 'active'].map(p => [`Revised · ${POL[p]}`, seeds.map(s => s[p].mae), col[p]])];
    plot('bm-mae', maeRows.map(([name, vals, c], k) => ({ x: vals, y: vals.map((_, i) => k + jitter(i, k + 7)), mode: 'markers', name, marker: { size: 8, color: c, line: { width: 1, color: css('--surface') } }, customdata: seeds.map(s => s.seed), hovertemplate: `${name}<br>seed %{customdata}<br>MAE %{x:.3f} MPa<extra></extra>` })),
      layout({ xaxis: axis({ title: { text: 'Audit MAE (MPa, log scale)' }, type: 'log', range: [-0.7, 3.3] }), yaxis: axis({ tickvals: [0, 1, 2, 3], ticktext: maeRows.map(r => r[0]), range: [-0.6, 3.6], showgrid: false }), showlegend: false, margin: { l: 150 },
        shapes: [{ type: 'line', x0: floor, x1: floor, yref: 'paper', y0: 0, y1: 1, line: { color: css('--ink-3'), dash: 'dash', width: 1.2 } }],
        annotations: [{ x: Math.log10(floor), y: 3.5, xanchor: 'left', text: ` noise floor ${floor.toFixed(2)} MPa`, showarrow: false, font: { size: 11, color: css('--ink-2') } }] }));
    $('#bm-mae-note').innerHTML = `Median initial ${fixed(agg.median_holdout_linear_mae_mpa, 1)} MPa; revised ${fixed(m.active.holdout_revised_mae_mpa.median, 3)} (bisection), ${fixed(m.uniform.holdout_revised_mae_mpa.median, 3)} (uniform), ${fixed(m.random.holdout_revised_mae_mpa.median, 3)} (random). The revision family contains the simulator's true form, so every policy reaches the measurement floor.`;
    // noise sweep (post-hoc)
    const sw = D.posthoc_audit.noise_sweep.rows, xs = sw.map(r => r.noise_sd_mpa);
    const ENC = { active: ['circle', 'solid'], uniform: ['square', 'dash'], random: ['diamond', 'dot'] };
    const line = (p, f) => ({ x: xs, y: sw.map(r => f(r[p], r)), mode: 'lines+markers', name: POL[p], line: { color: col[p], width: 2, dash: ENC[p][1] }, marker: { size: 9, symbol: ENC[p][0], color: col[p], line: { width: 1.5, color: css('--surface') } } });
    const covF = (q) => (q.evaluable_brackets ? q.covered / q.evaluable_brackets : null);
    const lab2 = (title) => layout({ xaxis: axis({ title: { text: 'Instrument noise SD (MPa, log scale)' }, type: 'log', tickvals: xs, ticktext: xs.map(String) }), yaxis: axis({ title: { text: title }, range: [-0.04, 1.06], tickformat: '.0%' }), legend: { y: -0.28 } });
    plot('bm-noise-cov', ['active', 'uniform', 'random'].map(p => ({ ...line(p, covF), customdata: sw.map(r => [r[p].covered, r[p].evaluable_brackets]), hovertemplate: `${POL[p]}<br>noise %{x} MPa<br>%{customdata[0]}/%{customdata[1]} covered<extra></extra>` })), lab2('Brackets containing onset'));
    plot('bm-noise-inc', ['active', 'uniform', 'random'].map(p => ({ ...line(p, (q, r) => q.boundary_inconclusive / r.n), customdata: sw.map(r => [r[p].boundary_inconclusive, r.n]), hovertemplate: `${POL[p]}<br>noise %{x} MPa<br>%{customdata[0]}/%{customdata[1]} flagged<extra></extra>` })), lab2('Flagged INCONCLUSIVE'));
    const r8 = sw.find(r => r.noise_sd_mpa === 8), mi = D.posthoc_audit.misses;
    $('#bm-noise-note').innerHTML = `Across ${mi.runs} post-hoc runs (${mi.runs_above_nominal_noise} above the nominal 0.8 MPa), <b>${mi.missed} of ${mi.evaluable_brackets} brackets missed the onset</b>, and <b>${mi.missed_reported_resolved}</b> of those were reported as settled: every miss occurred where the engine abstained on every run. That is conservative, not discriminating. At 2 MPa bisection abstained on ${mi.active_2mpa_abstained_while_covering}/30 brackets that were correct, and the abstention rule is given the true instrument noise SD. The narrow bisection bracket stays accurate up to about 2–4 MPa and then degrades (${r8.active.covered}/${r8.active.evaluable_brackets} at 8 MPa); wide passive brackets keep covering because they are wide. The frozen 3-seed subset reported 1/3 active coverage at 8 MPa.`;
    const fr = D.benchmark.robustness.materials;
    $('#bm-frozen-noise').innerHTML = `<table><thead><tr><th>Noise SD (MPa)</th><th>Policy</th><th class="r">Onset covered</th><th class="r">Boundary inconclusive</th><th class="r">Revised audit inconclusive</th></tr></thead><tbody>${fr.flatMap(r => ['active', 'uniform', 'random'].map(p => `<tr><td>${r.noise_sd_mpa}</td><td>${POL[p]}</td><td class="r">${r.methods[p].reference_onset_coverage_fraction === null ? 'no evaluable bracket' : `${pct(r.methods[p].reference_onset_coverage_fraction, 1)} (n=${r.methods[p].coverage_denominator})`}</td><td class="r">${pct(r.methods[p].inconclusive_boundary_fraction, 1)}</td><td class="r">${pct(r.methods[p].revision_audit_inconclusive_fraction, 1)}</td></tr>`)).join('')}</tbody></table>`;
    // oscillator table
    const os = D.benchmark.oscillator;
    const lbl = { harmonic_undamped_control: 'Harmonic (valid control)', duffing_nonlinearity: 'Duffing', weakly_damped_negative_control: 'Damped (negative control)' };
    $('#bm-osc-sub').textContent = `Seeds ${D.benchmark.seed_ids[0]}–${D.benchmark.seed_ids.at(-1)}, noise-free. The discovery, search and revision steps are deterministic, so each system is one pipeline audited on ${os[0].n} jittered final sets, not ${os[0].n} independent trials.`;
    $('#bm-osc').innerHTML = `<table><thead><tr><th>System</th><th class="r">Quadratic refuted</th><th class="r">Revision survives</th><th class="r">No-search quartic survives</th></tr></thead><tbody>${os.map(r => `<tr><td>${lbl[r.system]}</td><td class="r">${pct(r.initial_refutation_rate)}</td><td class="r">${r.revised_survival_rate === null ? 'not attempted' : pct(r.revised_survival_rate)}</td><td class="r">${pct(r.no_search_quartic_survival_rate)}</td></tr>`).join('')}</tbody></table>
      <p class="tiny" style="margin-top:8px">Median audit drift of the quadratic on Duffing: ${(os[1].initial_drift.median * 100).toFixed(1)}%; of the revision: ${sci(os[1].revised_drift.median, 2)}. Threshold 2% (a demonstration threshold, not a p-value).</p>`;
    const ex = D.posthoc_audit.excitation;
    const vname = { none: 'Discovery only', search: 'Counterexample search', random: 'Random catalog condition', largest: 'Largest amplitude (1.7 m, 12 s)' };
    $('#bm-excite').innerHTML = `<table><thead><tr><th>Extra experiment</th>${ex.map(e => `<th class="r">noise ${e.noise_sd}<br>✕ / ✓ / ?</th><th class="r">x⁴ coef.</th>`).join('')}</tr></thead><tbody>${['none', 'search', 'random', 'largest'].map(k => `<tr><td>${vname[k]}</td>${ex.map(e => `<td class="r">${e[k].REFUTED} / ${e[k].NOT_REFUTED} / ${e[k].INCONCLUSIVE}</td><td class="r">${e[k].quartic_coeff_median === null ? '—' : e[k].quartic_coeff_median.toFixed(3)}</td>`).join('')}</tr>`).join('')}</tbody></table><p class="tiny" style="margin-top:8px">✕ refuted, ✓ not refuted, ? inconclusive; coef. is the median fitted x⁴ coefficient. The search-selected revision is never refuted but is confirmed in only a few runs; most audits abstain. Search spent 15 catalog runs plus 1 and always chose 1.7 m, so one largest-amplitude run (no search) does as well.</p>`;
    $('#bm-solver').innerHTML = `<table><thead><tr><th>System</th><th class="r">rtol</th><th class="r">atol</th><th class="r">Quadratic drift</th><th class="r">Revised drift</th><th>Verdicts</th><th class="r">RHS evaluations</th></tr></thead><tbody>${D.benchmark.solver_sensitivity.map(s => `<tr><td>${lbl[s.system]}</td><td class="r">${s.rtol}</td><td class="r">${s.atol}</td><td class="r">${sci(s.initial_drift, 3)}</td><td class="r">${s.revised_drift === null ? '—' : sci(s.revised_drift, 3)}</td><td>${chip(s.initial_status)} ${s.revised_status ? chip(s.revised_status) : ''}</td><td class="r">${s.rhs_evaluations.toLocaleString('en-US')}</td></tr>`).join('')}</tbody></table><p class="tiny" style="margin-top:8px">The quadratic's physical failure on Duffing (0.22) exceeds numerical drift of the revision by over five orders of magnitude at both tolerances. An independent Radau integrator reproduces the audit drifts to 10⁻⁶.</p>`;
  }

  // ======================= EVIDENCE VIEWER =======================
  const CERTS = [['materials', 'Materials · seed 2026'], ['oscillator', 'Duffing oscillator'], ['harmonic_undamped_control', 'Harmonic control'], ['weakly_damped_negative_control', 'Damped control']];
  let currentCert = 'materials';
  function openCertificate(name) {
    currentCert = name;
    $$('#ev-tabs button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.c === name)));
    renderCertificate();
  }
  function renderEvidenceTabs() {
    $('#ev-tabs').innerHTML = CERTS.map(([k, l]) => `<button type="button" role="tab" data-c="${k}" aria-selected="${k === currentCert}">${l}</button>`).join('');
    $$('#ev-tabs button').forEach(b => b.addEventListener('click', () => openCertificate(b.dataset.c)));
    renderCertificate();
  }
  function renderCertificate() {
    const doc = D.certificates[currentCert];
    const base = '../outputs/certificates/';
    const isMat = doc.physical_system.name === 'synthetic_bilinear_material';
    const costs = Object.entries(doc.resource_costs).map(([p, c]) => `<tr><td>${esc(p)}</td><td class="r">${c.simulator_calls}</td><td class="r">${c.measurements.toLocaleString('en-US')}</td><td class="r">${c.rhs_evaluations.toLocaleString('en-US')}</td></tr>`).join('');
    const parts = Object.entries(doc.partition_manifest.partitions).map(([p, ids]) => `${esc(p)} (${ids.length})`).join(', ');
    const ce = doc.counterexamples;
    const ceText = !ce.length ? 'None observed' : isMat
      ? `${ce.length} resolved probes refute the law; first at strain ${pctStrain(ce[0].strain, 3)}, |error| ${sig(ce[0].absolute_deviation_mpa, 4)} ± ${sig(ce[0].uncertainty_allowance_mpa, 2)} MPa`
      : `${ce.length} of 15 catalog conditions exceed 2% drift; largest ${(Math.max(...ce.map(c => c.relative_drift)) * 100).toFixed(2)}%`;
    const rev = doc.revision;
    const revText = isMat ? (rev.fit.status === 'FITTED' ? `${esc(rev.family)}: ε<sub>y</sub> = ${pctStrain(rev.fit.yield_strain)}, H = ${sig(rev.fit.hardening_modulus_mpa, 5)} MPa, fit RMSE ${sig(rev.fit.fit_rmse_mpa, 3)} MPa` : esc(rev.fit.reason))
      : (rev.coefficients ? `<span class="mono">${esc(rev.expression)}</span>` : 'Not attempted');
    const holdout = isMat ? `${doc.final_holdout.strain.length} strains × ${doc.final_holdout.replicates} readings; MAE ${fixed(doc.metrics.initial_holdout_mae_mpa, 2)} → ${fixed(doc.metrics.revised_holdout_mae_mpa, 3)} MPa`
      : doc.final_holdout.decisions.map((d, i) => `Trajectory ${i + 1}: quadratic ${chip(d.initial.status)}${d.revised ? ` revision ${chip(d.revised.status)}` : ''}`).join('<br>');
    const validity = isMat
      ? `Discovery strain ${doc.validity_domain.discovery_strain.map(e => pctStrain(e, 2)).join('–')}; probed ${doc.validity_domain.probed_strain.map(e => pctStrain(e, 1)).join('–')}; tolerance ${doc.validity_domain.operational_tolerance_mpa} MPa; observed boundary [${doc.validity_domain.empirical_boundary.map(e => pctStrain(e)).join(', ')}] ${boundaryChip(doc.validity_domain.boundary_status)}<br><span class="tiny">${esc(doc.validity_domain.interpretation)}</span>`
      : `Discovery amplitudes ${doc.validity_domain.discovery_amplitudes_m.join(', ')} m over ${doc.validity_domain.discovery_horizon_s} s. Grid: ${doc.validity_domain.sampled_grid.map(g => `${g.horizon_s} s → last pass ${g.last_observed_pass_m ?? '—'} m, first failure ${g.first_observed_failure_m ?? '—'} m`).join('; ')}<br><span class="tiny">${esc(doc.validity_domain.warning)}</span>`;
    const arts = doc.artifacts.map((a, i) => `<tr><td><a href="${esc(base + a.path)}">${esc(a.path)}</a><div class="tiny">${esc(a.kind)} · ${a.bytes.toLocaleString('en-US')} bytes</div></td><td class="hash">${esc(a.sha256)}</td><td><button class="btn secondary" type="button" data-verify="${i}" style="min-height:32px;padding:5px 10px;font-size:12.5px">Verify</button><div class="tiny" id="vr-${i}"></div></td></tr>`).join('');
    const sources = Object.entries(doc.software.source_sha256 || {}).map(([f, h]) => `<tr><td class="mono">${esc(f)}</td><td class="hash">${esc(h)}</td></tr>`).join('');
    const sens = doc.numerical_sensitivity.status === 'MEASURED' ? `Measured at two DOP853 tolerances (${doc.numerical_sensitivity.records.length} records)` : esc(doc.numerical_sensitivity.status);
    $('#ev-panel').innerHTML = `
      <div class="section-head" style="margin-bottom:8px"><div><h3>${esc(doc.physical_system.name)} <span class="tiny">${esc(doc.physical_system.version)}</span></h3>
        <div class="tiny">Run ${esc(doc.run_id)} · schema ${esc(doc.schema_version)} · seed ${doc.seed} · ${esc(doc.created_at_utc)}</div></div>
        <div>Initial claim ${chip(doc.status)} · Revision ${chip(rev.heldout_status)}</div></div>
      <div class="alert info small" style="margin-bottom:10px">Record type: <code>${esc(doc.record_type)}</code>. It shows the run is internally consistent and re-executable; it is not a proof.</div>
      <div class="kv">
        <div>Hypothesis</div><div><span class="mono">${esc(doc.candidate.expression)}</span></div>
        <div>Validity domain</div><div>${validity}</div>
        <div>Selection policy</div><div>${esc(doc.selection_policy.name)}${doc.selection_policy.assumptions.length ? `<br><span class="tiny">Assumes: ${esc(doc.selection_policy.assumptions.join('; '))}</span>` : ''}</div>
        <div>Counterexamples</div><div>${ceText}</div>
        <div>Revision</div><div>${revText} ${chip(rev.heldout_status)}<br><span class="tiny">Frozen before holdout: ${rev.frozen_before_holdout ? 'yes' : 'no'}; fit inputs ${esc((rev.fit_inputs || []).join(', ') || '—')}</span></div>
        <div>Final audit</div><div>${holdout}</div>
        <div>Partitions and freeze</div><div>${parts}<br><span class="tiny">Model freeze after experiment ${doc.partition_manifest.model_freeze.after_experiment}; fingerprint <span class="hash">${esc(doc.partition_manifest.model_freeze.fingerprint)}</span></span></div>
        <div>Measurements and costs</div><div class="table-wrap"><table><thead><tr><th>Partition</th><th class="r">Calls</th><th class="r">Readings</th><th class="r">RHS evals</th></tr></thead><tbody>${costs}</tbody></table></div>
        <div>Numerical sensitivity</div><div>${sens}</div>
        <div>Software</div><div>Git <span class="hash">${esc(doc.software.git_sha || '—')}</span> · Python ${esc(doc.software.python)} · worktree dirty: ${doc.software.git_worktree_dirty ? 'yes' : 'no'}
          <details class="raw"><summary>${Object.keys(doc.software.source_sha256 || {}).length} source file hashes</summary><div class="table-wrap"><table><tbody>${sources}</tbody></table></div></details></div>
        <div>Artifacts</div><div class="table-wrap"><table><tbody>${arts}</tbody></table></div>
        <div>Limitations</div><div><ul style="margin:0;padding-left:18px">${doc.limitations.map(l => `<li>${esc(l)}</li>`).join('')}</ul></div>
        <div>Reproduce</div><div><code>${esc(doc.reproduce)}</code></div>
        <div>Files</div><div><a href="${base}${currentCert}.json">${currentCert}.json</a> · <a href="${base}${currentCert}.md">readable trace</a></div>
      </div>`;
    $$('#ev-panel [data-verify]').forEach(b => b.addEventListener('click', () => verifyArtifact(doc.artifacts[+b.dataset.verify], base, b.dataset.verify)));
  }
  async function verifyArtifact(a, base, i) {
    const out = document.getElementById('vr-' + i);
    out.textContent = 'Hashing…';
    try {
      if (!window.crypto || !crypto.subtle) throw new Error('Web Crypto unavailable (needs https or localhost)');
      const res = await fetch(base + a.path, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const buf = await res.arrayBuffer();
      const hex = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', buf))).map(b => b.toString(16).padStart(2, '0')).join('');
      out.innerHTML = hex === a.sha256 ? '<span class="chip survives">✓ SHA-256 matches</span>' : `<span class="chip refuted">✕ mismatch</span> <span class="hash">${hex}</span>`;
    } catch (err) {
      out.innerHTML = `Could not fetch in this browser (${esc(err.message)}). Opened as a local file? Run <code>python -m falsifylab.verify outputs</code>.`;
    }
  }
  function renderProvenance() {
    const p = D.provenance;
    $('#prov-body').innerHTML = `<p class="small" style="margin-top:10px">Bundle built ${esc(p.built_at_utc)} by <code>site/build.py</code> at commit <code>${esc(p.site_build_commit || '—')}</code>. Evidence generated at commit <code>${esc((p.evidence_git_sha || '—').slice(0, 12))}</code>.</p><div class="table-wrap"><table><thead><tr><th>Input file</th><th>SHA-256</th></tr></thead><tbody>${Object.entries(p.inputs_sha256).map(([f, h]) => `<tr><td><a href="../${esc(f)}">${esc(f)}</a></td><td class="hash">${esc(h)}</td></tr>`).join('')}</tbody></table></div>`;
    $('#footer-build').textContent = `Evidence commit ${(p.evidence_git_sha || '').slice(0, 7)} · page data built ${p.built_at_utc}.`;
  }

  // ======================= LIMITATIONS, REPRODUCE =======================
  function renderLimits() {
    const hn = D.posthoc_audit.hidden_nonmonotonicity, n = D.posthoc_audit.hidden_nonmonotonicity_n;
    const r8 = D.posthoc_audit.noise_sweep.rows.find(r => r.noise_sd_mpa === 8);
    const items = [
      ['Synthetic only', 'Both laboratories are textbook simulators: one bilinear material and three oscillators. Noise seeds repeat measurements of the same system; they are not independent specimens.'],
      ['Predeclared revision families', 'The quartic and bilinear families contain the true generating law. The system revises within a declared family; it does not discover functional forms.'],
      ['Uncalibrated thresholds', 'The 2% drift and 10 MPa tolerances and all uncertainty allowances are demonstration heuristics. No Type-I error control or coverage guarantee is claimed.'],
      ['High-noise failures', `At 8 MPa noise the narrow bisection bracket contains the onset in only ${r8.active.covered}/${r8.active.evaluable_brackets} post-hoc runs. The engine abstains on every run there, so it never reports these misses as settled, but it cannot locate the boundary either.`],
      ['Blunt abstention', `Abstention is conservative, not discriminating: at 2 MPa bisection abstained on ${D.posthoc_audit.misses.active_2mpa_abstained_while_covering}/30 brackets that were correct. The rule is given the true instrument noise SD.`],
      ['False refutation of a valid law', `At 0.01 instrument noise the valid harmonic law is never confirmed, and it is refuted in ${D.posthoc_audit.harmonic_noise.filter(h => h.noise_sd === 0.01).map(h => h.refuted + '/' + h.n).join(', ')} post-hoc runs across three horizons.`],
      ['Mean-error audit misses local failures', `With the hidden softening dip, the frozen revision passes the audit in ${D.posthoc_audit.dip.audit_not_refuted}/${D.posthoc_audit.dip.runs} runs while erring by up to ${D.posthoc_audit.dip.max_local_error_range_mpa[1].toFixed(1)} MPa locally. The audits also interpolate inside the probed range; none tests extrapolation.`],
      ['Monotonic search assumption', `With a hidden pre-yield softening dip, bisection silently missed the true first failure in ${hn.active.silent}/${n} seeds. Random sampling caught the contradiction only occasionally.`],
      ['Onset is not yield', 'The reported boundary is where the fitted Hooke law first errs by 10 MPa, about 0.005% strain past the simulator\'s yield. It is not a yield-strength measurement.'],
      ['No real alloy characterization', 'There is no real measurement, hysteresis, unloading, rate, temperature or microstructure.'],
      ['No mature-method comparison', 'There is no head-to-head with Gaussian-process level-set estimation, SINDy, PySR, POPPER or SciExplorer. Baselines are uniform and random sampling only.'],
      ['Evidence records are not proofs', 'The verifier checks internal consistency against raw data. A fabricated but self-consistent run would also verify; re-running the deterministic benchmark is the stronger check.'],
    ];
    $('#limits-grid').innerHTML = items.map(([h, p]) => `<div class="card limit"><h3>${esc(h)}</h3><p>${esc(p)}</p></div>`).join('');
  }
  function renderRepro() {
    const checks = D.posthoc_audit.checks, pass = checks.filter(c => c.pass).length;
    const L = D.logs || {};
    const row = (label, value, path) => `<tr><td>${label}</td><td>${esc(value || 'not recorded')}</td><td>${path ? `<a href="../${esc(path)}">log</a>` : ''}</td></tr>`;
    $('#repro-checks').innerHTML = `<table><tbody>
      ${row('Test suite', L.pytest && L.pytest.summary, L.pytest && L.pytest.path)}
      ${row('Evidence verifier', L.verify && L.verify.summary, L.verify && L.verify.path)}
      ${row('Independent numerical audit', `${pass}/${checks.length} checks pass`, 'audit/independent_checks.json')}
      ${row('Browser engine parity', L.parity && L.parity.summary, L.parity && L.parity.path)}
      ${row('Benchmark rerun', L.rerun && L.rerun.summary, L.rerun && L.rerun.path)}
    </tbody></table>`;
  }

  // ======================= chrome =======================
  function wireTheme() {
    const root = document.documentElement;
    try { const saved = localStorage.getItem('falsifylab-theme'); if (saved) root.dataset.theme = saved; } catch (e) { /* storage unavailable */ }
    $('#theme-toggle').addEventListener('click', () => {
      const dark = css('color-scheme') === 'dark';
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('falsifylab-theme', root.dataset.theme); } catch (e) { /* ignore */ }
      renderers.forEach(r => r());
    });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => renderers.forEach(r => r()));
  }
  function wireNav() {
    if (!('IntersectionObserver' in window)) return;
    const links = $$('.nav a');
    const io = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id));
    }), { rootMargin: '-45% 0px -50% 0px' });
    links.forEach(a => { const t = document.querySelector(a.getAttribute('href')); if (t) io.observe(t); });
    const top = document.getElementById('top');
    if (top) io.observe(top);
  }

  function boot() {
    if (!D || !FE) {
      document.querySelector('main').insertAdjacentHTML('afterbegin', '<div class="error-box" style="margin-top:20px">Evidence bundle or engine failed to load. Run <code>python site/build.py</code> and serve the repository root.</div>');
      return;
    }
    wireTheme();
    panel('hero-stats', renderStats);
    panel('hero-chart', renderHero);
    panel('workflow', renderWorkflow);
    wireLab();
    panel('mat-verdicts', renderLab);
    wireOsc();
    panel('osc-verdicts', oscRun);
    panel('bm-width', renderBenchmark);
    panel('ev-panel', renderEvidenceTabs);
    panel('prov-body', renderProvenance);
    panel('limits-grid', renderLimits);
    panel('repro-checks', renderRepro);
    wireNav();
    let t;
    window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => { try { renderHero(); } catch (err) { console.error(err); } }, 250); });
    window.FalsifyLabUI = { lab, osc, labRun, labStep, oscRun, openCertificate };
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
