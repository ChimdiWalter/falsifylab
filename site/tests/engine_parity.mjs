// Parity test: replay recorded Python measurements through site/assets/engine.js
// and require the same decisions, brackets, fits and audit errors.
// Run: node site/tests/engine_parity.mjs   (after python site/tests/make_parity_fixtures.py)
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const E = require('../assets/engine.js');
const fx = JSON.parse(readFileSync(new URL('./fixtures/parity.json', import.meta.url)));

let failures = 0, checks = 0;
const worst = {};
function ok(cond, msg) { checks++; if (!cond) { failures++; if (failures < 25) console.log('FAIL', msg); } }
function rel(a, b) { return Math.abs(a - b) / Math.max(Math.abs(b), 1e-12); }
function track(key, v) { worst[key] = Math.max(worst[key] || 0, v); }
const sameInterval = (a, b, tol = 1e-12) => (a === null || b === null) ? a === b : Math.abs(a[0] - b[0]) < tol && Math.abs(a[1] - b[1]) < tol;

for (const c of fx.materials) {
  const tag = `materials seed ${c.seed} noise ${c.noise_sd}`;
  const sim = E.material({ noise: c.noise_sd });
  const res = E.runMaterials({ seed: c.seed, sim, noiseSd: c.noise_sd, replay: c.replay });
  const x = c.expected;
  ok(rel(res.ehat, x.ehat) < 1e-12, `${tag} ehat ${res.ehat} vs ${x.ehat}`); track('ehat_rel', rel(res.ehat, x.ehat));
  ok(x.slope_se < 1e-9 ? Math.abs(res.slopeSe - x.slope_se) < 1e-6 : rel(res.slopeSe, x.slope_se) < 1e-10, `${tag} slope se`);
  ok(rel(res.initialAudit.mae, x.initial_mae) < 1e-10, `${tag} initial MAE`);
  ok(res.initialAudit.status === x.initial_decision, `${tag} initial decision`);
  for (const p of E.POLICIES) {
    const s = res.strategies[p], xs = x.strategies[p];
    ok(s.observations.length === xs.strains.length && s.observations.every((o, i) => Math.abs(o.strain - xs.strains[i]) < 1e-15), `${tag} ${p} probe strains`);
    ok(s.observations.every((o, i) => o.status === xs.statuses[i]), `${tag} ${p} probe statuses`);
    ok(sameInterval(s.interval, xs.interval), `${tag} ${p} interval ${JSON.stringify(s.interval)} vs ${JSON.stringify(xs.interval)}`);
    ok(sameInterval(s.uncertaintyInterval, xs.uncertainty_interval), `${tag} ${p} uncertainty interval`);
    ok(s.boundaryStatus === xs.boundary_status, `${tag} ${p} boundary status`);
    ok(s.nonmonotone === xs.nonmonotone, `${tag} ${p} nonmonotone`);
    const f = res.fits[p], xf = x.fits[p];
    ok(f.status === xf.status, `${tag} ${p} fit status ${f.status} vs ${xf.status} (${f.reason || ''} / ${xf.reason || ''})`);
    if (f.status === 'FITTED' && xf.status === 'FITTED') {
      track('yield_rel', rel(f.ey, xf.yield_strain));
      track('hardening_abs_mpa', Math.abs(f.H - xf.hardening_modulus_mpa));
      ok(rel(f.ey, xf.yield_strain) < 1e-4, `${tag} ${p} fitted yield ${f.ey} vs ${xf.yield_strain}`);
      ok(Math.abs(res.audit[p].mae - x.mae[p]) < 0.02, `${tag} ${p} audit MAE ${res.audit[p].mae} vs ${x.mae[p]}`);
      track('audit_mae_abs_mpa', Math.abs(res.audit[p].mae - x.mae[p]));
    }
    ok(res.audit[p].status === x.decisions[p], `${tag} ${p} audit decision ${res.audit[p].status} vs ${x.decisions[p]}`);
  }
}

for (const c of fx.oscillator) {
  const tag = `oscillator ${c.system}`;
  // Replay the recorded selection when the two largest catalog drifts tie within 1e-6 (relative).
  const ranked = [...c.catalog].map(s => s.drift).sort((a, b) => b - a);
  const tie = Math.abs(ranked[0] - ranked[1]) <= 1e-6 * Math.max(ranked[0], 1e-12) || ranked[0] < 1e-6;
  const res = E.runOscillator({ system: c.system, seed: c.seed, auditAmplitudes: c.audit_amplitudes, selectedOverride: tie ? c.selected : null });
  if (tie) console.log(`note: ${tag} catalog drifts tie (top two ${ranked[0]}, ${ranked[1]}); recorded selection replayed`);
  const fm = c.frozen_models;
  ok(Math.abs(res.quadratic.a - fm.initial.quadratic) < 1e-7, `${tag} quadratic ${res.quadratic.a} vs ${fm.initial.quadratic}`);
  track('quadratic_abs', Math.abs(res.quadratic.a - fm.initial.quadratic));
  if (fm.revised) {
    ok(res.revised && Math.abs(res.revised.a - fm.revised.quadratic) < 1e-6 && Math.abs(res.revised.b - fm.revised.quartic) < 1e-6, `${tag} revised coefficients`);
    track('revised_abs', Math.max(Math.abs(res.revised.a - fm.revised.quadratic), Math.abs(res.revised.b - fm.revised.quartic)));
  } else ok(res.revised === null, `${tag} no revision expected`);
  ok(res.catalog.every((s, i) => s.status === c.catalog[i].status), `${tag} catalog statuses`);
  res.catalog.forEach((s, i) => { if (c.catalog[i].drift > 1e-6) track('catalog_drift_rel', rel(s.drift, c.catalog[i].drift)); });
  ok(res.catalog.every((s, i) => c.catalog[i].drift < 1e-6 ? s.drift < 1e-6 : rel(s.drift, c.catalog[i].drift) < 1e-5), `${tag} catalog drifts`);
  ok(res.selected.amplitude === c.selected[0] && res.selected.horizon === c.selected[1], `${tag} selected counterexample`);
  res.audits.forEach((a, i) => {
    for (const [k, key] of [['initial', 'initial'], ['revised', 'revised'], ['noSearch', 'no_search_quartic']]) {
      const xa = c.audits[i][key];
      if (!xa) { ok(a[k] === null, `${tag} audit ${i} ${k} absent`); continue; }
      ok(a[k].status === xa.status, `${tag} audit ${i} ${k} status ${a[k].status} vs ${xa.status}`);
      if (xa.drift > 1e-6) { ok(rel(a[k].drift, xa.drift) < 1e-5, `${tag} audit ${i} ${k} drift`); track('audit_drift_rel', rel(a[k].drift, xa.drift)); }
      else ok(a[k].drift < 1e-6, `${tag} audit ${i} ${k} small drift ${a[k].drift}`);
    }
  });
  ok(res.initialVerdict === c.initial_verdict, `${tag} initial verdict`);
  ok((res.revisedVerdict || null) === (c.revised_verdict || null), `${tag} revised verdict`);
}

console.log(`engine parity: ${checks - failures}/${checks} checks pass over ${fx.materials.length} material runs and ${fx.oscillator.length} oscillator cases`);
console.log('worst deviations:', JSON.stringify(worst));
process.exit(failures ? 1 : 0);
