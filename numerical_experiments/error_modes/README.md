# Error modes — Smoothing/Amplification analysis

Compute spectral radii and smoothing factors; produce contour plots over phase angles.

Requirements
- Python 3 with numpy, scipy, matplotlib.
- xlb (with a supported compute backend).

Run
- Single case (fixed material and relaxation parameters):
  `python3 smoothing_factor_single.py <E> <nu> <gamma>`
  Example:
  `python3 smoothing_factor_single.py 1.0 0.3 0.8`
- Batch study over parameter ranges:
  `bash run_smoothing_factor_study.sh`

Adjust
- `smoothing_factor_single.py`: theta, backend/precision, grid resolution, output naming.
- `run_smoothing_factor_study.sh`: parameter grids and job control.
