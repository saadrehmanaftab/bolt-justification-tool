import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd, pytest
from boltjust.joint import Joint, Factors, margins, THREADS
from boltjust.postprocess import read_fe_export, run

def test_preload_from_torque_matches_hand_calculation():
    j = Joint(size="M10", torque=50e3, mu_thread=0.12, mu_head=0.12)
    t = THREADS["M10"]
    lever = 0.16 * 1.5 + 0.58 * 9.026 * 0.12 + 0.12 * (16.0 + 11.0) / 4      # mm, worked by hand
    assert math.isclose(j.preload_nominal(), 50e3 / lever, rel_tol=1e-9)

def test_load_factor_between_zero_and_load_introduction_factor():
    phi = Joint().load_factor()
    assert 0 < phi < Joint().n_load

def test_thermal_preload_sign():
    j = Joint()                      # aluminium part expands more than the steel bolt
    assert j.thermal_preload_change(80) > 0 > j.thermal_preload_change(-60)

def test_margins_fall_with_load():
    j = Joint()
    a = margins(j, 1000, 500, 0); b = margins(j, 8000, 2000, 0)
    assert b["mos_yield"] < a["mos_yield"] and b["mos_separation"] < a["mos_separation"] and b["mos_slip"] < a["mos_slip"]

def test_missing_columns_rejected(tmp_path):
    p = tmp_path / "bad.csv"; pd.DataFrame({"bolt_id": [1]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        read_fe_export(p)

def test_end_to_end_report(tmp_path):
    root = pathlib.Path(__file__).resolve().parents[1]
    s, res = run(root / "data/fe_interface_loads.csv", tmp_path, Joint(size="M12", grade="12.9", torque=115e3, DA=32.0))
    assert (tmp_path / "report.md").exists() and (tmp_path / "margins.csv").exists()
    assert s["evaluations"] == 32 and s["failing"] == 0
