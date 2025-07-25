import sys

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
import argparse
from mpltools import annotation
import xlb.experimental.thermo_mechanical.solid_utils as utils

parser = argparse.ArgumentParser("plotter")
parser.add_argument("smoothing_steps_per_iteration", type=int)
parser.add_argument("smoothing_factor", type=float)
parser.add_argument("convergence_factor", type=float)
parser.add_argument("E_scaled", type=float)
parser.add_argument("nu", type=float)
args = parser.parse_args()

smoothing_steps_per_iteration = args.smoothing_steps_per_iteration
smoothing_factor = args.smoothing_factor


multigrid_data = pd.read_csv(
    "multigrid_results.csv", skiprows=0, sep=",", engine="python", dtype=np.float64
)
print(multigrid_data.head())


# plot convergence residual per iteration for multigrid
title = r"$\tilde{E} = $" + str(args.E_scaled) + r", $\nu = $" + str(args.nu)
x_label = "Iteration"
y_label = "Error Norm"
fig, ax = plt.subplots()
ax.plot(
    multigrid_data["iteration"],
    multigrid_data["error_norm"],
    "-",
    color="green",
    label="Error",
)
ax.grid(True)
plt.yscale("log")
ax.set_title(title)
# plot expected speed of convergence
slope = smoothing_factor**smoothing_steps_per_iteration
multigrid_data["slope_power"] = slope ** multigrid_data["iteration"]
ax.plot(
    multigrid_data["iteration"],
    multigrid_data["slope_power"],
    "--",
    color="black",
    label="Smoothing Factor {:.2f}".format(slope),
)
print("Smoothing Factor: {}".format(slope))

# plot convergence factor
convergence_factor = args.convergence_factor
multigrid_data["convergence_factor"] = convergence_factor ** multigrid_data["iteration"]
ax.plot(
    multigrid_data["iteration"],
    multigrid_data["convergence_factor"],
    "--",
    color="blue",
    label="Convergence Factor {:.2f}".format(convergence_factor),
)
print("Convergence Factor: {}".format(convergence_factor))

# Actual rate of convergence
slope = utils.rate_of_convergence(multigrid_data, "error_norm")
multigrid_data["slope_power"] = slope ** (multigrid_data["iteration"] + 5)
ax.plot(
    multigrid_data["iteration"],
    multigrid_data["slope_power"],
    "--",
    color="red",
    label="Actual Speed of Convergence {:.2f}".format(slope),
)
print("Actual Speed of Convergence: {}".format(slope))

ax.set_ylim((1e-11, 1e2))
# calculate actual speed of convergence
end_residual = multigrid_data["error_norm"].min()
plt.xlabel(x_label, labelpad=20, fontsize=12)
plt.ylabel(y_label, labelpad=20, fontsize=12)
plt.legend(loc="upper right")
plt.tight_layout()
plt.savefig("residual_mg.pdf")
