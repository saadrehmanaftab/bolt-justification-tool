"""Post processing of an FE interface load export into bolt margins of safety and an automated report."""
import json, pathlib, time
import pandas as pd
from .joint import Joint, Factors, margins

REQUIRED = ["load_case", "bolt_id", "F_axial_N", "F_transverse_N", "dT_K"]

def read_fe_export(path):
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"FE export misses columns: {missing}")
    return df

def evaluate(df, joint: Joint, factors: Factors = Factors()):
    rows = []
    for r in df.itertuples(index=False):
        m = margins(joint, r.F_axial_N, r.F_transverse_N, r.dT_K, factors)
        rows.append(dict(load_case=r.load_case, bolt_id=r.bolt_id, F_axial_N=r.F_axial_N,
                         F_transverse_N=r.F_transverse_N, dT_K=r.dT_K, **m))
    res = pd.DataFrame(rows)
    res["min_mos"] = res[["mos_yield", "mos_separation", "mos_slip"]].min(axis=1)
    res["governing"] = res[["mos_yield", "mos_separation", "mos_slip"]].idxmin(axis=1).str.replace("mos_", "")
    res["status"] = res["min_mos"].apply(lambda v: "OK" if v >= 0 else "FAIL")
    return res

def write_report(res, out_dir, joint: Joint, factors: Factors, runtime_s):
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "margins.csv", index=False)
    worst = res.loc[res.min_mos.idxmin()]
    per_case = res.groupby("load_case").agg(min_mos=("min_mos", "min"), failing_bolts=("status", lambda s: (s == "FAIL").sum()))
    lines = [
        "# Bolted joint justification report", "",
        f"Joint: {joint.size} grade {joint.grade}, clamp length {joint.clamp_length} mm, torque {joint.torque/1000:.1f} N m, "
        f"factors of safety yield {factors.yield_fos}, separation {factors.separation_fos}, slip {factors.slip_fos}.",
        f"Bolt load cases evaluated: {len(res)} ({res.bolt_id.nunique()} bolts x {res.load_case.nunique()} load cases) in {runtime_s*1000:.1f} ms.", "",
        "| load case | min margin of safety | failing bolts |", "|---|---|---|",
        *[f"| {lc} | {v.min_mos:+.2f} | {int(v.failing_bolts)} |" for lc, v in per_case.iterrows()], "",
        f"Governing: bolt {worst.bolt_id}, load case {worst.load_case}, {worst.governing}, margin {worst.min_mos:+.2f}.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    summary = dict(evaluations=int(len(res)), bolts=int(res.bolt_id.nunique()), load_cases=int(res.load_case.nunique()),
                   failing=int((res.status == "FAIL").sum()), min_mos=float(res.min_mos.min()),
                   governing=dict(bolt=int(worst.bolt_id), load_case=str(worst.load_case), check=str(worst.governing)),
                   runtime_ms=runtime_s * 1000,
                   preload_nominal_N=float(res.preload_nominal.iloc[0]), load_factor=float(res.load_factor.iloc[0]))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary

def run(fe_csv, out_dir, joint: Joint = Joint(), factors: Factors = Factors()):
    t0 = time.perf_counter()
    res = evaluate(read_fe_export(fe_csv), joint, factors)
    return write_report(res, out_dir, joint, factors, time.perf_counter() - t0), res
