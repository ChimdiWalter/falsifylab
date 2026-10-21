"""Counted experiment queue and stored raw measurements, including failures."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol
import numpy as np
from .physics import Trajectory


class OscillatorObserver(Protocol):
    def __call__(self, *, amplitude: float, initial_velocity: float, horizon: float,
                 steps: int, partition: str) -> Trajectory: ...


@dataclass
class ExperimentLog:
    experiments: list[dict] = field(default_factory=list)
    raw: dict[str, np.ndarray] = field(default_factory=dict)
    frozen: dict | None = None

    def freeze(self, models: dict) -> None:
        from .artifacts import fingerprint
        self.frozen = {'models': models, 'fingerprint': fingerprint(models),
                       'after_experiment': len(self.experiments)}

    def acquire(self, partition: str, knobs: dict, action: Callable, *, kind: str,
                noise_sd: float = 0.0, rng=None):
        if partition == 'holdout' and self.frozen is None:
            raise RuntimeError('Models must be frozen before holdout acquisition')
        if partition != 'holdout' and any(e['partition'] == 'holdout' for e in self.experiments):
            raise RuntimeError('Cannot acquire fitting/search data after final audit')
        key = f'e{len(self.experiments):04d}'
        event = {'id': key, 'partition': partition, 'knobs': knobs, 'kind': kind,
                 'status': 'REQUESTED', 'simulator_calls': 1,
                 'measurements': 0, 'observation_points': 0, 'rhs_evaluations': 0,
                 'simulated_duration_s': 0.0, 'raw_keys': []}
        self.experiments.append(event)
        try:
            result = action()
            if kind == 'oscillator':
                if noise_sd:
                    result = Trajectory(result.time, result.x + rng.normal(0, noise_sd, len(result.x)),
                                        result.v + rng.normal(0, noise_sd, len(result.v)), solver=result.solver)
                arrays = {'time': result.time, 'x': result.x, 'v': result.v}
                event.update(measurements=2 * len(result.x), observation_points=len(result.x),
                             rhs_evaluations=result.solver.get('nfev', 0),
                             simulated_duration_s=knobs['horizon'])
            else:
                arrays = {'strain': np.asarray(knobs['strain']), 'stress_mpa': result}
                event.update(measurements=int(result.size), observation_points=int(result.shape[0]))
            for name, value in arrays.items():
                raw_key = key + '_' + name
                self.raw[raw_key] = value
                event['raw_keys'].append(raw_key)
            event['status'] = 'COMPLETED'
            return result
        except Exception as error:
            event.update(status='FAILED', error=f'{type(error).__name__}: {error}')
            raise

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **self.raw)

    def manifest(self) -> dict:
        parts = {name: [e['id'] for e in self.experiments if e['partition'] == name]
                 for name in sorted({e['partition'] for e in self.experiments})}
        return {'partitions': parts, 'model_freeze': self.frozen,
                'holdout_policy': 'protocol-v3 predeclared final split; legacy v1 and development v2 splits are development data; no tuning on final data',
                'experiment_queue': self.experiments,
                'costs': {partition: {metric: sum(e[metric] for e in self.experiments if e['partition'] == partition)
                         for metric in ('simulator_calls', 'measurements', 'observation_points',
                                        'rhs_evaluations', 'simulated_duration_s')}
                          for partition in parts}}
