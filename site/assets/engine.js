/* FalsifyLab browser mirror of the Python engine (falsifylab/*.py, frozen at 63c686c).
 *
 * Used only for LIVE exploration in the workbench. It ports the same decision
 * rules, budgets, thresholds and fitting families. Differences from Python:
 *  - random numbers come from a seeded mulberry32 + Box-Muller generator, not NumPy,
 *    so live runs never reproduce the recorded seeds number-for-number;
 *  - the bilinear fit profiles the hardening slope in closed form and searches the
 *    change point on a grid with golden-section refinement (Python: multi-start
 *    bounded least squares);
 *  - trajectories use fixed-step RK4 (Python: adaptive DOP853).
 * site/tests/engine_parity.mjs checks this file against the recorded Python runs.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FalsifyEngine = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const REFUTED = 'REFUTED';
  const SURVIVES = 'NOT_REFUTED_UNDER_TESTED_CONDITIONS';
  const INCONCLUSIVE = 'INCONCLUSIVE';

  // ---------- seeded randomness ----------
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function makeRng(...keys) {
    let h = 2166136261;
    for (const k of keys) {
      const s = String(k);
      for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
      h ^= 0x9e3779b9; h = Math.imul(h, 16777619);
    }
    const u = mulberry32(h >>> 0);
    let spare = null;
    return {
      uniform: (lo = 0, hi = 1) => lo + (hi - lo) * u(),
      normal(mu = 0, sd = 1) {
        if (sd === 0) return mu;
        if (spare !== null) { const z = spare; spare = null; return mu + sd * z; }
        let a, b, s;
        do { a = 2 * u() - 1; b = 2 * u() - 1; s = a * a + b * b; } while (s >= 1 || s === 0);
        const m = Math.sqrt(-2 * Math.log(s) / s);
        spare = b * m;
        return mu + sd * a * m;
      },
    };
  }

  // ---------- small numeric helpers ----------
  const sum = a => a.reduce((s, v) => s + v, 0);
  const mean = a => sum(a) / a.length;
  const ptp = a => Math.max(...a) - Math.min(...a);
  const linspace = (a, b, n) => Array.from({ length: n }, (_, i) => (n === 1 ? a : a + (b - a) * i / (n - 1)));
  function stdDdof1(a) { const m = mean(a); return Math.sqrt(sum(a.map(v => (v - m) ** 2)) / (a.length - 1)); }

  // ======================= MATERIALS =======================
  const M = { MIN_EPS: 0.001, MAX_EPS: 0.014, BUDGET: 10, REPLICATES: 4, TOLERANCE_MPA: 10.0 };
  const POLICIES = ['active', 'uniform', 'random'];

  function material({ E = 210000, ey = 0.002, H = 1500, noise = 0.8, dip = null } = {}) {
    if (!(E > 0) || !(ey > 0 && ey <= 0.03) || !(H >= 0 && H <= E) || !(noise >= 0)) throw new Error('Invalid elastic/plastic parameters or noise');
    const noiseless = e => {
      if (!(e >= 0 && e <= 0.03)) throw new Error('Strain must lie in [0, 0.03]');
      let s = E * Math.min(e, ey) + H * Math.max(e - ey, 0);
      if (dip) s -= dip.depth * Math.max(0, 1 - Math.abs(e - dip.center) / dip.halfWidth);
      return s;
    };
    return {
      E, ey, H, noise, dip, noiseless,
      observe: (strains, rng, reps) => strains.map(e => Array.from({ length: reps }, () => noiseless(e) + rng.normal(0, noise))),
    };
  }

  function fitHooke(strains, readings) {
    let xy = 0, xx = 0;
    strains.forEach((x, i) => readings[i].forEach(y => { xy += x * y; xx += x * x; }));
    if (xx < 1e-12) throw new Error('Insufficient strain signal');
    const slope = xy / xx;
    if (!(slope > 0) || !isFinite(slope)) throw new Error('Unphysical or unstable elastic slope');
    return slope;
  }

  function hookeUncertainty(strains, readings, slope, noiseSd) {
    let ss = 0, xx = 0, n = 0;
    strains.forEach((x, i) => readings[i].forEach(y => { ss += (y - slope * x) ** 2; xx += x * x; n++; }));
    const sd = Math.max(noiseSd, Math.sqrt(ss / Math.max(n - 1, 1)));
    return sd / Math.sqrt(xx);
  }

  /** Mirror of run_materials.search_boundary. `observe(e)` returns REPLICATES readings. */
  function searchBoundary(observe, E, strategy, { slopeSe = 0, noiseSd = 0.8, selectionRng = makeRng(0), locations = null, onProbe = null } = {}) {
    if (!POLICIES.includes(strategy) || !(E > 0)) throw new Error('Invalid strategy or slope');
    const observations = [];
    const query = e => {
      const values = observe(e);
      const m = mean(values);
      const deviation = Math.abs(m - E * e);
      const sd = Math.max(noiseSd, stdDdof1(values));
      const allowance = 3 * Math.hypot(sd / Math.sqrt(M.REPLICATES), e * slopeSe);
      const nominalFailure = deviation > M.TOLERANCE_MPA;
      const status = deviation - allowance > M.TOLERANCE_MPA ? REFUTED : deviation + allowance <= M.TOLERANCE_MPA ? SURVIVES : INCONCLUSIVE;
      const obs = { strain: e, readings: values, mean: m, deviation, allowance, rejected: nominalFailure, status, index: observations.length };
      observations.push(obs);
      if (onProbe) onProbe(obs);
      return nominalFailure;
    };
    const loFail = query(M.MIN_EPS), hiFail = query(M.MAX_EPS);
    const bracketOk = !loFail && hiFail;
    if (strategy === 'active' && bracketOk) {
      let lower = M.MIN_EPS, upper = M.MAX_EPS;
      for (let k = 0; k < M.BUDGET - 2; k++) {
        const middle = (lower + upper) / 2;
        if (query(middle)) upper = middle; else lower = middle;
      }
    } else {
      const locs = locations || (strategy === 'random'
        ? Array.from({ length: M.BUDGET - 2 }, () => selectionRng.uniform(M.MIN_EPS, M.MAX_EPS))
        : linspace(M.MIN_EPS, M.MAX_EPS, M.BUDGET).slice(1, -1));
      locs.forEach(e => query(e));
    }
    const passes = observations.filter(o => !o.rejected).map(o => o.strain);
    const fails = observations.filter(o => o.rejected).map(o => o.strain);
    const nonmono = passes.length > 0 && fails.length > 0 && Math.max(...passes) >= Math.min(...fails);
    const valid = bracketOk && passes.length > 0 && fails.length > 0 && !nonmono;
    const bounds = valid ? [Math.max(...passes), Math.min(...fails)] : null;
    const cp = observations.filter(o => o.status === SURVIVES).map(o => o.strain);
    const cf = observations.filter(o => o.status === REFUTED).map(o => o.strain);
    const uncertaintyBounds = cp.length && cf.length && Math.max(...cp) < Math.min(...cf) ? [Math.max(...cp), Math.min(...cf)] : null;
    const uncertain = observations.filter(o => o.status === INCONCLUSIVE).length;
    return {
      strategy, probes: observations.length, measurements: observations.length * M.REPLICATES,
      interval: bounds, width: bounds ? bounds[1] - bounds[0] : null,
      boundaryStatus: valid && !uncertain ? SURVIVES : INCONCLUSIVE,
      uncertaintyInterval: uncertaintyBounds, uncertainProbes: uncertain,
      initialBracketSatisfied: bracketOk, nonmonotone: nonmono, observations,
    };
  }

  function predictBilinear(e, E, ey, H) { return E * Math.min(e, ey) + H * Math.max(e - ey, 0); }

  /** Mirror of materials.fit_bilinear: modulus fixed, fit (yield strain, hardening). */
  function fitBilinear(x, y, E) {
    if (x.length < 4 || !(E > 0)) throw new Error('At least four paired means and positive modulus required');
    if (Math.max(...x.map((xi, i) => Math.abs(y[i] - E * xi))) < 1e-6) throw new Error('No identifiable change point in a linear response');
    const ub = Math.max(Math.max(...x) * 1.001, 1e-5), lb = 1e-6;
    const profile = ey => {
      let num = 0, den = 0;
      x.forEach((xi, i) => { const d = Math.max(xi - ey, 0); num += (y[i] - E * Math.min(xi, ey)) * d; den += d * d; });
      const H = den > 0 ? Math.min(Math.max(num / den, 0), E) : 0;
      let sse = 0;
      x.forEach((xi, i) => { sse += (predictBilinear(xi, E, ey, H) - y[i]) ** 2; });
      return { ey, H, sse };
    };
    // Grid over the change point, then golden-section refinement around the best cell.
    const grid = linspace(lb, ub, 4001).map(profile);
    let k = 0;
    grid.forEach((g, i) => { if (g.sse < grid[k].sse) k = i; });
    let a = grid[Math.max(k - 1, 0)].ey, b = grid[Math.min(k + 1, grid.length - 1)].ey;
    const phi = (Math.sqrt(5) - 1) / 2;
    let c = b - phi * (b - a), d = a + phi * (b - a), fc = profile(c), fd = profile(d);
    for (let it = 0; it < 120; it++) {
      if (fc.sse < fd.sse) { b = d; d = c; fd = fc; c = b - phi * (b - a); fc = profile(c); }
      else { a = c; c = d; fc = fd; d = a + phi * (b - a); fd = profile(d); }
    }
    let best = [grid[k], fc, fd].reduce((p, q) => (q.sse < p.sse ? q : p));
    // Identifiability: normalized Jacobian columns d/d(ey) and d/dH.
    const j1 = x.map(xi => (xi < best.ey ? E : 0) - (xi > best.ey ? best.H : 0));
    const j2 = x.map(xi => Math.max(xi - best.ey, 0));
    const n1 = Math.hypot(...j1), n2 = Math.hypot(...j2);
    if (n1 < 1e-10 || n2 < 1e-10) throw new Error('Unidentifiable/ill-conditioned bilinear fit');
    const g12 = sum(j1.map((v, i) => v * j2[i])) / (n1 * n2);
    const cond = Math.sqrt((1 + Math.abs(g12)) / Math.max(1 - Math.abs(g12), 1e-300));
    if (cond > 1e8) throw new Error('Unidentifiable/ill-conditioned bilinear fit');
    if (x.filter(v => v > best.ey).length < 2 || x.filter(v => v < best.ey).length < 1) throw new Error('Insufficient observations on both sides of change point');
    return { ey: best.ey, H: best.H, rmse: Math.sqrt(best.sse / x.length) };
  }

  function maeDecision(mae, noiseSd, replicates = 3, tolerance = 10) {
    const allowance = 3 * noiseSd / Math.sqrt(replicates);
    let status;
    if (mae === null || Math.abs(mae - tolerance) <= allowance) status = INCONCLUSIVE;
    else status = mae > tolerance ? REFUTED : SURVIVES;
    return { mae, allowance, status, tolerance };
  }

  const HOLDOUT_STRAIN = linspace(0.000161, M.MAX_EPS - 0.000219, 83);
  const DISCOVERY_STRAIN = linspace(0.0002, 0.0008, 8);

  /** Mirror of run_materials.run. `replay` (tests only) supplies recorded readings. */
  function runMaterials({ seed = 2026, sim = material(), noiseSd = sim.noise, replay = null, onProbe = null } = {}) {
    const ledger = [];
    let frozen = null;
    const rngs = Object.fromEntries(['discovery', ...POLICIES, 'holdout'].map(n => [n, makeRng(seed, 1729, n)]));
    const acquire = (partition, strains, reps, readings) => {
      if (partition === 'holdout' && !frozen) throw new Error('Models must be frozen before holdout acquisition');
      if (partition !== 'holdout' && ledger.some(e => e.partition === 'holdout')) throw new Error('Cannot acquire fitting/search data after final audit');
      ledger.push({ id: 'e' + String(ledger.length).padStart(4, '0'), partition, strains, readings, measurements: strains.length * reps });
      return readings;
    };
    const disc = acquire('discovery', DISCOVERY_STRAIN, 5, replay ? replay.discovery : sim.observe(DISCOVERY_STRAIN, rngs.discovery, 5));
    const ehat = fitHooke(DISCOVERY_STRAIN, disc);
    const slopeSe = hookeUncertainty(DISCOVERY_STRAIN, disc, ehat, noiseSd);
    const strategies = {}, fits = {};
    POLICIES.forEach((name, i) => {
      let cursor = 0;
      const observe = e => {
        const r = replay ? replay.probes[name][cursor++] : sim.observe([e], rngs[name], M.REPLICATES)[0];
        acquire('probe_' + name, [e], M.REPLICATES, [r]);
        return r;
      };
      const s = searchBoundary(observe, ehat, name, {
        slopeSe, noiseSd, selectionRng: makeRng(seed, 4793, i),
        locations: replay && name === 'random' ? replay.randomLocations : null,
        onProbe: onProbe ? o => onProbe(name, o) : null,
      });
      strategies[name] = s;
      try {
        if (!s.observations.some(o => o.status === REFUTED)) throw new Error('No uncertainty-resolved counterexample: decline revision');
        const fit = fitBilinear(s.observations.map(o => o.strain), s.observations.map(o => o.mean), ehat);
        fits[name] = { status: 'FITTED', ...fit };
      } catch (err) {
        fits[name] = { status: INCONCLUSIVE, reason: err.message };
      }
    });
    frozen = JSON.parse(JSON.stringify({ ehat, fits }));
    const hold = acquire('holdout', HOLDOUT_STRAIN, 3, replay ? replay.holdout : sim.observe(HOLDOUT_STRAIN, rngs.holdout, 3));
    const holdMean = replay && replay.holdoutIsMean ? hold : hold.map(r => mean(r));
    const initialMae = mean(HOLDOUT_STRAIN.map((e, i) => Math.abs(ehat * e - holdMean[i])));
    const audit = {};
    POLICIES.forEach(name => {
      const f = fits[name];
      const mae = f.status === 'FITTED' ? mean(HOLDOUT_STRAIN.map((e, i) => Math.abs(predictBilinear(e, ehat, f.ey, f.H) - holdMean[i]))) : null;
      audit[name] = maeDecision(mae, noiseSd);
    });
    // EVALUATOR ONLY: first noiseless 10 MPa exceedance for the fitted slope (dense scan + bisection).
    let onset = null;
    const dev = e => Math.abs(sim.noiseless(e) - ehat * e) - M.TOLERANCE_MPA;
    const onsetBelowRange = dev(M.MIN_EPS) >= 0;
    if (!onsetBelowRange) {
      const n = 26000;
      for (let i = 1; i <= n; i++) {
        const e1 = M.MIN_EPS + (M.MAX_EPS - M.MIN_EPS) * i / n;
        if (dev(e1) > 0) {
          let lo = M.MIN_EPS + (M.MAX_EPS - M.MIN_EPS) * (i - 1) / n, hi = e1;
          for (let k = 0; k < 80; k++) { const mid = (lo + hi) / 2; if (dev(mid) > 0) hi = mid; else lo = mid; }
          onset = (lo + hi) / 2;
          break;
        }
      }
    }
    for (const s of Object.values(strategies)) s.covered = s.interval && onset !== null ? s.interval[0] <= onset && onset <= s.interval[1] : null;
    const costs = {};
    ledger.forEach(e => { costs[e.partition] = costs[e.partition] || { calls: 0, measurements: 0 }; costs[e.partition].calls++; costs[e.partition].measurements += e.measurements; });
    return {
      seed, noiseSd, ehat, slopeSe, discovery: { strain: DISCOVERY_STRAIN, readings: disc },
      strategies, fits, frozen, holdout: { strain: HOLDOUT_STRAIN, mean: holdMean },
      initialAudit: maeDecision(initialMae, noiseSd), audit, evaluatorOnset: onset, evaluatorOnsetBelowRange: onsetBelowRange, ledger, costs,
    };
  }

  // ======================= OSCILLATOR =======================
  const THRESHOLD = 0.02;

  function simulate({ amplitude, v0 = 0, omega = 2, alpha = 0, gamma = 0, horizon = 8, steps = 501, h = 5e-4 }) {
    if (!(horizon > 0) || !(omega > 0) || steps < 4 || gamma < 0) throw new Error('Invalid simulation parameters');
    const f = (x, v) => -(omega * omega) * x - alpha * x * x * x - gamma * v;
    const t = linspace(0, horizon, steps), X = [amplitude], V = [v0];
    let x = amplitude, v = v0, rhs = 0;
    for (let i = 1; i < steps; i++) {
      const dt = t[i] - t[i - 1], n = Math.max(1, Math.ceil(dt / h)), s = dt / n;
      for (let k = 0; k < n; k++) {
        const k1x = v, k1v = f(x, v);
        const k2x = v + 0.5 * s * k1v, k2v = f(x + 0.5 * s * k1x, v + 0.5 * s * k1v);
        const k3x = v + 0.5 * s * k2v, k3v = f(x + 0.5 * s * k2x, v + 0.5 * s * k2v);
        const k4x = v + s * k3v, k4v = f(x + s * k3x, v + s * k3v);
        x += s / 6 * (k1x + 2 * k2x + 2 * k3x + k4x);
        v += s / 6 * (k1v + 2 * k2v + 2 * k3v + k4v);
        rhs += 4;
      }
      X.push(x); V.push(v);
    }
    return { t, x: X, v: V, rhs };
  }

  function hypothesis(a, b = 0) {
    if (!(a > 0) || !isFinite(b)) throw new Error('Finite coefficients and positive quadratic stiffness required');
    return {
      a, b,
      evaluate: tr => tr.x.map((x, i) => tr.v[i] ** 2 + a * x * x + b * x ** 4),
      expression: Math.abs(b) < 1e-8 ? `Q = v² + ${a.toFixed(6)} x²` : `Q = v² + ${a.toFixed(6)} x² ${b < 0 ? '−' : '+'} ${Math.abs(b).toFixed(6)} x⁴`,
    };
  }

  /** Mirror of hypothesis.fit_hypothesis: v² coefficient fixed to 1, centered per trajectory. */
  function fitHypothesis(trajs, degree) {
    if (![2, 4].includes(degree) || !trajs.length) throw new Error('Use degree 2 or 4 with nonempty observations');
    const c1 = [], c2 = [], yv = [];
    for (const tr of trajs) {
      if (ptp(tr.x) <= 1e-10 || ptp(tr.v) <= 1e-10) throw new Error('No excitation: stationary/zero trajectories cannot identify an invariant');
      const x2 = tr.x.map(x => x * x), x4 = tr.x.map(x => x ** 4), v2 = tr.v.map(v => v * v);
      const m2 = mean(x2), m4 = mean(x4), mv = mean(v2);
      x2.forEach((v, i) => { c1.push(v - m2); c2.push(x4[i] - m4); yv.push(-(v2[i] - mv)); });
    }
    const dot = (p, q) => sum(p.map((v, i) => v * q[i]));
    const s11 = dot(c1, c1), s22 = dot(c2, c2), s12 = dot(c1, c2), y1 = dot(c1, yv), y2 = dot(c2, yv);
    if (degree === 2) {
      if (s11 <= 1e-24) throw new Error('Not enough excitation to identify hypothesis');
      return hypothesis(y1 / s11, 0);
    }
    if (s11 <= 1e-24 || s22 <= 1e-24) throw new Error('Not enough excitation to identify hypothesis');
    const r = s12 / Math.sqrt(s11 * s22);
    const cond = Math.sqrt((1 + Math.abs(r)) / Math.max(1 - Math.abs(r), 1e-300));
    if (cond > 1e8) throw new Error('Ill-conditioned hypothesis design');
    const det = s11 * s22 - s12 * s12;
    return hypothesis((y1 * s22 - y2 * s12) / det, (y2 * s11 - y1 * s12) / det);
  }

  function driftDecision(law, tr, noiseSd = 0, threshold = THRESHOLD) {
    try {
      if (ptp(tr.x) <= 1e-10 || ptp(tr.v) <= 1e-10) throw new Error('Degenerate trajectory: constant expressions are not evidence');
      const q = law.evaluate(tr);
      const denom = mean(q.map(Math.abs));
      if (!(denom > 1e-12)) throw new Error('Nonfinite or vanishing invariant');
      const score = ptp(q) / denom;
      let maxProp = 0;
      tr.x.forEach((x, i) => {
        const p = Math.hypot(2 * tr.v[i] * noiseSd, (2 * law.a * x + 4 * law.b * x ** 3) * noiseSd);
        if (p > maxProp) maxProp = p;
      });
      const bound = (6 * maxProp + 12 * (1 + Math.abs(law.a)) * noiseSd ** 2) / denom;
      const status = Math.abs(score - threshold) <= bound ? INCONCLUSIVE : score > threshold ? REFUTED : SURVIVES;
      return { drift: score, allowance: bound, status };
    } catch (err) {
      return { drift: null, allowance: null, status: INCONCLUSIVE, reason: err.message };
    }
  }

  const combine = ds => (ds.some(d => d.status === REFUTED) ? REFUTED : ds.some(d => d.status === INCONCLUSIVE) ? INCONCLUSIVE : SURVIVES);
  const SYSTEMS = {
    harmonic_undamped_control: { omega: 2, alpha: 0, gamma: 0, revise: false, label: 'Harmonic oscillator (valid control)' },
    duffing_nonlinearity: { omega: 2, alpha: 1, gamma: 0, revise: true, label: 'Duffing oscillator (nonlinear)' },
    weakly_damped_negative_control: { omega: 2, alpha: 0, gamma: 0.008, revise: true, label: 'Weakly damped (negative control)' },
  };
  const CATALOG = [0.2, 0.5, 0.9, 1.3, 1.7].flatMap(a => [2, 6, 12].map(d => [a, d]));
  const AUDIT_BASE = [[1.463, 0.239, 9.73, 641], [1.613, -0.173, 11.57, 733], [1.243, 0.359, 8.13, 569]];

  /** Mirror of run_demo.run_case. `auditAmplitudes` (tests only) injects recorded jitter. */
  function runOscillator({ system = 'duffing_nonlinearity', seed = 2026, noiseSd = 0, horizonScale = 1, params = null, auditAmplitudes = null, selectedOverride = null, onStage = null } = {}) {
    const p = params || SYSTEMS[system];
    const streams = Object.fromEntries(['discovery', 'probe', 'revision', 'holdout'].map(k => [k, makeRng(seed, 310, k)]));
    const ledger = [];
    let frozen = null;
    const observe = (amplitude, v0, horizon, steps, partition) => {
      if (partition === 'holdout' && !frozen) throw new Error('Models must be frozen before holdout acquisition');
      const tr = simulate({ amplitude, v0, omega: p.omega, alpha: p.alpha, gamma: p.gamma, horizon, steps });
      if (noiseSd) { tr.x = tr.x.map(v => v + streams[partition].normal(0, noiseSd)); tr.v = tr.v.map(v => v + streams[partition].normal(0, noiseSd)); }
      ledger.push({ partition, amplitude, v0, horizon, steps, measurements: 2 * steps, rhs: tr.rhs });
      return tr;
    };
    const initial = [[0.12, 0], [0.2, 0.06], [0.27, -0.04]].map(([a, v]) => observe(a, v, 0.8, 121, 'discovery'));
    const quadratic = fitHypothesis(initial, 2);
    const training = initial.map(tr => driftDecision(quadratic, tr, noiseSd));
    if (onStage) onStage('fit', { quadratic });
    const catalog = CATALOG.map(([a, d]) => {
      const tr = observe(a, 0, d * horizonScale, 401, 'probe');
      return { amplitude: a, horizon: d * horizonScale, ...driftDecision(quadratic, tr, noiseSd) };
    });
    const counterexamples = catalog.filter(s => s.status === REFUTED);
    const pool = counterexamples.length ? counterexamples : catalog;
    let best = pool.reduce((m, s) => ((s.drift ?? -1) > (m.drift ?? -1) ? s : m));
    // Tests only: near-equal drifts (e.g. amplitude-independent damping) make the
    // argmax a numerical tie-break; replay the recorded choice to compare fits.
    if (selectedOverride) best = catalog.find(s => s.amplitude === selectedOverride[0] && s.horizon === selectedOverride[1]) || best;
    let revised = null, revisionError = null, extra = null;
    if (p.revise && counterexamples.length) {
      extra = observe(best.amplitude, 0, best.horizon, 501, 'revision');
      try { revised = fitHypothesis([...initial, extra], 4); } catch (err) { revisionError = err.message; }
    }
    let noSearch = null;
    try { noSearch = fitHypothesis(initial, 4); } catch (err) { noSearch = null; }
    frozen = { initial: [quadratic.a, quadratic.b], revised: revised && [revised.a, revised.b], noSearch: noSearch && [noSearch.a, noSearch.b] };
    const jitter = makeRng(seed, 17391);
    const audits = AUDIT_BASE.map(([a, v, h, steps], i) => {
      const amp = auditAmplitudes ? auditAmplitudes[i] : a + jitter.uniform(-0.025, 0.025);
      const tr = observe(amp, v, h * horizonScale, steps, 'holdout');
      return {
        amplitude: amp, v0: v, horizon: h * horizonScale, trajectory: tr,
        initial: driftDecision(quadratic, tr, noiseSd),
        revised: revised ? driftDecision(revised, tr, noiseSd) : null,
        noSearch: noSearch ? driftDecision(noSearch, tr, noiseSd) : null,
      };
    });
    return {
      system, params: p, seed, noiseSd, quadratic, training, catalog, counterexamples, selected: best,
      discovery: initial, revisionTrajectory: extra,
      revised, revisionError, noSearch, frozen, audits,
      initialVerdict: combine(audits.map(a => a.initial)),
      revisedVerdict: revised ? combine(audits.map(a => a.revised)) : null,
      noSearchVerdict: noSearch ? combine(audits.map(a => a.noSearch)) : INCONCLUSIVE,
      ledger,
    };
  }

  return {
    REFUTED, SURVIVES, INCONCLUSIVE, M, POLICIES, THRESHOLD, SYSTEMS, CATALOG, AUDIT_BASE,
    makeRng, material, fitHooke, hookeUncertainty, searchBoundary, fitBilinear, predictBilinear, maeDecision, runMaterials,
    simulate, fitHypothesis, hypothesis, driftDecision, combine, runOscillator, linspace,
  };
});
