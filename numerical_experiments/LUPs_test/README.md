# LUPs_test — Numerical Speed Experiments

Benchmark lattice updates per second (LUPs) for periodic/Dirichlet BCs in single/double precision.

## Requirements
- Python 3 (project environment).
- bash and bc.

## Run
- From this folder:
  ```bash
  bash run_speed_study.sh
  ```

## What happens
- Repeated runs of `speed_tester.py` across grid sizes and precisions.
- Outputs:
  - `log_YYYY-MM-DD_HH-MM-SS.txt` (detailed log)
  - `results_YYYY-MM-DD_HH-MM-SS.csv` (aggregated timings)
  - Plots via `plotter.py`

## Adjust
- `run_speed_study.sh`: grid, dt, timesteps, iterations, repeats.
- `speed_tester.py`: timing details and printed metrics.
- `plotter.py`: plotting options.

## Notes
- Temporary files `tmp_*` are cleaned at the end.
- Results are written to the current working directory.
