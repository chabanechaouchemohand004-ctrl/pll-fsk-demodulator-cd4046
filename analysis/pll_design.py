"""Design of a CD4046 FSK demodulator (XOR phase comparator, one-pole RC loop filter).

Prints the design table and writes the model figures to ../figures/.
Run: python analysis/pll_design.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

FIG = Path(__file__).resolve().parent.parent / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 10, "legend.fontsize": 8.5,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "axes.linewidth": 0.7,
    "xtick.direction": "in", "ytick.direction": "in", "legend.frameon": False,
    "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.5,
    "lines.linewidth": 1.3, "axes.titlelocation": "left"})
NAVY, RED, GREY, LIGHT, INK = "#1f3a5f", "#9a3b2e", "#6e6e6e", "#c8c8c8", "#222222"

# ---- Specification -------------------------------------------------------
VDD, VSS = 5.0, -5.0            # supply rails (V)
V_SPACE, V_MARK = -2.5, 2.5     # data levels (V)
F_SPACE, F_MARK = 800.0, 1200.0  # FSK tones (Hz)
ZETA = 0.5                      # target damping
C_FILTER = 100e-9               # chosen loop-filter capacitor (F)

# ---- VCO -----------------------------------------------------------------
k0_hz = (F_MARK - F_SPACE) / (V_MARK - V_SPACE)   # Hz/V
k0 = 2 * np.pi * k0_hz                            # rad/s/V
f_center = (F_MARK + F_SPACE) / 2
f_vco_min = f_center + k0_hz * VSS
f_vco_max = f_center + k0_hz * VDD

# ---- XOR phase comparator ------------------------------------------------
# Mean output goes from VSS to VDD when the phase shift goes from 0 to pi.
kd = (VDD - VSS) / np.pi                          # V/rad

# ---- Loop: H(s) = K / (tau s^2 + s + K) ----------------------------------
K = k0 * kd                                       # loop gain (1/s)
tau = 1 / (4 * ZETA**2 * K)                       # from zeta = 1 / (2 sqrt(K tau))
wn = np.sqrt(K / tau)
fn = wn / (2 * np.pi)
R_FILTER = tau / C_FILTER
f3db = fn * np.sqrt(1 - 2 * ZETA**2 + np.sqrt((1 - 2 * ZETA**2) ** 2 + 1))

# ---- Ranges --------------------------------------------------------------
# Lock: the XOR phase error can move by +/- pi/2 around quadrature.
df_lock = K * (np.pi / 2) / (2 * np.pi)           # +/- Hz
lock_lo, lock_hi = f_center - df_lock, f_center + df_lock
# Capture: datasheet approximation 2 fc = (1/pi) sqrt(2 pi 2fL / tau).
capture_full = np.sqrt(2 * np.pi * 2 * df_lock / tau) / np.pi

# ---- Step response of the demodulated output (space -> mark) -------------
loop = signal.TransferFunction([K], [tau, 1, K])
t = np.linspace(0, 8e-3, 4000)
_, y = signal.step(loop, T=t)
overshoot = (y.max() - 1) * 100
t10, t90 = t[np.argmax(y >= 0.1)], t[np.argmax(y >= 0.9)]
outside = np.where(np.abs(y - 1) > 0.05)[0]
t_settle = t[outside[-1] + 1]
baud_model = 2 * f3db   # 0101 pattern at D baud has its fundamental at D/2

rows = [
    ("VCO gain K0", f"{k0_hz:.0f} Hz/V"),
    ("Centre frequency", f"{f_center:.0f} Hz"),
    ("VCO range at the rails", f"{f_vco_min:.0f} to {f_vco_max:.0f} Hz"),
    ("Phase comparator gain KD", f"{kd:.2f} V/rad"),
    ("Loop gain K = 2 pi K0 KD", f"{K:.0f} 1/s"),
    ("Filter time constant tau", f"{tau*1e6:.0f} us"),
    (f"R for C = {C_FILTER*1e9:.0f} nF", f"{R_FILTER/1e3:.2f} kOhm"),
    ("Natural frequency fn", f"{fn:.0f} Hz"),
    ("-3 dB loop bandwidth", f"{f3db:.0f} Hz"),
    ("Lock range", f"{lock_lo:.0f} to {lock_hi:.0f} Hz"),
    ("Capture range (datasheet estimate)", f"{capture_full:.0f} Hz"),
    ("Step overshoot", f"{overshoot:.1f} %"),
    ("Rise time 10-90 %", f"{(t90-t10)*1e3:.2f} ms"),
    ("Settling time to 5 %", f"{t_settle*1e3:.2f} ms"),
    ("Bit rate with D/2 = f3dB", f"{baud_model:.0f} baud"),
]
for name, value in rows:
    print(f"{name:38s} {value}")


def fig_block():
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    ax.set_axis_off(); ax.grid(False)
    ax.set_xlim(0, 14.4); ax.set_ylim(0, 5)

    def box(x, y, w, h, text):
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec=INK, lw=0.9))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=INK, fontsize=9)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, shrinkA=0, shrinkB=0))

    box(1.9, 2.6, 2.0, 1.2, "VCO\n(4046 no. 1)")
    box(6.0, 2.6, 1.9, 1.2, "XOR phase\ncomparator")
    box(9.0, 2.6, 1.8, 1.2, "RC loop\nfilter")
    box(7.5, 0.4, 2.0, 1.2, "VCO\n(4046 no. 2)")
    arrow(0.2, 3.2, 1.9, 3.2); ax.text(0.2, 3.4, "data\n$\\pm$2.5 V", fontsize=8.5, color=INK, va="bottom")
    arrow(3.9, 3.2, 6.0, 3.2); ax.text(4.95, 3.4, "FSK\n800 / 1200 Hz", fontsize=8.5, color=INK, ha="center", va="bottom")
    arrow(7.9, 3.2, 9.0, 3.2)
    ax.plot([10.8, 13.9], [3.2, 3.2], color=INK, lw=0.9); arrow(13.0, 3.2, 14.2, 3.2)
    ax.text(12.6, 3.4, "demodulated\ndata (pin 9)", fontsize=8.5, color=NAVY, ha="center", va="bottom")
    ax.plot([11.6, 11.6], [3.2, 1.0], color=INK, lw=0.9); arrow(11.6, 1.0, 9.5, 1.0)
    ax.plot(11.6, 3.2, "o", ms=3, color=INK)
    ax.plot([7.5, 5.2, 5.2], [1.0, 1.0, 2.9], color=INK, lw=0.9); arrow(5.2, 2.9, 6.0, 2.9)
    ax.text(1.9, 4.35, "Modulator", fontsize=9, color=GREY)
    ax.text(6.0, 4.35, "Demodulator (phase-locked loop)", fontsize=9, color=GREY)
    fig.savefig(FIG / "01_block_diagram.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_vco():
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    v = np.array([VSS, VDD])
    ax.plot(v, f_center + k0_hz * v, color=NAVY, label=f"design line, $K_0$ = {k0_hz:.0f} Hz/V")
    ax.plot([V_SPACE, V_MARK], [F_SPACE, F_MARK], "o", color=RED, ms=5, label="space and mark (specification)")
    ax.plot([VSS, 0, VDD], [f_vco_min, f_center, f_vco_max], "o", mfc="white", color=NAVY, ms=5,
            label="rails and centre")
    ax.set_xlabel("VCO control voltage (V)"); ax.set_ylabel("VCO frequency (Hz)")
    ax.set_title("VCO characteristic to set on the 4046", fontsize=10)
    ax.set_xlim(-5.6, 5.6); ax.set_ylim(500, 1500); ax.legend(loc="upper left")
    fig.savefig(FIG / "02_vco_design_line.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_loop():
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.0))
    vout = V_SPACE + (V_MARK - V_SPACE) * y
    a.plot(t * 1e3, vout, color=NAVY, label="model, $\\zeta$ = 0.5")
    a.axhline(V_MARK, color=GREY, lw=0.7, ls="--")
    a.set_xlabel("time after a space-to-mark step (ms)"); a.set_ylabel("demodulated output (V)")
    a.set_title("(a) Step response", fontsize=10); a.set_xlim(0, 8); a.legend(loc="lower right")
    f = np.logspace(1, 3.6, 400)
    _, h = signal.freqresp(loop, 2 * np.pi * f)
    b.semilogx(f, 20 * np.log10(np.abs(h)), color=NAVY, label="model")
    b.axvline(f3db, color=RED, lw=0.9, ls="--", label=f"$-$3 dB at {f3db:.0f} Hz")
    b.set_xlabel("modulation frequency (Hz)"); b.set_ylabel("closed-loop gain (dB)")
    b.set_title("(b) Loop bandwidth", fontsize=10); b.set_ylim(-30, 5); b.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "03_loop_model.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


fig_block(); fig_vco(); fig_loop()
