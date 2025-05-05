import xlb
import sys
from xlb.compute_backend import ComputeBackend
from xlb.precision_policy import PrecisionPolicy
from xlb.grid import grid_factory
import xlb.experimental
from xlb.experimental.thermo_mechanical.solid_stepper import SolidsStepper
import xlb.velocity_set
import warp as wp
import numpy as np
from typing import Any
import sympy
import csv
import math
import xlb.experimental.thermo_mechanical.solid_utils as utils
import xlb.experimental.thermo_mechanical.solid_bounceback as bc
from xlb.utils import save_fields_vtk, save_image
from xlb.experimental.thermo_mechanical.solid_simulation_params import SimulationParams
from xlb.experimental.thermo_mechanical.multigrid import MultigridSolver
from xlb.experimental.thermo_mechanical.benchmark_data import BenchmarkData
from xlb.experimental.thermo_mechanical.kernel_provider import KernelProvider
import argparse


def write_results(data_over_wu, name):
    with open(name, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["wu", "iteration", "residual_norm", "l2_disp", "linf_disp", "l2_stress", "linf_stress"])
        writer.writerows(data_over_wu)




if __name__ == "__main__":
    compute_backend = ComputeBackend.WARP
    precision_policy = PrecisionPolicy.FP64FP64
    velocity_set = xlb.velocity_set.D2Q9(precision_policy=precision_policy, compute_backend=compute_backend)

    xlb.init(velocity_set=velocity_set, default_backend=compute_backend, default_precision_policy=precision_policy)
    

    parser = argparse.ArgumentParser("convergence_study")
    parser.add_argument("nodes_x", type=int)
    parser.add_argument("nodes_y", type=int)
    parser.add_argument("timesteps", type=int)
    parser.add_argument("dt", type=float)
    args = parser.parse_args()

    # initiali1e grid
    nodes_x = args.nodes_x
    nodes_y = args.nodes_y
    grid = grid_factory((nodes_x, nodes_y), compute_backend=compute_backend)

    # get discretization
    length_x = 1.
    length_y = 1.
    dx = length_x / float(nodes_x)
    dy = length_y / float(nodes_y)
    assert math.isclose(dx, dy)
    timesteps = args.timesteps
    dt = args.dt
    #dt = dx*dx

    # params
    E = 0.085 * 2.5
    nu = 0.8

    solid_simulation = SimulationParams()
    solid_simulation.set_all_parameters(E=E, nu=nu, dx=dx, dt=dt, L=dx, T=dt, kappa=1.0, theta=1.0 / 3.0)
    print("Simulating with E_scaled {}".format(solid_simulation.E))
    print("Simulating with nu {}".format(solid_simulation.nu))

    # get force load
    x, y = sympy.symbols("x y")
    manufactured_u = sympy.cos(2 * sympy.pi * x)*sympy.sin(2*sympy.pi*y)  # + 3
    manufactured_v = sympy.cos(2 * sympy.pi * y)*sympy.sin(2*sympy.pi*x)  # + 3
    expected_displacement = np.array([
        utils.get_function_on_grid(manufactured_u, x, y, dx, grid),
        utils.get_function_on_grid(manufactured_v, x, y, dx, grid),
    ])
    force_load = utils.get_force_load((manufactured_u, manufactured_v), x, y)

    # get expected stress
    s_xx, s_yy, s_xy = utils.get_expected_stress((manufactured_u, manufactured_v), x, y)
    expected_stress = np.array([
        utils.get_function_on_grid(s_xx, x, y, dx, grid),
        utils.get_function_on_grid(s_yy, x, y, dx, grid),
        utils.get_function_on_grid(s_xy, x, y, dx, grid),
    ])

    potential, boundary_array, boundary_values = None, None, None

    # adjust expected solution
    expected_macroscopics = np.concatenate((expected_displacement, expected_stress), axis=0)
    expected_macroscopics = utils.restrict_solution_to_domain(expected_macroscopics, potential, dx)


    #-------------------------------------- collect data for multigrid----------------------------
    data_over_wu = list()
    residuals = list()
    benchmark_data = BenchmarkData()
    benchmark_data.wu = 0.
    multigrid_solver = MultigridSolver(
            nodes_x=nodes_x,
            nodes_y=nodes_y,
            length_x=length_x,
            length_y=length_y,
            dt=dt,
            force_load=force_load,
            gamma=0.8,
            v1=4,
            v2=4,
            max_levels=None, 
        )
    finest_level = multigrid_solver.get_finest_level()
    for i in range(timesteps):
        residual_norm = finest_level.start_v_cycle(return_residual=True)
        residuals.append(residual_norm)
        macroscopics = finest_level.get_macroscopics()
        l2_disp, linf_disp, l2_stress, linf_stress = utils.process_error(macroscopics, expected_macroscopics, i, dx, list())
        data_over_wu.append((benchmark_data.wu, i, residual_norm, l2_disp, linf_disp, l2_stress, linf_stress))
        if (residual_norm < 1e-14):
            break

    print(l2_disp, linf_disp, l2_stress, linf_stress)
    print(residual_norm)
    write_results(data_over_wu, "multigrid_results.csv")


