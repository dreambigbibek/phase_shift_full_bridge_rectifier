"""
Si7336ADP-based loss and ZVS analysis for the PSFB converter.

Standalone: no inputs needed, just run it.

Device data: Vishay Siliconix Si7336ADP, datasheet document 73152.
Converter currents: LTspice .meas output at each load point.
"""

# ---- Si7336ADP datasheet (Vishay doc 73152) ----
VDS_RATING = 30.0      # V
ID_25C     = 30.0      # A continuous @ Ta=25C
ID_70C     = 25.0      # A continuous @ Ta=70C
RDSON_10V  = 2.4e-3    # ohm, typ @ Vgs=10V, Id=25A
RDSON_45V  = 3.1e-3    # ohm, typ @ Vgs=4.5V
QG         = 36e-9     # C, typ @ Vgs=4.5V, Vds=15V
COSS       = 860e-12   # F @ Vds=15V
VSD        = 0.72      # V typ @ 2.9A
RTH_JA     = 50.0      # C/W steady state
TJ_MAX     = 150.0

# Rds(on) of a 30V silicon MOSFET rises roughly 50% by Tj = 125C
HOT = 1.5
RDSON_HOT = RDSON_10V * HOT

# ---- Converter operating points ----
FS   = 100e3
TD   = 150e-9         # bridge dead time
VBUS = 400.0
N    = 22.0
LLK  = 4e-6

OPS = {
    # load : (Pout, Vout, Iout, Iprim_pk, Iprim_rms, Isec_pk, Isec_rms)
    '100%': (2977.95, 13.4558, 221.313, 12.734,  10.857,  281.25, 223.09),
    '50%':  (1514.28, 13.478,  112.35,   7.182,   5.849,  162.31, 116.12),
    '25%':  ( 752.99, 13.526,   55.665,  3.5327,  3.1176,  69.582, 58.339),
}

print("=" * 78)
print("1. ZVS THRESHOLD  (real Coss = 860 pF, not an assumed 200 pF)")
print("=" * 78)
Q_need = 2 * COSS * VBUS
I_need_charge = Q_need / TD
I_need_energy = VBUS * (2 * COSS / LLK) ** 0.5
print("  Charge to move per leg transition  Q = 2*Coss*Vbus = %.0f nC" % (Q_need * 1e9))
print("  Dead time available                td = %.0f ns" % (TD * 1e9))
print("  --> charge-balance criterion       I >= %.2f A" % I_need_charge)
print("  --> resonant-energy criterion      I >= %.2f A" % I_need_energy)
print()
for k, (P, V, I, ipk, irms, spk, srms) in OPS.items():
    verdict = "ZVS" if ipk >= I_need_charge else "NO ZVS"
    print("  %5s load: Iprim_pk = %6.2f A  vs %.2f A required -> %-7s (%.2fx)"
          % (k, ipk, I_need_charge, verdict, ipk / I_need_charge))
print()
print("  For comparison, an assumed Coss = 200 pF gives:")
print("    I_required = %.2f A -> would predict ZVS at ALL loads, contradicting the sim"
      % (2 * 200e-12 * VBUS / TD))
print()

print("=" * 78)
print("2. PRIMARY CONDUCTION LOSS IF Si7336ADP WERE USED AT 400 V (as simulated)")
print("=" * 78)
for k, (P, V, I, ipk, irms, spk, srms) in OPS.items():
    print("  %5s load: Iprim_rms = %6.3f A -> %5.2f W (25C) / %5.2f W (125C)"
          % (k, irms, 2 * irms ** 2 * RDSON_10V, 2 * irms ** 2 * RDSON_HOT))
print("\n  NOTE: device Vds rating = %.0f V vs bus = %.0f V, i.e. %.1fx OVER RATING."
      % (VDS_RATING, VBUS, VBUS / VDS_RATING))
print("  Valid as simulation, not buildable. A real primary needs a 650 V device.")
print()

print("=" * 78)
print("3. SECONDARY SYNCHRONOUS RECTIFIER PARALLELING STUDY (100% load)")
print("=" * 78)
P100, V100, I100, ipk100, irms100, spk100, srms100 = OPS['100%']
print("  Secondary winding RMS current = %.2f A" % srms100)
print("  Reflected blocking voltage    = Vin/n = %.1f V (vs 30 V rating, %.2fx margin)"
      % (VBUS / N, VDS_RATING / (VBUS / N)))
