import csv
import json
import warnings

import qiskit
import qiskit_aer
from qiskit import transpile
from qiskit.providers.fake_provider import Fake20QV1
from qiskit_aer import AerSimulator

from circuit import grover, theory

warnings.filterwarnings("ignore", category=DeprecationWarning)

N_VALUES = [2, 3, 4]
K_VALUES = range(1, 10)
LEVELS = [0, 1, 2, 3]
SEEDS = range(10)
SHOTS = 4096

BACKEND = Fake20QV1()
CALIBRATION = BACKEND.properties()
IDEAL_SIM = AerSimulator()
NOISY_SIM = AerSimulator.from_backend(BACKEND)
cx_errors = [CALIBRATION.gate_error("cx", pair) for pair in BACKEND.configuration().coupling_map]
MEAN_CX_ERROR = sum(cx_errors) / len(cx_errors)


def count_cx(qc):
    return qc.count_ops().get("cx", 0)


def count_1q(qc):
    ops = qc.count_ops()
    return ops.get("u1", 0) + ops.get("u2", 0) + ops.get("u3", 0)


def physical_qubits(qc):
    return sorted({qc.find_bit(q).index for gate in qc.data for q in gate.qubits})


def success_rate(counts, n):
    return counts.get("0" * n, 0) / sum(counts.values())


def fidelity_actual(qc):
    f = 1.0
    for gate in qc.data:
        if gate.operation.name == "cx":
            f *= 1 - CALIBRATION.gate_error("cx", [qc.find_bit(q).index for q in gate.qubits])
    return f


def predicted_success(fidelity, n, k):
    N = 2 ** n
    return fidelity * theory(n, k) + (1 - fidelity) / N


def run(n, k, level, seed):
    qc = grover(n, k)
    before = transpile(qc, basis_gates=BACKEND.configuration().basis_gates, optimization_level=0)
    after = transpile(qc, backend=BACKEND, optimization_level=level, seed_transpiler=seed)
    sim_seed = 1000 * n + 100 * k + 10 * level + seed
    ideal = IDEAL_SIM.run(after, shots=SHOTS, seed_simulator=sim_seed).result().get_counts()
    noisy = NOISY_SIM.run(after, shots=SHOTS, seed_simulator=sim_seed).result().get_counts()
    f_mean = (1 - MEAN_CX_ERROR) ** count_cx(after)
    f_actual = fidelity_actual(after)
    return {
        "n": n, "k": k, "level": level, "seed": seed,
        "depth_before": before.depth(), "cx_before": count_cx(before),
        "depth_after": after.depth(), "cx_after": count_cx(after), "oneq_after": count_1q(after),
        "physical_qubits": " ".join(str(q) for q in physical_qubits(after)),
        "p_theory": theory(n, k),
        "p_ideal": success_rate(ideal, n),
        "p_noisy": success_rate(noisy, n),
        "fidelity_mean": f_mean, "p_pred_mean": predicted_success(f_mean, n, k),
        "fidelity_actual": f_actual, "p_pred_actual": predicted_success(f_actual, n, k),
    }


rows = []
for n in N_VALUES:
    for k in K_VALUES:
        print(f"n={n} k={k}")
        rows += [run(n, k, level, seed) for level in LEVELS for seed in SEEDS]

with open("data/grid.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

with open("data/grid.json", "w") as f:
    json.dump({
        "rows": len(rows), "shots": SHOTS, "marked_item": 0,
        "backend": "Fake20QV1 (test backend bundled with Qiskit)",
        "calibration_date": str(CALIBRATION.last_update_date),
        "mean_cx_error": MEAN_CX_ERROR,
        "qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
    }, f, indent=2)
