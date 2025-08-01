from xlb.operator import Operator
from xlb.experimental.thermo_mechanical.kernel_provider import KernelProvider
from xlb.compute_backend import ComputeBackend
import warp as wp


class Prolongation(Operator):
    def __init__(
        self,
        velocity_set=None,
        precision_policy=None,
        compute_backend=None,
    ):
        super().__init__(
            velocity_set=velocity_set,
            precision_policy=precision_policy,
            compute_backend=compute_backend,
        )

    def _construct_warp(self):
        kernel_provider = KernelProvider()
        vec = kernel_provider.vec
        calc_moments = kernel_provider.calc_moments
        calc_equilibrium = kernel_provider.calc_equilibrium
        calc_populations = kernel_provider.calc_populations
        write_population_to_global = kernel_provider.write_population_to_global
        read_local_population = kernel_provider.read_local_population
        zero_vec = kernel_provider.zero_vec

        @wp.func
        def functional(f_a: vec, f_b: vec, f_c: vec, f_d: vec):
            m_a = calc_moments(f_a)
            m_b = calc_moments(f_b)
            m_c = calc_moments(f_c)
            m_d = calc_moments(f_d)

            m_out = self.compute_dtype(0.25) * (m_a + m_b + m_c + m_d)

            # scale necessary components of m
            m_out[0] = self.compute_dtype(1) * m_out[0]
            m_out[1] = self.compute_dtype(1) * m_out[1]
            m_out[2] = self.compute_dtype(0.5) * m_out[2]
            m_out[3] = self.compute_dtype(0.5) * m_out[3]
            m_out[4] = self.compute_dtype(0.5) * m_out[4]
            m_out[5] = self.compute_dtype(1) * m_out[5]
            m_out[6] = self.compute_dtype(1) * m_out[6]
            m_out[7] = self.compute_dtype(0.5) * m_out[7]
            m_out[8] = self.compute_dtype(1) * m_out[8]

            f_out = calc_populations(m_out)

            return f_out

        @wp.kernel
        def kernel_no_bc(
            fine: wp.array4d(dtype=self.store_dtype),
            coarse: wp.array4d(dtype=self.store_dtype),
            coarse_nodes_x: wp.int32,
            coarse_nodes_y: wp.int32,
        ):
            i, j, k = wp.tid()

            coarse_i = i / 2
            coarse_j = j / 2  # rounds down

            res_i = i - coarse_i * 2
            res_j = j - coarse_j * 2

            _f_a = read_local_population(coarse, coarse_i, coarse_j)
            _f_b = read_local_population(
                coarse, wp.mod(coarse_i + 1 + coarse_nodes_x, coarse_nodes_x), coarse_j
            )
            _f_c = read_local_population(
                coarse, coarse_i, wp.mod(coarse_j + 1 + coarse_nodes_y, coarse_nodes_y)
            )
            _f_d = read_local_population(
                coarse,
                wp.mod(coarse_i + 1 + coarse_nodes_x, coarse_nodes_x),
                wp.mod(coarse_j + 1 + coarse_nodes_y, coarse_nodes_y),
            )

            if res_i == 0 and res_j == 0:
                _error_approx = functional(f_a=_f_a, f_b=_f_a, f_c=_f_a, f_d=_f_a)
            elif res_i == 1 and res_j == 0:
                _error_approx = functional(f_a=_f_a, f_b=_f_b, f_c=_f_a, f_d=_f_b)
            elif res_i == 0 and res_j == 1:
                _error_approx = functional(f_a=_f_a, f_b=_f_c, f_c=_f_a, f_d=_f_c)
            else:
                _error_approx = functional(f_a=_f_a, f_b=_f_b, f_c=_f_c, f_d=_f_d)

            _f_old = read_local_population(fine, i, j)
            _f_out = vec()
            for l in range(self.velocity_set.q):
                _f_out[l] = _f_old[l] + _error_approx[l]

            write_population_to_global(fine, _f_out, i, j)

        @wp.kernel
        def kernel_with_bc(
            fine: wp.array4d(dtype=self.store_dtype),
            coarse: wp.array4d(dtype=self.store_dtype),
            coarse_nodes_x: wp.int32,
            coarse_nodes_y: wp.int32,
            coarse_boundary_array: wp.array4d(dtype=wp.int8),
        ):
            i, j, k = wp.tid()

            coarse_i = i / 2
            coarse_j = j / 2  # rounds down

            res_i = i - coarse_i * 2
            res_j = j - coarse_j * 2

            _f_a = read_local_population(coarse, coarse_i, coarse_j)
            _f_b = read_local_population(
                coarse, wp.mod(coarse_i + 1 + coarse_nodes_x, coarse_nodes_x), coarse_j
            )
            _f_c = read_local_population(
                coarse, coarse_i, wp.mod(coarse_j + 1 + coarse_nodes_y, coarse_nodes_y)
            )
            _f_d = read_local_population(
                coarse,
                wp.mod(coarse_i + 1 + coarse_nodes_x, coarse_nodes_x),
                wp.mod(coarse_j + 1 + coarse_nodes_y, coarse_nodes_y),
            )

            # check for boundary
            if coarse_boundary_array[0, coarse_i, coarse_j, 0] == wp.int8(0):
                _f_a = zero_vec()
            if coarse_boundary_array[
                0, wp.mod(coarse_i + 1 + coarse_nodes_x, coarse_nodes_x), coarse_j, 0
            ] == wp.int8(0):
                _f_b = zero_vec()
            if coarse_boundary_array[
                0, coarse_i, wp.mod(coarse_j + 1 + coarse_nodes_y, coarse_nodes_y), 0
            ] == wp.int8(0):
                _f_c = zero_vec()
            if coarse_boundary_array[
                0,
                wp.mod(coarse_i + 1 + coarse_nodes_x, coarse_nodes_x),
                wp.mod(coarse_j + 1 + coarse_nodes_y, coarse_nodes_y),
                0,
            ] == wp.int8(0):
                _f_d = zero_vec()

            if res_i == 0 and res_j == 0:
                _error_approx = functional(f_a=_f_a, f_b=_f_a, f_c=_f_a, f_d=_f_a)
            elif res_i == 1 and res_j == 0:
                _error_approx = functional(f_a=_f_a, f_b=_f_b, f_c=_f_a, f_d=_f_b)
            elif res_i == 0 and res_j == 1:
                _error_approx = functional(f_a=_f_a, f_b=_f_c, f_c=_f_a, f_d=_f_c)
            else:
                _error_approx = functional(f_a=_f_a, f_b=_f_b, f_c=_f_c, f_d=_f_d)

            _f_old = read_local_population(fine, i, j)
            _f_out = vec()
            for l in range(self.velocity_set.q):
                _f_out[l] = _f_old[l] + _error_approx[l]

            write_population_to_global(fine, _f_out, i, j)

        return functional, (kernel_no_bc, kernel_with_bc)

    @Operator.register_backend(ComputeBackend.WARP)
    def warp_implementation(self, fine, coarse, coarse_boundary_array=None):
        coarse_nodes_x = coarse.shape[1]
        coarse_nodes_y = coarse.shape[2]
        if coarse_boundary_array is None:
            wp.launch(
                self.warp_kernel[0],
                inputs=[fine, coarse, coarse_nodes_x, coarse_nodes_y],
                dim=fine.shape[1:],
            )
        else:
            wp.launch(
                self.warp_kernel[1],
                inputs=[fine, coarse, coarse_nodes_x, coarse_nodes_y, coarse_boundary_array],
                dim=fine.shape[1:],
            )
