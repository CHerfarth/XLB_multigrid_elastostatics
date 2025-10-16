import numpy as np
import warp as wp
import sympy
from typing import Any

from xlb.velocity_set.velocity_set import VelocitySet
from xlb.precision_policy import PrecisionPolicy
from xlb.utils import save_image
from xlb.compute_backend import ComputeBackend
from xlb.operator.operator import Operator
import xlb.experimental.multigrid_elastostatics.solid_utils as utils
from xlb.experimental.multigrid_elastostatics.solid_simulation_params import SimulationParams
from xlb.experimental.multigrid_elastostatics.kernel_provider import KernelProvider
from xlb import DefaultConfig


class SolidsBoundary(Operator):
    """
    Operator to apply Dirichlet and VN boundary conditions
    """

    def __init__(
        self,
        force,
        velocity_set: VelocitySet = None,
        precision_policy: PrecisionPolicy = None,
        compute_backend: ComputeBackend = None,
    ):
        super().__init__(
            velocity_set,
            precision_policy,
            compute_backend,
        )
        self.force = force

    def _construct_warp(self):
        opp_indices = self.velocity_set.opp_indices
        w = self.velocity_set.w
        c = self.velocity_set.c_float
        q = self.velocity_set.q

        kernel_provider = KernelProvider()
        vec = kernel_provider.vec
        bc_info_vec = kernel_provider.bc_info_vec
        bc_val_vec = kernel_provider.bc_val_vec
        read_bc_info = kernel_provider.read_bc_info
        read_bc_vals = kernel_provider.read_bc_vals
        read_local_population = kernel_provider.read_local_population
        calc_moments = kernel_provider.calc_moments
        calc_equilibrium = kernel_provider.calc_equilibrium
        calc_populations = kernel_provider.calc_populations
        write_population_to_global = kernel_provider.write_population_to_global

        @wp.func
        def dirichlet_functional(
            old_direction: wp.int32,  # l: direction index of population leaving domain
            f_current_vec: vec,
            f_previous_post_collision_vec: vec,
            bared_m_vec: vec,
            u_x: self.compute_dtype,
            u_y: self.compute_dtype,
            q_ij: self.compute_dtype,
            K: self.compute_dtype,
            mu: self.compute_dtype,
        ):
            """
            Functional for reconstructing a single missing incoming population through Dirichlet BC

            old_direction: direction index from node to ghost node
            f_current_vec: vector of populations after streaming step at time t
                 with missing incoming population not applied yet
            f_previous_post_collision_vec: vector of populations
                after collision step at time t - Delta t
            bared_m_vec: vector of bared moments
            u_x, u_y: boundary conditions
            q_ij: distance between node and ghost node
            K, mu: material parameters

            returns:
                vector of populations with missing population reconstructed
            """
            new_direction = opp_indices[old_direction]
            x_dir = c[0, new_direction]
            y_dir = c[1, new_direction]
            weight = w[new_direction]

            m_s = bared_m_vec[3]
            m_d = bared_m_vec[4]
            m_11 = bared_m_vec[2]
            dx_u_x = -self.compute_dtype(0.25) * (m_s / K + m_d / mu)
            dy_u_y = -self.compute_dtype(0.25) * (m_s / K - m_d / mu)
            cross_dev = -m_11 / mu  # dy_u_x + dx_u_y

            f_out = f_current_vec

            # bounceback with zero order correction
            f_out[new_direction] = self.store_dtype(
                self.compute_dtype(f_previous_post_collision_vec[old_direction])
                + self.compute_dtype(6.0) * weight * (x_dir * u_x + y_dir * u_y)
            )
            # add first order correction
            if wp.abs(wp.abs(x_dir) + wp.abs(y_dir) - self.compute_dtype(1.0)) < 1e-3:
                f_out[new_direction] += self.store_dtype(
                    self.compute_dtype(6.0)
                    * weight
                    * (q_ij - self.compute_dtype(0.5))
                    * (wp.abs(x_dir) * dx_u_x + wp.abs(y_dir) * dy_u_y)
                )
            if wp.abs(wp.abs(x_dir) + wp.abs(y_dir) - self.compute_dtype(2.0)) < 1e-3:
                f_out[new_direction] += self.store_dtype(
                    self.compute_dtype(6.0)
                    * weight
                    * (q_ij - self.compute_dtype(0.5))
                    * (dx_u_x + dy_u_y + x_dir * y_dir * (cross_dev))
                )
            return f_out

        @wp.func
        def vn_functional(
            old_direction: wp.int32,
            f_post_stream_vec: vec,
            f_post_collision_vec: vec,
            bared_m_vec: vec,
            n_x: self.compute_dtype,
            n_y: self.compute_dtype,
            T_x: self.compute_dtype,
            T_y: self.compute_dtype,
            q_ij: self.compute_dtype,
            force_x: self.compute_dtype,
            force_y: self.compute_dtype,
            K: self.compute_dtype,
            mu: self.compute_dtype,
            tau_t: self.compute_dtype,
            theta: self.compute_dtype,
        ):
            """
            Functional for reconstruction a single missing incoming population through VN BC

            Note: currently only zeroth order correction is implemented

            old_direction: direction from node to ghost node
            f_post_stream_vec: vector of populations after streaming step at time t
                with missing incoming population not applied yet
            f_post_collision_vec: vector of populations after collision step at time t
            bared_m_vec: vector of bared moments
            n_x, n_y: normal vector
            T_x, T_Y: boundary conditions
            q_ij: distance between node and ghost node
            force_x, force_y: forcing terms
            K, mu: material parameters
            tau_t: relaxation time of third-order moments (typically 0.5)
            theta: lattice parameter

            returns:
                vector of populations with missing population reconstructed
            """
            new_direction = opp_indices[old_direction]
            x_dir = c[0, new_direction]
            y_dir = c[1, new_direction]
            weight = w[new_direction]
            f_out = f_post_stream_vec
            # get zeta
            zeta = self.compute_dtype(1.0)
            if wp.abs(n_x) > wp.abs(n_y):
                zeta = -self.compute_dtype(1.0)
            # get c's
            c_1 = -(self.compute_dtype(2.0) * (self.compute_dtype(1.0) - theta) * (K - mu)) / (
                theta * (self.compute_dtype(1.0) - theta - self.compute_dtype(4.0) * mu)
            )
            c_2 = -(self.compute_dtype(2.0) * mu) / (theta - self.compute_dtype(2.0) * mu)
            c_3 = -(self.compute_dtype(4.0) * mu) / (
                self.compute_dtype(1.0) - theta - self.compute_dtype(4.0) * mu
            )

            local_sum = self.compute_dtype(0.0)
            if wp.abs(wp.abs(x_dir) + wp.abs(y_dir) - self.compute_dtype(1.0)) < 1e-3:  # case V1
                local_sum = self.compute_dtype(0.0)
                for m in range(q):
                    k = c[0, m]
                    l = c[1, m]
                    a_ijkl = (
                        wp.abs(k)
                        * wp.abs(l)
                        * (self.compute_dtype(1.0) + x_dir * n_x + y_dir * n_y)
                        * c_1
                    )
                    a_ijkl += k * l * (x_dir * n_y + y_dir * n_x) * c_2
                    a_ijkl += (
                        wp.abs(k)
                        * (self.compute_dtype(1.0) - wp.abs(l))
                        * (wp.abs(x_dir) + x_dir * n_x)
                        + wp.abs(l)
                        * (self.compute_dtype(1.0) - wp.abs(k))
                        * (wp.abs(y_dir) + y_dir * n_y)  # type: ignore
                    ) * c_3
                    if wp.abs(x_dir + k) < 1e-3 and wp.abs(y_dir + l) < 1e-3:
                        a_ijkl += -self.compute_dtype(1.0)
                    local_sum += a_ijkl * f_post_collision_vec[m]
            elif wp.abs(wp.abs(x_dir) + wp.abs(y_dir) - self.compute_dtype(2.0)) < 1e-3:  # case V2
                local_sum = self.compute_dtype(0.0)
                for m in range(q):
                    k = c[0, m]
                    l = c[1, m]
                    a_ijkl = (
                        self.compute_dtype(0.5)
                        * wp.abs(k)
                        * wp.abs(l)
                        * (
                            self.compute_dtype(0.5) * (self.compute_dtype(1.0) + zeta) * x_dir * n_x
                            + self.compute_dtype(0.5)
                            * (self.compute_dtype(1.0) - zeta)
                            * y_dir
                            * n_y
                        )
                        * c_1
                    )
                    a_ijkl += (
                        self.compute_dtype(0.5)
                        * k
                        * l
                        * (
                            x_dir * y_dir
                            + self.compute_dtype(0.5)
                            * (self.compute_dtype(1.0) + zeta)
                            * x_dir
                            * n_y
                            + self.compute_dtype(0.5)
                            * (self.compute_dtype(1.0) - zeta)
                            * y_dir
                            * n_x
                        )
                        * c_2
                    )
                    a_ijkl += (
                        self.compute_dtype(0.5)
                        * (
                            wp.abs(k)
                            * (self.compute_dtype(1.0) - wp.abs(l))
                            * self.compute_dtype(0.5)
                            * (self.compute_dtype(1.0) + zeta)
                            * x_dir
                            * n_x
                            + wp.abs(l)
                            * (self.compute_dtype(1.0) - wp.abs(k))
                            * self.compute_dtype(0.5)
                            * (self.compute_dtype(1.0) - zeta)
                            * y_dir
                            * n_y
                        )
                        * c_3
                    )
                    if wp.abs(x_dir + k) < 1e-3 and wp.abs(y_dir + l) < 1e-3:
                        a_ijkl += -self.compute_dtype(1.0)
                    local_sum += a_ijkl * f_post_collision_vec[m]

            f_out[new_direction] = local_sum
            if wp.abs(wp.abs(x_dir) + wp.abs(y_dir) - self.compute_dtype(1.0)) < 1e-3:
                f_out[new_direction] += T_x * x_dir + T_y * y_dir
            elif wp.abs(wp.abs(x_dir) + wp.abs(y_dir) - self.compute_dtype(2.0)) < 1e-3:
                f_out[new_direction] += self.compute_dtype(0.25) * (
                    x_dir * (self.compute_dtype(1.0) + zeta) * T_x
                    + y_dir * (self.compute_dtype(1.0) - zeta) * T_y
                )

            # so far no first order correction is implemented, this is a ToDo

            return f_out

        @wp.func
        def functional(
            f_post_stream_vec: vec,
            f_post_collision_vec: vec,
            f_previous_post_collision_vec: vec,
            i: wp.int32,
            j: wp.int32,
            boundary_info: wp.array4d(dtype=wp.int8),
            boundary_vals: wp.array4d(dtype=self.store_dtype),
            force_x: self.compute_dtype,
            force_y: self.compute_dtype,
            bared_m_vec: vec,
            K: self.compute_dtype,
            mu: self.compute_dtype,
            theta: self.compute_dtype,
        ):
            """
            Functional for applying boundary conditions at
                lattice point (i,j) after streaming at time t

            f_post_stream_vec: vector of populations after streaming at time t
                with boundary conditions not applied yet
            f_post_collision_vec: vector of populations after collision at time t
            f_previous_post_collision_vec: vector of populations after collision at time t - Delta t
            i,j: indices of lattice point
            boundary_info: array encoding the type of node (interior, boundary, ghost)
                and which incoming populations to reconstruct
            boundary_vals: array storing values needed for reconstructing
                missing populations at boundary
            force_x, force_y: forcing terms at lattice point
            bared_m_vec: vector of bared moments
            K, mu: material params
            theta: lattice parameter

            returns:
                vector of populations after streaming at time t, with boundary conditions applied
            """
            f_out_vec = f_post_stream_vec
            # -------------outside domain--------------
            if boundary_info[0, i, j, 0] == wp.int8(0):  # if outside domain, just set to 0
                for l in range(self.velocity_set.q):
                    f_out_vec[l] = self.compute_dtype(0)
            # -------------Dirichlet BC---------------
            elif boundary_info[0, i, j, 0] == wp.int8(
                2
            ):  # for boundary nodes: check which directions need to be given by dirichlet BC
                for l in range(self.velocity_set.q):
                    if (
                        boundary_info[l + 1, i, j, 0] == wp.int8(1)
                    ):  # this means the interior node is connected to a ghost node in direction l; the bounce back bc needs to be applied
                        # get values from value array
                        u_x = self.compute_dtype(boundary_vals[l * 7, i, j, 0])
                        u_y = self.compute_dtype(boundary_vals[l * 7 + 1, i, j, 0])
                        q_ij = self.compute_dtype(boundary_vals[l * 7 + 6, i, j, 0])
                        f_out_vec = dirichlet_functional(
                            old_direction=l,
                            f_current_vec=f_out_vec,
                            f_previous_post_collision_vec=f_previous_post_collision_vec,
                            bared_m_vec=bared_m_vec,
                            u_x=u_x,
                            u_y=u_y,
                            q_ij=q_ij,
                            K=K,
                            mu=mu,
                        )
            # -------------VN BC--------------------
            elif boundary_info[0, i, j, 0] == wp.int8(
                3
            ):  # for boundary nodes: check which directions need to be given VN BC
                for l in range(q):
                    if boundary_info[l + 1, i, j, 0] == wp.int8(1):
                        # print("Calling Von Neumann")
                        n_x = self.compute_dtype(boundary_vals[l * 7, i, j, 0])
                        n_y = self.compute_dtype(boundary_vals[l * 7 + 1, i, j, 0])
                        T_x = self.compute_dtype(boundary_vals[l * 7 + 2, i, j, 0])
                        T_y = self.compute_dtype(boundary_vals[l * 7 + 3, i, j, 0])
                        q_ij = self.compute_dtype(boundary_vals[l * 7 + 6, i, j, 0])
                        f_out_vec = vn_functional(
                            old_direction=l,
                            f_post_stream_vec=f_out_vec,
                            f_post_collision_vec=f_post_collision_vec,
                            bared_m_vec=bared_m_vec,
                            n_x=n_x,
                            n_y=n_y,
                            T_x=T_x,
                            T_y=T_y,
                            q_ij=q_ij,
                            force_x=force_x,
                            force_y=force_y,
                            K=K,
                            mu=mu,
                            tau_t=self.compute_dtype(0.5),
                            theta=theta,
                        )
            return f_out_vec

        # Kernel is not implemented. Boundary conditions are to be applied from
        # inside a seperate kernel by calling the functional above
        # (see solid_stepper.py or multigrid_stepper.py)
        return functional, None

    @Operator.register_backend(ComputeBackend.WARP)
    def warp_implementation(self):
        raise NotImplementedError(
            "Boundary conditions are to be applied by calling the functional, not through a kernel"
        )


