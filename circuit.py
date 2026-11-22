import math

from qiskit import QuantumCircuit


def flip_sign_of_zero(qc, n):
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))


def grover(n, k):
    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    for _ in range(k):
        flip_sign_of_zero(qc, n)  # oracle, marked item 0
        qc.h(range(n))            # diffusion
        flip_sign_of_zero(qc, n)
        qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def theory(n, k):
    theta = math.asin(1 / math.sqrt(2 ** n))
    return math.sin((2 * k + 1) * theta) ** 2
