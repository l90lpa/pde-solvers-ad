from jax import config, vjp, jvp, jit
config.update("jax_enable_x64", True)
import jax.numpy as jnp
from math import pi, ceil
import numpy as np
import matplotlib.pyplot as plt
from rk3 import *

def create_advection_opeartor(dx, n):
    
    @jit
    def advection_op(u):
        dx2 = dx * 2
        u_new = (jnp.roll(u, -1) - jnp.roll(u, 1)) / dx2
        return u_new
    
    return advection_op

def solver_rk3(u_initial, v, dx, num_points, dt, num_steps):
    A = create_advection_opeartor(dx, num_points)

    @jit
    def f(u):
        return - v * A(u)
    
    return RK3(f, u_initial, dt, num_steps)


def solver_rk3_tlm(u_initial, du_initial, v, dx, num_points, dt, num_steps):
    A = create_advection_opeartor(dx, num_points)

    @jit
    def f(u):
        return - v * A(u)
    
    _, dy = RK3_tlm(f, u_initial, du_initial, dt, num_steps)
    return dy

def solver_rk3_adm(u_initial, Du, v, dx, num_points, dt, num_steps):
    A = create_advection_opeartor(dx, num_points)

    @jit
    def f(u):
        return - v * A(u)
    
    _, Du_initial = RK3_adm(f, u_initial, Du, dt, num_steps)
    return Du_initial
    

# Example usage
if __name__ == "__main__":
    # Define problem parameters
    num_points = 100
    domain_length = 1.0
    dx = domain_length / num_points
    v = 1.2
    C = 0.1 # Courant number
    dt = (dx / v) * C  # Time step size
    num_steps = ceil(1.0 * (domain_length / (dt * v)))

    # Create the initial condition (e.g., a sinusoidal profile)
    x = jnp.linspace(0, domain_length - dx, num_points)
    u_initial = jnp.sin((2*pi/domain_length) * x)
    u_initial_p = np.concatenate((u_initial[len(u_initial)-1:len(u_initial)],u_initial[:len(u_initial)-1]))

    solver_partial = lambda u0 : solver_rk3(u0, v, dx, num_points, dt, num_steps)
    
    # Run solver
    u_final = solver_partial(u_initial)

    # Plot the results
    plt.plot(x, u_initial, label="Initial Condition")
    plt.plot(x, u_final, label=f"Solution after {num_steps} time steps")
    plt.xlabel("Position (x)")
    plt.ylabel("Solution (u)")
    plt.legend()
    plt.show()

    num_steps = 8

    def m(u):
        return solver_rk3(u, v, dx, num_points, dt, num_steps)

    def TLM(u, du):
        return solver_rk3_tlm(u, du, v, dx, num_points, dt, num_steps)

    def ADM(u, Dv):
        return solver_rk3_adm(u, Dv, v, dx, num_points, dt, num_steps)

    def testTLMLinearity(TLM, tol):
        rng = np.random.default_rng(12345)
        N = 100
        u0 = rng.random((N,), dtype=np.float64)
        du = rng.random((N,), dtype=np.float64)
        dv = np.array(TLM(jnp.array(u0), jnp.array(du)))
        dv2 = np.array(TLM(jnp.array(u0), jnp.array(2.0*du)))
        absolute_error = np.linalg.norm(dv2 - 2.0*dv)
        return absolute_error < tol, absolute_error

    def testTLMApprox(m, TLM, tol):
        rng = np.random.default_rng(12345)
        N = 100
        u0 = rng.random((N,), dtype=np.float64)
        v0 = m(jnp.array(u0))

        du = rng.random((N,), dtype=np.float64)
        dv = np.array(TLM(jnp.array(u0), jnp.array(du)))
        
        scale = 1.0

        absolute_errors = []
        relavite_errors = []
        for i in range(15):
            v1 = np.array(m(jnp.array(u0 + (scale * du))))
            absolute_error = np.linalg.norm((scale * dv) - (v1 - v0))
            absolute_errors.append(absolute_error)
            relative_error = absolute_error / np.linalg.norm(v1 - v0)
            relavite_errors.append(relative_error)
            scale /= 10.0

        # print(absolute_errors)
        # print(relavite_errors)
        min_relative_error = np.min(relavite_errors)

        return min_relative_error < tol, min_relative_error

    def testADMApprox(TLM, ADM, tol):
        rng = np.random.default_rng(12345)
        N = 100
        u0 = rng.random((N,), dtype=np.float64)
        du =  rng.random((N,), dtype=np.float64)

        dv = np.array(TLM(jnp.array(u0), jnp.array(du)))

        M = jnp.size(dv)
        Dv = rng.random((M,), dtype=np.float64)
        Du = np.array(ADM(jnp.array(u0), jnp.array(Dv))).flatten()
        
        absolute_error = np.abs(np.dot(dv, Dv) - np.dot(du, Du))
        return absolute_error < tol, absolute_error

    print("Test TLM Linearity:")
    success, absolute_error = testTLMLinearity(TLM, 1.0e-13)
    print("success = ", success, ", absolute_error = ", absolute_error)

    print("Test TLM Approximation:")
    success, relative_error = testTLMApprox(m, TLM, 1.0e-13)
    print("success = ", success, ", relative error = ", relative_error)

    print("Test ADM Approximation:")
    success, absolute_error = testADMApprox(TLM, ADM, 1.0e-13)
    print("success = ", success, ", relative absolute_error = ", absolute_error)










