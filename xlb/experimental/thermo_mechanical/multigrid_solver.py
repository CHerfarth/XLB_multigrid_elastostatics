import numpy as np
import warp as wp
from xlb.experimental.thermo_mechanical.solid_simulation_params import SimulationParams
import xlb
from xlb.compute_backend import ComputeBackend
from xlb.precision_policy import PrecisionPolicy
from xlb.grid import grid_factory
from xlb.experimental.thermo_mechanical.solid_stepper import SolidsStepper
import xlb.experimental.thermo_mechanical.solid_utils as utils
from xlb.experimental.thermo_mechanical.benchmark_data import BenchmarkData
from xlb.experimental.thermo_mechanical.kernel_provider import KernelProvider
import xlb.experimental.thermo_mechanical.solid_boundary as bc
from xlb.experimental.thermo_mechanical.multigrid_level import Level
from xlb import DefaultConfig
import math
from typing import Any
import sympy


class MultigridSolver:
    """
    A class implementing a multigrid iterative solver for elliptic PDEs.
    """

    def __init__(
        self,
        nodes_x,
        nodes_y,
        length_x,
        length_y,
        dt,
        force_load,
        gamma,
        v1,
        v2,
        max_levels=None,
        coarsest_level_iter=0,
        boundary_conditions=None,
        boundary_values=None,
        potential=None,
        output_images=False,
        error_correction_iterations=1,  # by default do V-Cycle
    ):
        precision_policy = DefaultConfig.default_precision_policy
        compute_backend = DefaultConfig.default_backend
        velocity_set = DefaultConfig.velocity_set

        # Determine maximum possible levels
        self.max_possible_levels = min(int(np.log2(nodes_x)), int(np.log2(nodes_y)))  # + 1

        if max_levels is None:
            self.max_levels = self.max_possible_levels
        else:
            self.max_levels = min(max_levels, self.max_possible_levels)

        # setup levels
        self.levels = list()
        for i in range(self.max_levels):
            nx_level = (nodes_x - 1) // (
                2**i
            ) + 1  # IMPORTANT: only works with nodes as power of two at the moment
            ny_level = (nodes_y - 1) // (2**i) + 1
            dx = length_x / float(nx_level)
            dy = length_y / float(ny_level)
            dt_level = dt * (4**i)
            assert math.isclose(dx, dy)

            if i != 0:
                force_load = None

            level = Level(
                nodes_x=nx_level,
                nodes_y=ny_level,
                dx=dx,
                dt=dt_level,
                force_load=force_load,
                gamma=gamma,
                v1=v1,
                v2=v2,
                level_num=i,
                compute_backend=compute_backend,
                velocity_set=velocity_set,
                precision_policy=precision_policy,
                coarsest_level_iter=coarsest_level_iter,
                error_correction_iterations=error_correction_iterations,
            )
            if boundary_conditions != None:
                if i == 0:
                    level.add_boundary_conditions(boundary_conditions, boundary_values)
                else:
                    # create zero displacement boundary for coarser meshes
                    x, y = sympy.symbols("x y")
                    displacement = [0 * x + 0 * y, 0 * x + 0 * y]
                    indicator = lambda x, y: -1
                    boundary_conditions_level, boundary_values_level = bc.init_bc_from_lambda(
                        potential_sympy=potential,
                        grid=level.grid,
                        dx=dx,
                        velocity_set=velocity_set,
                        manufactured_displacement=displacement,
                        indicator=indicator,
                        x=x,
                        y=y,
                        precision_policy=precision_policy,
                    )
                    level.add_boundary_conditions(boundary_conditions_level, boundary_values_level)
            self.levels.append(level)

    def get_next_level(self, level_num):
        if level_num + 1 < self.max_levels:
            return self.levels[level_num + 1]
        else:
            return None

    def get_finest_level(self):
        return self.levels[0]

    def free(self):
        for level in self.levels:
            del level.f_1
            del level.f_2
            del level.f_3
            del level.f_4
            del level.defect_correction
            del level

    def start_v_cycle(self, return_residual=False, timestep=0):
        finest_level = self.get_finest_level()
        return finest_level(self, return_residual, timestep)

    def get_macroscopics(self, output_array):
        finest_level = self.get_finest_level()
        finest_level.stepper.get_macroscopics(f=finest_level.f_1, output_array=output_array)
