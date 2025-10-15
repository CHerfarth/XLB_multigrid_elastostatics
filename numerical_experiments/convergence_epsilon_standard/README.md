# Convergence tester — standard elastostatic LB

Purpose
- Run automated convergence studies for the standard elastostatic lattice-Boltzmann solver.

Prerequisites
- Python with required packages (see project environment or pip install requirements).
- Bash to run the provided shell scripts.

Quick run
1. Choose boundary-condition subfolder:
   - periodic BC: convergence_epsilon_no_boundaries
   - Dirichlet BC: convergence_epsilon_with_dirichlet
   - Von Neumann BC: convergence_epsilon_with_vn
2. From this folder run:
   bash start_convergence_study.sh
3. Outputs:
   - Convergence plots (PDF/PNG) and CSV files with errors are written to the working directory (same folder where the script is run).

Adjusting the study
- Simulation parameters / material properties / geometry: edit convergence_study.py 
- Grid sizes / refinement / iterations: edit convergence_study.sh 

Notes
- Run scripts assume default environment; activate your Python environment if needed.
- For reproducibility, record the parameters printed at the start of each run.
