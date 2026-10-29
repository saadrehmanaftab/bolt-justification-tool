# Bolted joint justification from FE interface loads (personal project, assumed data)

A small Python tool that post processes an FE interface load export into bolted joint margins of safety and writes
an automated justification report. It covers a thermomechanical effect: the change of preload when the aluminium
flange and the steel bolt expand differently with temperature.

## What it does
- `boltjust.joint`: preload from tightening torque, bolt and part resilience (substitutional cylinder), load factor,
  embedding loss, thermal preload change, von Mises bolt stress with thread torsion, and margins of safety
  MoS = capacity / factored demand - 1 for bolt yield, joint separation and slip.
- `boltjust.postprocess`: reads the FE export (`load_case, bolt_id, F_axial_N, F_transverse_N, dT_K`), evaluates every
  bolt in every load case, flags failures and writes `margins.csv`, `report.md` and `summary.json`.
- Command line: `PYTHONPATH=src python -m boltjust data/fe_interface_loads.csv results/out`
- `run_study.py`: the example, three joint designs on the same export (design change M8, M10, M12).

## Results of the example run (`results/design_comparison.json`)
- 8 bolts x 4 load cases (nominal, peak bending, hot +80 K, cold -60 K) = 32 bolt checks per design, a few ms per run.
- M8 10.9: 16 of 32 fail, governed by slip in the cold, high bending case (minimum MoS -0.88).
- M10 10.9: 6 of 32 fail (minimum MoS -0.42).
- M12 12.9: all 32 pass, minimum MoS +0.11, governed by bolt yield in the hot case, where thermal expansion raises the preload.

## Assumed data
- The FE export is SYNTHETIC: `data/make_example_export.py` distributes assumed resultants (axial force, bending,
  shear, torsion) over 8 bolts with rigid flange theory. It stands in for a real FE interface load export.
- Joint values: aluminium flange (E 70 GPa, alpha 23e-6/K), steel bolts (E 205 GPa, alpha 11.5e-6/K), friction 0.12 in
  thread and head and 0.15 in the interface, preload scatter +/-25%, embedding 11 micrometres, load introduction factor 0.5,
  factors of safety 1.25 (yield), 1.2 (separation), 1.25 (slip). Thread data from ISO 724, proof stress from ISO 898-1.

## Limits
- Simplified and only in the spirit of VDI 2230 Part 1. It is NOT a VDI 2230 or ECSS-E-HB-32-23A implementation and
  must not be used to justify hardware.
- No thread stripping, fatigue, prying, temperature dependent material data or creep. One bolt size per run.

## Tests
`python -m pytest` checks the torque to preload relation against a hand calculation, the load factor range, the sign of the
thermal preload change, margin trends, input validation and the end to end report.