# --------------utils used to construct bc arrays----------------
def init_bc_from_lambda(
    potential_sympy,
    grid,
    dx,
    velocity_set,
    manufactured_displacement,
    indicator,
    x,
    y,
    precision_policy=None,
):
    """
    Initialize boundary conditions from a level set function given as a sympy expression

    potential_sympy: sympy expression defining the level set function
    grid: grid object
    dx: lattice spacing
    velocity_set: velocity set object
    manufactured_displacement: tuple of sympy expressions defining the manufactured displacement
    indicator: function taking x and y coordinates and returning <0 for Dirichlet BC and >0 for VN BC
    x, y: sympy symbols
    precision_policy: precision policy object (if None, default precision policy is used)

    returns:
        boundary_info: warp array encoding the type of node (interior, boundary, ghost), as well as missing neighbors
        boundary_values: warp array storing values needed for reconstructing missing populations at boundary
            (e.g. boundary displacement, distance to boundary, normal vector, traction, etc.)
    """
    # Mapping for boundary_info[0]:
    # 0: ghost node
    # 1: interior node
    # 2: boundary node with dirichlet bc
    # 3: boundary node with VN bc

    # Mapping for boundary_info[1...q]:
    # 0: no missing neighbor in this direction
    # 1: missing neighbor in this direction (i.e. connected to ghost node)

    # Mapping for boundary values, Dirichlet:
    # 0: u_x
    # 1: u_y
    # 2:
    # 3:
    # previoui 4:
    # 5:
    # 6: q_ij

    # Mapping for boundary values, VN:
    # 0: n_x
    # 1: n_y
    # 2: T_x
    # 3: T_y
    # 4:
    # 5:
    # 6: q_ij

    if precision_policy is None:
        precision_policy = DefaultConfig.default_precision_policy

    potential = sympy.lambdify([x, y], potential_sympy)

    params = SimulationParams()
    T = params.T
    L = params.L
    K = params.K
    mu = params.mu
    kappa = params.kappa

    values_per_direction = 7
    host_boundary_info = np.zeros(shape=(10, grid.shape[0], grid.shape[1], 1), dtype=np.int8)
    host_boundary_values = np.zeros(
        shape=(velocity_set.q * values_per_direction, grid.shape[0], grid.shape[1], 1),
        dtype=np.float64,
    )

    # lambdify bc
    bc_dirichlet = [
        sympy.lambdify([x, y], manufactured_displacement[0]),
        sympy.lambdify([x, y], manufactured_displacement[1]),
    ]

    # get derivative of BC
    bc_dirichlet_devs = [
        sympy.diff(manufactured_displacement[0], x),
        sympy.diff(manufactured_displacement[0], y),
        sympy.diff(manufactured_displacement[1], x),
        sympy.diff(manufactured_displacement[1], y),
    ]
    # lambdify derivatives
    for i in range(4):
        bc_dirichlet_devs[i] = sympy.lambdify([x, y], bc_dirichlet_devs[i])

    # concatenate with non-derivative BC
    bc_dirichlet = np.concatenate((bc_dirichlet, bc_dirichlet_devs))

    # step 1: set all nodes with negative potential to interior
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if potential(i * dx, j * dx) <= 0:
                host_boundary_info[0, i, j, 0] = 1

    # get gradients of potential
    dx_potential = sympy.lambdify([x, y], sympy.diff(potential_sympy, x))
    dy_potential = sympy.lambdify([x, y], sympy.diff(potential_sympy, y))

    # step 2: for each interior node, check if all neighbor nodes are also interior; if not, set to boundary
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if host_boundary_info[0, i, j, 0] == 1:
                for direction in range(velocity_set.q):
                    x_direction = velocity_set._c[0, direction]
                    y_direction = velocity_set._c[1, direction]
                    on_boundary = False
                    on_boundary = (
                        on_boundary or i + x_direction < 0 or i + x_direction >= grid.shape[0]
                    )  # check if on edge of grid, automatically counts as boundary node too
                    on_boundary = (
                        on_boundary or j + y_direction < 0 or j + y_direction >= grid.shape[1]
                    )

                    # check if boundary node
                    boundary_node = False
                    cur_x, cur_y = i * dx, j * dx
                    bc_x, bc_y = cur_x, cur_y
                    q_ij = 0.5

                    if on_boundary:  # if already on boundary of grid, just move the 0.5 to the side
                        boundary_node = True
                        bc_x = cur_x + 0.5 * dx * x_direction
                        bc_y = cur_y + 0.5 * dx * y_direction
                    elif host_boundary_info[0, (i + x_direction), (j + y_direction), 0] == 0:
                        boundary_node = True
                        max_steps = 1000
                        stepsize = dx / max_steps
                        counter = 0
                        while (
                            potential(bc_x, bc_y) < 0
                        ):  # otherwise distance to boundary needs to be found, move along direction of pathway until on boundary
                            bc_x += stepsize * x_direction
                            bc_y += stepsize * y_direction
                            counter += 1
                            assert counter <= (max_steps + 1)
                        q_ij = counter / max_steps

                    # if dirichlet bc: set values
                    if boundary_node and indicator(bc_x, bc_y) < 0:
                        host_boundary_info[direction + 1, i, j, 0] = 1
                        host_boundary_info[0, i, j, 0] = 2
                        for k in range(values_per_direction - 1):
                            host_boundary_values[direction * values_per_direction + k, i, j, 0] = (
                                bc_dirichlet[k](bc_x, bc_y)
                            )
                        host_boundary_values[
                            (direction + 1) * values_per_direction - 1, i, j, 0
                        ] = q_ij
                    elif boundary_node and indicator(bc_x, bc_y) > 0:  # if VN: find T
                        host_boundary_info[direction + 1, i, j, 0] = 1
                        opposite_direction = velocity_set.opp_indices[direction]
                        # host_boundary_info[1 + 9 + opposite_direction, i, j, 0] = 1
                        host_boundary_info[0, i, j, 0] = 3
                        # find n
                        n = [dx_potential(bc_x, bc_y), dy_potential(bc_x, bc_y)]
                        n = n / (np.linalg.norm(n))  # normalise
                        # if on edge of domain: normals cant be calculated with potential
                        if on_boundary:
                            n = [0.0, 0.0]
                            if i + x_direction < 0 or i + x_direction >= grid.shape[0]:
                                n[0] = x_direction
                                n[1] = 0
                            if j + y_direction < 0 or j + y_direction >= grid.shape[1]:
                                n[0] = 0
                                n[1] = y_direction

                        # find T
                        dx_ux = bc_dirichlet[2](bc_x, bc_y)
                        dy_ux = bc_dirichlet[3](bc_x, bc_y)
                        dx_uy = bc_dirichlet[4](bc_x, bc_y)
                        dy_uy = bc_dirichlet[5](bc_x, bc_y)
                        T_x = (
                            (
                                (K - mu) * (dx_ux + dy_uy) * n[0]
                                + mu * (2 * dx_ux * n[0] + (dx_uy + dy_ux) * n[1])
                            )
                            * L
                            / kappa
                        )
                        T_y = (
                            (
                                (K - mu) * (dx_ux + dy_uy) * n[1]
                                + mu * ((dx_uy + dy_ux) * n[0] + 2 * dy_uy * n[1])
                            )
                            * L
                            / kappa
                        )

                        # write to array
                        host_boundary_values[direction * values_per_direction, i, j, 0] = n[0]
                        host_boundary_values[direction * values_per_direction + 1, i, j, 0] = n[1]
                        host_boundary_values[direction * values_per_direction + 2, i, j, 0] = T_x
                        host_boundary_values[direction * values_per_direction + 3, i, j, 0] = T_y
                        host_boundary_values[
                            (direction + 1) * values_per_direction - 1, i, j, 0
                        ] = q_ij

    # move to device
    return wp.from_numpy(host_boundary_info, dtype=wp.int8), wp.from_numpy(
        host_boundary_values, dtype=precision_policy.store_precision.wp_dtype
    )
