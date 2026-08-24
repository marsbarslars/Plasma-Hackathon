"""Live chart panel composited beside the 3D render.

Two panels, both driven by the particles present in the current frame:

* a |B| scale bar spanning the field's own range, with a live marker showing
  where the particles are actually sitting in the field — it climbs as they
  approach the throats;
* the (v_par, v_perp) distribution, where the loss cone empties out over the run.

Rendered with Agg into an RGB array so it can be stacked next to a PyVista
screenshot; nothing here opens a window.
"""

from __future__ import annotations

import numpy as np

CIVIDIS_LO = "#00224E"
ACCENT = "#FFEA46"
INK = "#DDE3EC"


class ChartPanel:
    """Fixed-size matplotlib panel, redrawn per frame.

    Axis limits are locked from the first frame so the charts do not jitter as
    particles are lost.
    """

    def __init__(self, width_px, height_px, b_range, v_scale, loss_cone_deg,
                 dpi=100):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        self.dpi = dpi
        self.b_lo, self.b_hi = b_range
        self.v_scale = v_scale
        self.theta_lc = loss_cone_deg

        self.fig = plt.figure(
            figsize=(width_px / dpi, height_px / dpi), dpi=dpi,
            facecolor="black")
        self.fig.subplots_adjust(left=0.17, right=0.94, top=0.92, bottom=0.07,
                                 hspace=0.42)

        gs = self.fig.add_gridspec(2, 1, height_ratios=[0.5, 3.9])
        self.ax_b = self.fig.add_subplot(gs[0])
        self.ax_v = self.fig.add_subplot(gs[1])

        for ax in (self.ax_b, self.ax_v):
            ax.set_facecolor("black")
            for spine in ax.spines.values():
                spine.set_color("#4A5568")
            ax.tick_params(colors=INK, labelsize=8)
            ax.xaxis.label.set_color(INK)
            ax.yaxis.label.set_color(INK)
            ax.title.set_color(INK)

        self._setup_b_bar()
        self._setup_velocity()

    # ---------------------------------------------------------------- |B| bar

    def _setup_b_bar(self):
        ax = self.ax_b
        grad = np.linspace(0, 1, 256)[None, :]
        ax.imshow(grad, aspect="auto", cmap="cividis",
                  extent=[self.b_lo, self.b_hi, 0, 1])
        ax.set_yticks([])
        ax.set_xlabel("|B| sampled by particles  [T]", fontsize=9, labelpad=2)
        ax.set_title("Magnetic field strength", fontsize=11, loc="left",
                     pad=24, fontweight="medium", color=INK)
        ax.set_xlim(self.b_lo, self.b_hi)

        # live artists
        self._b_span = ax.axvspan(self.b_lo, self.b_lo, color="white",
                                  alpha=0.25, lw=0)
        self._b_line = ax.axvline(self.b_lo, color="white", lw=2.0)
        # Sits between title and bar, inside the figure.
        self._b_text = ax.annotate(
            "", xy=(0, 1), xycoords="axes fraction",
            xytext=(0, 5), textcoords="offset points",
            ha="left", va="bottom", color="#9AA6B8", fontsize=9)

    def _update_b_bar(self, bmag):
        if len(bmag) == 0:
            return
        lo, hi = np.percentile(bmag, [10, 90])
        mean = float(np.mean(bmag))
        # axvspan gives a Rectangle in current matplotlib, so move it by
        # origin+width rather than rebuilding a polygon path.
        self._b_span.set_x(lo)
        self._b_span.set_width(max(hi - lo, 1e-12))
        self._b_line.set_xdata([mean, mean])
        self._b_text.set_text(
            f"mean {mean:.3f} T      10-90%  {lo:.3f} - {hi:.3f} T")

    # ------------------------------------------------------- velocity space

    def _setup_velocity(self):
        ax = self.ax_v
        v = self.v_scale
        self.xedges = np.linspace(-v, v, 96)
        self.yedges = np.linspace(0, v, 48)

        self._v_img = ax.pcolormesh(
            self.xedges, self.yedges, np.zeros((len(self.yedges) - 1,
                                                len(self.xedges) - 1)),
            cmap="cividis", vmin=0, vmax=1)

        edge = np.tan(np.radians(90 - self.theta_lc))
        vv = np.linspace(0, v, 10)
        for sgn in (-1, 1):
            ax.plot(sgn * vv * edge, vv, c=ACCENT, lw=1.2, ls="--", alpha=0.9)

        ax.set_xlim(-v, v); ax.set_ylim(0, v)
        ax.set_xlabel("$v_\\parallel$  [10$^6$ m/s]", fontsize=9, labelpad=2)
        ax.set_ylabel("$v_\\perp$  [10$^6$ m/s]", fontsize=9, labelpad=2)
        ax.set_title("Velocity distribution", fontsize=11, loc="left", pad=24,
                     fontweight="medium", color=INK)
        ax.annotate(f"dashed: loss cone at {self.theta_lc:.1f}$^\\circ$",
                    xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 5), textcoords="offset points",
                    ha="left", va="bottom", color="#9AA6B8", fontsize=9)
        self._v_text = ax.text(0.97, 0.95, "", transform=ax.transAxes,
                               ha="right", va="top", color=INK, fontsize=9)

    def _update_velocity(self, vpar, vperp, n_total):
        h, _, _ = np.histogram2d(vpar / 1e6, vperp / 1e6,
                                 bins=[self.xedges, self.yedges])
        # Fixed ceiling from a robust quantile keeps the colour scale steady.
        top = max(np.percentile(h[h > 0], 96) if np.any(h > 0) else 1.0, 1.0)
        self._v_img.set_array(h.T.ravel())
        self._v_img.set_clim(0, top)
        self._v_text.set_text(f"{len(vpar)} of {n_total} confined")

    # ------------------------------------------------------------------ draw

    def render(self, bmag, vpar, vperp, n_total) -> np.ndarray:
        """Update both panels and return the panel as an RGB array."""
        self._update_b_bar(bmag)
        self._update_velocity(vpar, vperp, n_total)
        self.fig.canvas.draw()
        buf = np.asarray(self.fig.canvas.buffer_rgba())
        return buf[:, :, :3].copy()

    def close(self):
        import matplotlib.pyplot as plt
        plt.close(self.fig)


def stack_side_by_side(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Join two RGB frames horizontally, padding to the taller one."""
    h = max(left.shape[0], right.shape[0])
    out = np.zeros((h, left.shape[1] + right.shape[1], 3), dtype=np.uint8)
    out[:left.shape[0], :left.shape[1]] = left
    out[:right.shape[0], left.shape[1]:] = right
    return out
