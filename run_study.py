"""Runs the example: the FE interface export through two joint designs (design change M8 to M10)."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
from boltjust.joint import Joint, Factors
from boltjust.postprocess import run

root = pathlib.Path(__file__).parent
designs = {"M8_10.9": Joint(size="M8", grade="10.9", torque=30e3),
           "M10_10.9": Joint(size="M10", grade="10.9", torque=58e3, DA=28.0),
           "M12_12.9": Joint(size="M12", grade="12.9", torque=115e3, DA=32.0)}
out = {}
for name, j in designs.items():
    s, _ = run(root / "data/fe_interface_loads.csv", root / "results" / name, j, Factors())
    out[name] = s
(root / "results/design_comparison.json").write_text(json.dumps(out, indent=2))
print(json.dumps({k: dict(failing=v["failing"], min_mos=round(v["min_mos"], 2), governing=v["governing"], runtime_ms=round(v["runtime_ms"],1)) for k, v in out.items()}, indent=1))
