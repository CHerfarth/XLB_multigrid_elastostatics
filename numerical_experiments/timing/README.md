# Timing — Numerical Experiments

This folder contains scripts to measure and analyze the computational performance (timing) of the elastostatic lattice-Boltzmann solver.

## How to run the timing experiments

1. **Requirements**
   - Python 3 with required packages (activate your project environment).
   - Bash.

2. **Running the experiments**
   - Open a terminal in this folder.
   - Run the main timing script (for example):
     ```bash
     bash run_timing_study.sh
     ```
   - This will execute timing tests for various grid sizes and material parameters, and collect results.

3. **Outputs**
   - Timing logs and results are written to `data` .
   - Plots are written to `plots`.

4. **Adjusting parameters**
   - Edit `run_timing_study.sh` to change grid sizes, number of steps, or repetitions.
   - Edit the Python scripts to modify solver parameters or output formats.

## Notes

- All results are saved in the directory where you run the script.
- For reproducibility, use the same Python environment and keep the generated log and results files.
