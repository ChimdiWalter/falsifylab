"""One-command local demonstration; no cloud service, API key, or GPU."""
import argparse
from pathlib import Path
from .run_demo import execute as oscillator
from .run_materials import execute as materials
from .make_report import generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('outputs'))
    parser.add_argument('--seeds', type=int, default=30)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('seeds must be positive')
    oscillator(args.out)
    materials(args.out / 'materials', args.seeds)
    benchmark_file = args.out / 'benchmark/metrics.json'
    if args.benchmark:
        from .benchmark import execute
        execute(args.out / 'benchmark', args.seeds)
    result = generate(args.out / 'results.json', args.out / 'materials/results.json',
                      args.out / 'demo.html', args.out / 'certificates', benchmark_file)
    from .verify import verify
    verify(args.out)
    print(f"Offline report: {result['html']}")

if __name__ == '__main__':
    main()