print()
print("  %5s %10s %10s %13s %14s %9s" %
      ("N/pos", "Rds_eff", "Irms/dev", "P_tot(25C)", "P_tot(125C)", "Tj rise"))
for Npar in [1, 2, 4, 6, 8, 10, 12]:
    p_cold = 2 * srms100 ** 2 * (RDSON_10V / Npar)
    p_hot = 2 * srms100 ** 2 * (RDSON_HOT / Npar)
    irms_dev = (srms100 / 2 ** 0.5) / Npar
    tj_rise = (p_hot / (4 * Npar)) * RTH_JA
    flag = "  <-- exceeds current rating" if irms_dev > ID_70C else ""
    print("  %5d %8.3fmR %9.1fA %12.1fW %13.1fW %8.0fC%s"
          % (Npar, (RDSON_10V / Npar) * 1e3, irms_dev, p_cold, p_hot, tj_rise, flag))
NPAR = 8
print("\n  --> adopted: N = %d per position (%d devices total)" % (NPAR, 4 * NPAR))
print()

print("=" * 78)
print("4. LOSS BUDGET AT 100%% LOAD (secondary = %dx Si7336ADP per position)" % NPAR)
print("=" * 78)
P_sec_cond = 2 * srms100 ** 2 * (RDSON_HOT / NPAR)
TD_SR, VSD_HI = 100e-9, 1.0   # Vsd rises above the 2.9A datasheet point at ~28A/device
P_sec_diode = 2 * VSD_HI * I100 * (2 * TD_SR * FS)
P_sec_gate = (4 * NPAR) * QG * 10.0 * FS

RDSON_650, QG_650 = 70e-3, 60e-9      # representative 650 V superjunction part
P_pri_cond = 2 * irms100 ** 2 * (RDSON_650 * 1.7)
P_pri_gate = 4 * QG_650 * 12.0 * FS
P_pri_swoff = 4 * 0.5 * VBUS * (ipk100 / 2) * 20e-9 * FS * 0.5   # Coss snubs turn-off

losses = [
    ("Secondary conduction (%dx Si7336ADP, hot)" % (4 * NPAR), P_sec_cond),
    ("Primary conduction (4x 650 V SJ MOSFET, hot)",           P_pri_cond),
    ("Secondary body-diode conduction (SR dead time)",         P_sec_diode),
    ("Primary turn-off switching (turn-on ~0 under ZVS)",      P_pri_swoff),
    ("Secondary gate drive",                                   P_sec_gate),
    ("Primary gate drive",                                     P_pri_gate),
]
for name, v in losses:
    print("  %-56s %8.2f W" % (name, v))
tot = sum(v for _, v in losses)
print("  %s %s" % ("-" * 56, "-" * 8))
print("  %-56s %8.2f W" % ("TOTAL SEMICONDUCTOR LOSS", tot))
print("\n  Pout = %.1f W, Pin(est) = %.1f W" % (P100, P100 + tot))
print("  --> semiconductor-only efficiency = %.2f %%" % (100 * P100 / (P100 + tot)))
print("  Magnetics loss is NOT included, so treat this as an upper bound.")
print()
P_sec_1 = 2 * srms100 ** 2 * RDSON_HOT
print("  With only ONE device per secondary position:")
print("    secondary conduction = %.1f W -> total %.1f W -> efficiency %.1f %%"
      % (P_sec_1, tot - P_sec_cond + P_sec_1,
         100 * P100 / (P100 + tot - P_sec_cond + P_sec_1)))
print()

print("=" * 78)
print("5. LIGHT-LOAD HARD-SWITCHING PENALTY AT 25% LOAD")
print("=" * 78)
P25 = OPS['25%'][0]
E_hard = 0.5 * COSS * VBUS ** 2
P_hard = E_hard * 2 * FS       # two transitions per period on the lagging leg
print("  Energy per hard transition  E = 0.5*Coss*Vbus^2 = %.1f uJ" % (E_hard * 1e6))
print("  Lagging-leg loss            P = 2*E*fs          = %.2f W" % P_hard)
print("  As a fraction of the %.0f W output              = %.2f %%"
      % (P25, 100 * P_hard / P25))
