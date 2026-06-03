"""Zhu et al. (2017) global geospatial liquefaction model — verified implementation.

Source: Zhu, Baise & Thompson (2017), "An Updated Geospatial Liquefaction Model for
Global Application", Earthquake Spectra 33(4):1365-1385. Coefficients cross-checked
against GEM OpenQuake secondary-perils implementation.

Model 2 (general / non-coastal) — the model we use because WATER TABLE DEPTH (wtd) is
an explicit predictor (our GRACE attribution lever):

    X = 8.801 + 0.334 ln(PGV) - 1.918 ln(Vs30) + 0.0005408*precip - 0.2054*dw - 0.0333*wtd
    P(liq) = 1 / (1 + exp(-X))        # logistic; physically-correct sign convention

Sign check (why -X, not +X): higher PGV -> higher X -> higher P (more shaking) OK;
lower Vs30 -> higher X (softer soil) OK; SHALLOWER water table (smaller wtd) -> higher X
-> higher P OK. So a rising water table (Δwtd<0) RAISES liquefaction probability — the
mechanism (Wang et al. 2025, Nat Commun). The OpenQuake doc's "1/(1+e^X)" is a typo.

Areal coverage (Liquefaction Spatial Extent, %): L(P) = a/(1+b*exp(-c*P))^2
    Model 2: a=49.15, b=42.40, c=9.165

Heuristics: P:=0 if PGV<3 cm/s or Vs30>620 m/s.

Units: PGV cm/s; Vs30 m/s; precip mm/yr; dw km (min dist to water body); wtd m.
"""
from __future__ import annotations
import numpy as np

# --- Model 2 coefficients (general model, uses wtd) ---
B0, B_PGV, B_VS30, B_PRECIP, B_DW, B_WTD = 8.801, 0.334, -1.918, 0.0005408, -0.2054, -0.0333
# Model 1 (coastal) kept for cross-check (uses dc, dr; NO wtd)
M1 = dict(b0=12.435, bpgv=0.301, bvs30=-2.615, bprecip=0.0005556, bsqdc=-0.0287, bdr=0.0666, bdcdr=-0.0369)
# LSE coverage constants
LSE = {"m2": (49.15, 42.40, 9.165), "m1": (42.08, 62.59, 11.43)}
PGV_MIN, VS30_MAX = 3.0, 620.0


def liquefaction_X_model2(pgv, vs30, precip, dw, wtd):
    pgv = np.asarray(pgv, float); vs30 = np.asarray(vs30, float)
    precip = np.asarray(precip, float); dw = np.asarray(dw, float); wtd = np.asarray(wtd, float)
    return (B0 + B_PGV*np.log(np.maximum(pgv, 1e-3)) + B_VS30*np.log(np.maximum(vs30, 1.0))
            + B_PRECIP*precip + B_DW*dw + B_WTD*wtd)


def p_liquefaction(pgv, vs30, precip, dw, wtd, apply_heuristics=True):
    """Zhu-2017 Model-2 probability of liquefaction occurrence."""
    X = liquefaction_X_model2(pgv, vs30, precip, dw, wtd)
    P = 1.0 / (1.0 + np.exp(-X))
    if apply_heuristics:
        P = np.where((np.asarray(pgv, float) < PGV_MIN) | (np.asarray(vs30, float) > VS30_MAX), 0.0, P)
    return P


def lse_percent(P, model="m2"):
    a, b, c = LSE[model]
    return a / (1.0 + b*np.exp(-c*np.asarray(P, float)))**2


def dP_dwtd(pgv, vs30, precip, dw, wtd):
    """Analytic sensitivity dP/dwtd = P(1-P)*B_WTD (per metre). Negative: deeper->lower P."""
    P = p_liquefaction(pgv, vs30, precip, dw, wtd, apply_heuristics=False)
    return P * (1.0 - P) * B_WTD


# --- PGA -> PGV conversion (for hazard-map PGA_475; documented assumption) -------------
def pga_to_pgv(pga_g, k=100.0):
    """Representative PGV (cm/s) from 475-yr PGA (g) via ratio k (cm/s per g).
    Default k=100 within the empirical PGV/PGA range for M6.5-7.5 stiff-site motions
    (Bommer & Alarcon 2006; Wald et al. 1999). Sensitivity tested over k in [60,150].
    Upgrade path: PGV ~= 156 * SA(T=1s, g)  (peak pseudo-spectral velocity)."""
    return k * np.asarray(pga_g, float)


def pgv_from_sa1(sa1_g):
    """Physically-grounded PGV (cm/s) ~= (g*T/2pi)*PSA(1s) with T=1s, g=981 cm/s^2."""
    return (981.0 * 1.0 / (2*np.pi)) * np.asarray(sa1_g, float)


if __name__ == "__main__":
    # sanity: a shallow-GW soft-soil coastal city under strong shaking
    pgv = pga_to_pgv(0.4)          # 0.4 g -> 40 cm/s
    for wtd in [1, 2, 5, 10, 20]:
        P = p_liquefaction(pgv, 250, 1200, 0.5, wtd)
        print(f"wtd={wtd:>2} m  P_liq={float(P):.3f}  LSE={float(lse_percent(P)):.1f}%  dP/dwtd={float(dP_dwtd(pgv,250,1200,0.5,wtd)):.4f}/m")
    print("\n1 m water-table RISE (wtd 5->4 m):",
          f"ΔP = {float(p_liquefaction(pgv,250,1200,0.5,4) - p_liquefaction(pgv,250,1200,0.5,5)):+.4f}")
