# Multigrid — Numerical Experiments

This folder contains scripts for direct comparison between multigrid and standard LB for specific material params.

# How to run

- Execute
  ```bash
  bash run_convergence_study.sh
  ```
- To only run for for given set of grid size and material params:
 ```bash
  bash run_comparison_study_manual.sh <nodes> <timesteps> <E> <nu>
  ```

## Outputs

- Plots (PDF) of error/residual over time/WU for given material parameters smoothing steps saved in the current directory.

## Adjusting parameters

- Edit `run_convergence_study.sh` for adjusting material params and iterations.
- Edit `comparison.py` for adjusting smoothing steps, manufactured solution etc.
