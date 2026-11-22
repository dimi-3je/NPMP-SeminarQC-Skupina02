import csv
import getpass
import json
import sys

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from circuit import grover, theory

CASES = [(2, 1), (2, 2), (3, 1), (3, 2), (3, 3), (4, 1), (4, 2), (4, 3)]
LEVEL = 3
SHOTS = 4096


def two_qubit_count(qc):
    ops = qc.count_ops()
    return sum(ops.get(g, 0) for g in ("cx", "ecr", "cz"))


if "--login" in sys.argv:
    QiskitRuntimeService.save_account(
        channel="ibm_quantum_platform",
        token=getpass.getpass("IBM Quantum API key: "),
        instance=input("Instance CRN (Enter = default): ") or None,
        set_as_default=True, overwrite=True)
    sys.exit()

service = QiskitRuntimeService()

if "--fetch" in sys.argv:
    with open("data/ibm_job.json") as f:
        job_info = json.load(f)
    job = service.job(job_info["job_id"])
else:
    backend = service.least_busy(operational=True, simulator=False)
    # the backend's default "ibm_dynamic_circuits" translation plugin requires Qiskit 2.x
    pm = generate_preset_pass_manager(backend=backend, optimization_level=LEVEL, seed_transpiler=0,
                                      translation_method="translator")
    circuits = [pm.run(grover(n, k)) for n, k in CASES]
    job = SamplerV2(mode=backend).run(circuits, shots=SHOTS)
    job_info = {
        "job_id": job.job_id(), "backend": backend.name,
        "level": LEVEL, "shots": SHOTS, "cases": CASES,
        "depth_after": [c.depth() for c in circuits],
        "two_qubit_after": [two_qubit_count(c) for c in circuits],
    }
    with open("data/ibm_job.json", "w") as f:
        json.dump(job_info, f, indent=2)
    print(f"job {job.job_id()} on {backend.name}")

result = job.result()

backend = service.backend(job_info["backend"])
two_q_gate = next(g for g in ("cz", "ecr", "cx") if g in backend.target)
errors = [p.error for p in backend.target[two_q_gate].values() if p and p.error is not None and p.error < 1]
eps = sum(errors) / len(errors)
print(f"mean {two_q_gate} error {eps:.4f}")

with open("data/ibm.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["n", "k", "backend", "job_id", "level", "shots", "depth_after", "two_qubit_after",
                "mean_2q_error", "p_theory", "p_pred", "p_hardware"])
    for i, (n, k) in enumerate(job_info["cases"]):
        counts = result[i].data.c.get_counts()
        p = counts.get("0" * n, 0) / sum(counts.values())
        g = job_info["two_qubit_after"][i]
        fidelity = (1 - eps) ** g
        p_pred = fidelity * theory(n, k) + (1 - fidelity) / 2 ** n
        w.writerow([n, k, job_info["backend"], job_info["job_id"], job_info["level"], job_info["shots"],
                    job_info["depth_after"][i], g, f"{eps:.4f}", f"{theory(n, k):.3f}", f"{p_pred:.3f}", f"{p:.3f}"])
        print(f"n={n} k={k}: hardware {p:.3f}, predicted {p_pred:.3f}, theory {theory(n, k):.3f}")
