"""Bolted joint calculation, simplified and in the spirit of VDI 2230 Part 1.

NOT a certified implementation of VDI 2230 or ECSS-E-HB-32-23A. Simplifications are listed in the README.
Units: N, mm, MPa, K.
"""
from dataclasses import dataclass
import math

# metric coarse threads: pitch P, pitch diameter d2, minor diameter d3, stress area As (ISO 724 / ISO 898-1 values)
THREADS = {
    "M6":  dict(d=6.0,  P=1.00, d2=5.350,  d3=4.773, As=20.1, dw=10.0, dh=6.6),
    "M8":  dict(d=8.0,  P=1.25, d2=7.188,  d3=6.466, As=36.6, dw=13.0, dh=9.0),
    "M10": dict(d=10.0, P=1.50, d2=9.026,  d3=8.160, As=58.0, dw=16.0, dh=11.0),
    "M12": dict(d=12.0, P=1.75, d2=10.863, d3=9.853, As=84.3, dw=18.0, dh=13.5),
}
RP02 = {"8.8": 640.0, "10.9": 940.0, "12.9": 1100.0}     # minimum 0.2% proof stress, MPa (ISO 898-1, d <= 16 mm)

@dataclass
class Joint:
    size: str = "M8"
    grade: str = "10.9"
    clamp_length: float = 20.0      # l_k, mm
    DA: float = 24.0                # outer diameter of the clamped parts, mm
    E_bolt: float = 205e3
    E_part: float = 70e3            # aluminium flange
    alpha_bolt: float = 11.5e-6     # 1/K
    alpha_part: float = 23.0e-6
    torque: float = 30.0e3          # tightening torque, N mm
    mu_thread: float = 0.12
    mu_head: float = 0.12
    mu_interface: float = 0.15      # friction in the joint interface (slip)
    scatter: float = 0.25           # preload scatter +/- from torque tightening
    embedding: float = 0.011        # embedding loss, mm
    n_load: float = 0.5             # load introduction factor

    @property
    def t(self):
        return THREADS[self.size]

    def preload_nominal(self):
        """Preload from tightening torque: M_A = F_M (0.16 P + 0.58 d2 mu_G + mu_K D_Km / 2)."""
        t = self.t
        DKm = (t["dw"] + t["dh"]) / 2
        return self.torque / (0.16 * t["P"] + 0.58 * t["d2"] * self.mu_thread + self.mu_head * DKm / 2)

    def resilience_bolt(self):
        """delta_S: shank in the clamp length on the stress area plus head and engaged thread allowances."""
        t = self.t; Anom = math.pi * t["d"] ** 2 / 4; A3 = math.pi * t["d3"] ** 2 / 4
        return (self.clamp_length / (self.E_bolt * t["As"]) + 0.5 * t["d"] / (self.E_bolt * Anom)
                + 0.5 * t["d"] / (self.E_bolt * A3) + 0.4 * t["d"] / (self.E_bolt * Anom))

    def resilience_part(self):
        """delta_P with the substitutional cylinder of the clamped parts."""
        t = self.t; dw, dh, lk = t["dw"], t["dh"], self.clamp_length
        DA = max(self.DA, dw)
        x = (lk * dw / DA ** 2) ** (1 / 3)
        A_ers = math.pi / 4 * (dw ** 2 - dh ** 2) + math.pi / 8 * dw * (DA - dw) * ((x + 1) ** 2 - 1)
        return lk / (self.E_part * A_ers)

    def load_factor(self):
        dS, dP = self.resilience_bolt(), self.resilience_part()
        return self.n_load * dP / (dS + dP)

    def thermal_preload_change(self, dT):
        """Preload change when the part and the bolt expand differently: dF = (a_P - a_S) dT l_k / (d_S + d_P)."""
        return (self.alpha_part - self.alpha_bolt) * dT * self.clamp_length / (self.resilience_bolt() + self.resilience_part())

    def embedding_loss(self):
        return self.embedding / (self.resilience_bolt() + self.resilience_part())

    def equivalent_stress(self, F_bolt, F_assembly):
        """Von Mises stress in the bolt: tension from F_bolt, thread torsion from the assembly preload (k = 0.5)."""
        t = self.t; d0 = (t["d2"] + t["d3"]) / 2
        sigma = F_bolt / t["As"]
        tau = F_assembly * (0.16 * t["P"] + 0.58 * t["d2"] * self.mu_thread) / (math.pi * d0 ** 3 / 16)
        return math.sqrt(sigma ** 2 + 3 * (0.5 * tau) ** 2)

@dataclass
class Factors:
    yield_fos: float = 1.25
    separation_fos: float = 1.2
    slip_fos: float = 1.25

def margins(j: Joint, F_axial, F_transverse, dT, f: Factors = Factors()):
    """Margins of safety MoS = capacity / (factored demand) - 1 for yield, separation and slip."""
    FM = j.preload_nominal()
    FM_max, FM_min = FM * (1 + j.scatter), FM * (1 - j.scatter)
    phi = j.load_factor()
    dF_th = j.thermal_preload_change(dT)
    Fz = j.embedding_loss()
    FA = max(F_axial, 0.0)
    # yield: maximum preload, thermal increase if positive, bolt share of the factored axial load
    F_bolt = FM_max + max(dF_th, 0.0) + phi * FA * f.yield_fos
    mos_yield = RP02[j.grade] / j.equivalent_stress(F_bolt, FM_max) - 1
    # residual clamp force with minimum preload, embedding and thermal loss if negative
    F_clamp_min = FM_min - Fz + min(dF_th, 0.0)
    mos_sep = F_clamp_min / max((1 - phi) * FA * f.separation_fos, 1e-9) - 1
    F_residual = F_clamp_min - (1 - phi) * FA
    mos_slip = (j.mu_interface * max(F_residual, 0.0)) / max(F_transverse * f.slip_fos, 1e-9) - 1
    return dict(preload_nominal=FM, load_factor=phi, thermal_dF=dF_th, embedding_loss=Fz,
                F_bolt_max=F_bolt, F_clamp_min=F_clamp_min, mos_yield=mos_yield, mos_separation=mos_sep, mos_slip=mos_slip)
