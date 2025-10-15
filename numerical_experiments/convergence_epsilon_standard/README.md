# Convergence tester — standard elastostatic LB

Run automated convergence studies for the standard elastostatic LB solver.

Subfolders
- convergence_epsilon_no_boundaries — periodic BC.
- convergence_epsilon_with_dirichlet — Dirichlet BC.
- convergence_epsilon_with_vn — Von Neumann BC.

Run
- cd into the desired subfolder, then:
  bash start_convergence_study.sh

Outputs
- Convergence plots and CSVs with errors are written to the working directory.

Adjust
- convergence_study.py — material parameters and geometry.
- convergence_study.sh — base grid size, time steps, and number of refinement iterations.
