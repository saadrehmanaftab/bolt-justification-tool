"""Writes data/fe_interface_loads.csv: a SYNTHETIC stand in for an FE interface load export.

Assumed flange: 8 bolts on a 100 mm pitch circle. Bolt loads from assumed resultants per load case
(axial force F, bending moment M, shear Q, torsion T), distributed as rigid flange theory would:
F_i = F/n + M y_i / sum(y^2), Q_i = Q/n + T / (n r). This replaces a real FE run and is labelled as such.
"""
import math, pathlib, csv
n, r = 8, 50.0
CASES = {   # F N, M N mm, Q N, T N mm, dT K
    "LC1_nominal":       (4000.0, 0.8e6, 2000.0, 0.3e6, 0.0),
    "LC2_peak_bending":  (6000.0, 2.2e6, 3500.0, 0.6e6, 0.0),
    "LC3_hot_+80K":      (4000.0, 0.8e6, 2000.0, 0.3e6, 80.0),
    "LC4_cold_-60K":     (6000.0, 2.2e6, 3500.0, 0.6e6, -60.0),
}
out = pathlib.Path(__file__).with_name("fe_interface_loads.csv")
with open(out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["load_case", "bolt_id", "F_axial_N", "F_transverse_N", "dT_K"])
    ys = [r * math.sin(2 * math.pi * i / n) for i in range(n)]; sy2 = sum(y * y for y in ys)
    for lc, (F, M, Q, T, dT) in CASES.items():
        for i, y in enumerate(ys, start=1):
            w.writerow([lc, i, round(F / n + M * y / sy2, 1), round(Q / n + T / (n * r), 1), dT])
print("wrote", out)
