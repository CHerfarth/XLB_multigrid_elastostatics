# Stability — Numerical Experiments

This folder contains scripts for a systematic check of stability of the multigrid LB scheme.

# How to run

- Execute
  ```bash
  bash run_convergence_tester.sh
  ```

## Outputs

- Plots (PDF) for different values of stability for given material parameters smoothing steps saved in the current directory.

## Adjusting parameters

- Edit `run_convergence_tester.sh` for adjusting material params, smoothing steps and iterations.
