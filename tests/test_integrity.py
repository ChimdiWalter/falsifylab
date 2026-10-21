"""Scientific controls and adversarial failure cases, independent of report prose."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from scipy.integrate import cumulative_trapezoid
from jsonschema.exceptions import ValidationError
from falsifylab.artifacts import digest
from falsifylab.certificates import validate
from falsifylab.decisions import drift_decision, INCONCLUSIVE, SURVIVES, REFUTED
from falsifylab.experiments import ExperimentLog
from falsifylab.hypothesis import Hypothesis, fit_hypothesis, relative_drift
from falsifylab.materials import MaterialSimulator, fit_hooke, fit_bilinear
from falsifylab.physics import Trajectory, simulate
from falsifylab.run_demo import run_case, find_counterexample
from falsifylab.run_materials import run, search_boundary, BUDGET, REPLICATES


def test_duffing_energy_and_dissipation_balance():
    omega, alpha, gamma = 1.7, .9, .025
    tr = simulate(amplitude=1.1, initial_velocity=.2, omega=omega, alpha=alpha, gamma=gamma,
                  horizon=4, steps=4001)
    q = tr.v**2 + omega**2 * tr.x**2 + alpha/2 * tr.x**4
    # dQ/dt=-2*gamma*v². Integrated-work check uses an independent quadrature.
    loss = cumulative_trapezoid(2*gamma*tr.v**2, tr.time, initial=0)
    assert np.max(np.abs(q-q[0]+loss)) < 2e-7
    assert q[-1] < q[0]
    undamped = simulate(amplitude=1.1, omega=omega, alpha=alpha, horizon=4)
    assert relative_drift(Hypothesis(omega**2, alpha/2), undamped) < 1e-8


def test_solver_sensitivity_separates_numerics_from_failed_physics():
    for rtol, atol in [(2e-11, 1e-13), (1e-7, 1e-9)]:
        tr = simulate(amplitude=1.4, alpha=1, horizon=11, rtol=rtol, atol=atol)
        assert relative_drift(Hypothesis(4, .5), tr) < 2e-6
        assert relative_drift(Hypothesis(4), tr) > .15


@pytest.mark.parametrize('field,value', [('amplitude',np.nan),('omega',np.inf),('horizon',0),('steps',3),('rtol',-1)])
def test_invalid_simulation_inputs(field, value):
    with pytest.raises(ValueError):
        simulate(**{'amplitude':1.0, field:value})


def test_invalid_observations_units_and_degenerate_constants():
    t=np.arange(6.)
    with pytest.raises(ValueError, match='units'):
        Trajectory(t,t,t,units=('s','cm','cm/s'))
    with pytest.raises(ValueError):
        Trajectory(t, [np.nan]*6, t)
    with pytest.raises(ValueError):
        Trajectory(t[::-1],t,t)
    for x,v in [(np.zeros(6),np.zeros(6)),(np.ones(6),np.zeros(6))]:
        tr=Trajectory(t,x,v)
        with pytest.raises(ValueError, match='excitation'):
            fit_hypothesis([tr],2)
        assert drift_decision(Hypothesis(4), tr)['status'] == INCONCLUSIVE
    with pytest.raises(ValueError):
        Hypothesis(float('nan'))
    # Two displacement levels cannot distinguish centered x² and x⁴ columns.
    with pytest.raises(ValueError):
        fit_hypothesis([Trajectory(t,np.array([1,2,1,2,1,2.]),np.arange(6.))],4)


def test_noise_overwhelming_signal_abstains():
    tr=simulate(amplitude=.2)
    assert drift_decision(Hypothesis(4),tr,noise_sd=.2)['status'] == INCONCLUSIVE
    assert drift_decision(Hypothesis(4),tr)['status'] == SURVIVES


def test_logged_failures_and_freeze_before_holdout():
    log=ExperimentLog()
    with pytest.raises(RuntimeError,match='frozen'):
        log.acquire('holdout',{},lambda:None,kind='materials')
    def failed():
        raise RuntimeError('solver failed')
    with pytest.raises(RuntimeError,match='solver failed'):
        log.acquire('discovery',{},failed,kind='oscillator')
    assert log.experiments[0]['status']=='FAILED'
    assert log.experiments[0]['simulator_calls']==1
    log.freeze({'candidate':'fixed'})
    log.acquire('holdout',{'strain':[.001]},lambda:np.ones((1,4)),kind='materials')
    with pytest.raises(RuntimeError,match='after final audit'):
        log.acquire('discovery',{},lambda:None,kind='materials')


def test_final_audit_is_after_fit_and_disjoint_from_search():
    r,*_=run_case('duffing',dict(omega=2.,alpha=1.,gamma=0.),True)
    trace=r['trace']
    freeze=trace['model_freeze']['after_experiment']
    assert all(e['partition']!='holdout' for e in trace['experiment_queue'][:freeze])
    assert all(e['partition']=='holdout' for e in trace['experiment_queue'][freeze:])
    interventions=[(e['knobs']['amplitude'],e['knobs']['initial_velocity'],e['knobs']['horizon'])
                   for e in trace['experiment_queue']]
    assert len(set(interventions[-3:]).intersection(interventions[:-3]))==0
    assert r['ablations']['no_counterexample_search_quartic']==SURVIVES
    assert r['revised_verdict']==SURVIVES


def test_selection_never_reads_simulator_parameters():
    class SealedObserver:
        def __getattr__(self,name):
            raise AssertionError('Truth access: '+name)
        def __call__(self,strain,rng,replicates,partition):
            x=np.asarray(strain)
            stress=180000*np.minimum(x,.003)+2000*np.maximum(x-.003,0)
            return np.repeat(stress[:,None],replicates,axis=1)
    s=search_boundary(SealedObserver(),180000,np.random.default_rng(1),'active',noise_sd=0)
    assert s['probes']==BUDGET
    assert s['boundary_interval'][0] < .003+10/178000 < s['boundary_interval'][1]
    # The oscillator selector likewise sees only the observation protocol.
    def oscillator(**knobs):
        knobs.pop('partition')
        return simulate(**knobs,omega=1.8,alpha=.7)
    stress=find_counterexample(Hypothesis(1.8**2),oscillator)
    assert stress['counterexamples']


def test_material_noise_and_failed_bracket_preserve_equal_budgets():
    def linear(strain,rng,replicates,partition):
        return np.repeat((210000*np.asarray(strain))[:,None],replicates,axis=1)
    for policy in ('active','uniform','random'):
        r=search_boundary(linear,210000,np.random.default_rng(1),policy,noise_sd=0)
        assert r['boundary_interval'] is None
        assert r['boundary_status']==INCONCLUSIVE
        assert r['probes']==10 and r['measurements']==40
    high=run(2026,noise_sd=80)
    assert any(s['uncertain_probe_count'] for s in high['strategies'].values())
    assert high['heldout_revised_decisions']['active']['status'] == INCONCLUSIVE


def test_threshold_onset_is_not_yield_and_has_correct_units():
    r=run(2026,noise_sd=0)
    target=r['reference_operational_onset_benchmark_only']
    expected=.002+10/(210000-1500)
    assert abs(target-expected) < 1e-12
    assert target>r['true_yield_strain_benchmark_only']
    assert r['units']=={'strain':'dimensionless','stress':'MPa'}
    assert r['trace']['costs']['discovery']['measurements']==40
    assert r['trace']['costs']['holdout']['measurements']==249


@pytest.mark.parametrize('strain,stress', [([0,0],[0,0]),([.1,np.nan],[1,2]),([.1,.2],[1,np.inf]),([.1,.2],[1])])
def test_invalid_material_data(strain,stress):
    with pytest.raises(ValueError):
        fit_hooke(strain,stress)


def test_nonmonotone_material_observations_abstain():
    # Uniform probes see fail->pass->fail, contradicting the binary-search prior.
    def observer(strain,rng,replicates,partition):
        x=np.asarray(strain)
        y=200000*x-np.where((x>.002)&(x<.005),20.,0.)-np.where(x>.011,50.,0.)
        return np.repeat(y[:,None],replicates,axis=1)
    r=search_boundary(observer,200000,np.random.default_rng(1),'uniform',noise_sd=0)
    assert r['nonmonotone_observations']
    assert r['boundary_status']==INCONCLUSIVE
    assert r['bracket_width'] is None


def test_seeded_reproduction_includes_raw_arrays(tmp_path):
    paths=[tmp_path/'one.npz',tmp_path/'two.npz']
    a=run(2026,raw_path=paths[0])
    b=run(2026,raw_path=paths[1])
    a.pop('raw_artifact'); b.pop('raw_artifact')
    assert a==b
    assert digest(paths[0])==digest(paths[1])
    different=run(2027)
    assert a['strategies']['random']['observations'] != different['strategies']['random']['observations']


def test_certificate_rejects_tampering_and_overlap(evidence_run,tmp_path):
    from falsifylab.make_report import generate
    root=evidence_run
    generate(root/'results.json',root/'materials/results.json',root/'demo.html',root/'certificates')
    path=root/'certificates/oscillator.json'
    original=json.loads(path.read_text())
    bad=copy.deepcopy(original); bad['status']='PROVEN'
    with pytest.raises(ValidationError): validate(bad)
    bad=copy.deepcopy(original); bad['partition_manifest']['partitions']['discovery'].append('e0003')
    with pytest.raises(ValueError,match='overlap'): validate(bad)
    bad=copy.deepcopy(original); bad['artifacts'][0]['sha256']='0'*64
    with pytest.raises(ValueError,match='checksum'): validate(bad,certificate_path=path,artifact_root=root)
    bad=copy.deepcopy(original); bad['resource_costs']['holdout']['measurements']+=1
    with pytest.raises(ValueError,match='cost'): validate(bad)
    bad=copy.deepcopy(original); bad['artifacts'][0]['path']='../../../../etc/passwd'
    with pytest.raises(ValueError,match='outside'): validate(bad,certificate_path=path,artifact_root=root)


def test_cli_smoke_and_bad_budget(tmp_path):
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,'-m','falsifylab','--seeds','1','--out',str(tmp_path/'cli')],cwd=root,
                          capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stderr
    assert 'VERIFIED 4 certificates' in result.stdout
    result=subprocess.run([sys.executable,'-m','falsifylab.benchmark','--seeds','0'],cwd=root,capture_output=True,text=True)
    assert result.returncode!=0


def test_certificate_metrics_cannot_disagree_with_source(evidence_run):
    from falsifylab.make_report import generate
    root=evidence_run
    generate(root/'results.json',root/'materials/results.json',root/'demo.html',root/'certificates')
    path=root/'certificates/oscillator.json'
    original=json.loads(path.read_text())
    bad=copy.deepcopy(original); bad['metrics']['initial_holdout_relative_drift']=0.0
    with pytest.raises(ValueError,match='metric'):
        validate(bad,certificate_path=path,artifact_root=root)
    bad=copy.deepcopy(original); bad['candidate']['coefficients']['quadratic']=999
    with pytest.raises(ValueError,match='frozen'):
        validate(bad)


def test_raw_metric_verification_detects_fabricated_holdout(evidence_run):
    from falsifylab.verify import verify_oscillator
    root=evidence_run
    record=json.loads((root/'results.json').read_text())['cases'][1]
    record['holdout_observations'][0]['initial']['relative_drift']=0.0
    with pytest.raises(ValueError,match='differs'):
        verify_oscillator(record,root/record['raw_artifact'])
