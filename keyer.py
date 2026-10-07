"""Keying core for generated video (backdrop model, matte, colour clean-up). Pure torch, no ComfyUI imports.

Why one pass instead of two
---------------------------
Triangulation (two renders over two backgrounds) needs the subject to be
identical in both renders, including the semi-transparent pixels. A diffusion
model cannot regenerate a background *behind* a held subject: holding the
subject at denoise 0 also holds whatever was behind its soft edges, and the
VAE decoder mixes neighbouring latents, so the edges never match. The solve
then returns opaque blocks with the old background baked in, and coloured
noise wherever the two passes drifted.

So the shot is generated once, over a backdrop, and keyed with a model of the
backdrop rather than an assumed colour:

1. **Backdrop analysis.** The key colour and type (chroma / black / white) are
   read from the frame border, robustly, across the clip.
2. **Clean plate.** A generated backdrop is never flat: gradients, vignettes and
   colour shifts are normal. A per-frame plate is estimated at low resolution
   from confident backdrop pixels and pushed under the subject with push-pull
   hole filling, then smoothed in space and time. Every pixel is keyed against
   *its own* local backdrop, which is what removes haze and edge halos.
3. **Matte.** Colour-difference (screen) keying for green/blue, unmultiply
   for glow on black, and its mirror for smoke/ink on white. Two-pass
   triangulation is still available when passes really are identical.
4. **Refinement.** Edge-aware temporal smoothing (motion-gated, so moving
   edges never ghost), a colour guided filter that snaps the matte to full
   resolution image edges (this repairs 4:2:0 chroma blockiness), levels,
   despeckle, hold-out / garbage masks, choke and softness.
5. **Colour.** The foreground is un-mixed from the plate
   ``F = (C - (1-a) P) / a``, despilled, and colour-extended under low alpha
   so edges never pick up a dark or green fringe in the composite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

import torch
import torch.nn.functional as F

try:
    from .imageops import (LUMA, box, gaussian, guided_filter_color, luma, max_pool, min_pool,
                           push_pull, resize, to_nchw)
except ImportError:  # imported standalone (tests)
    from imageops import (LUMA, box, gaussian, guided_filter_color, luma, max_pool, min_pool,
                          push_pull, resize, to_nchw)

# The Pro stages live in keyer_pro.py, which the free edition does not contain.
try:
    from . import keyer_pro as pro
except ImportError:
    try:
        import keyer_pro as pro
    except ImportError:
        pro = None
HAS_PRO = pro is not None

BACKDROPS = ("auto", "green", "blue", "black", "white", "custom")
PRESET_COLORS = {
    "green": (0.0, 0.69, 0.25),
    "blue": (0.0, 0.28, 0.73),
    "black": (0.0, 0.0, 0.0),
    "white": (1.0, 1.0, 1.0),
}


@dataclass
class KeySettings:
    backdrop: str = "auto"            # one of BACKDROPS
    custom_color: str = "#00B140"
    screen_gain: float = 1.0          # >1 removes more, <1 keeps more
    screen_balance: float = 0.0       # 0 = max(others) (safest), 1 = mean(others)
    shadows: str = "keep"             # keep | remove (chroma only)
    plate_fix: float = 1.0            # 0 = flat key colour, 1 = full local plate
    clip_black: float = 0.03
    clip_white: float = 0.95
    edge_solve: bool = True           # colour-line solve for saturated subjects
    edge_detail: int = 2              # guided-filter radius in px (0 = off)
    choke: float = 0.0                # px, + shrinks, - grows
    softness: float = 0.0             # px blur on the final matte
    despill: float = 1.0
    edge_extend: bool = True
    despeckle: int = 8                # area in px of isolated faint specks to remove
    fill_holes: int = 0               # radius in px of enclosed holes to fill (0 = off)
    temporal: float = 0.5             # 0..1 (matte smoothing across frames; Pro)
    plate_temporal: Optional[float] = None   # backdrop-plate smoothing; None = follow ``temporal``


@dataclass
class BackdropInfo:
    kind: str                          # chroma | black | white
    color: tuple                       # rgb 0..1
    channel: int = 1                   # dominant channel for chroma
    confidence: float = 1.0            # share of border that matches the key
    source: str = "auto"
    warnings: list = field(default_factory=list)

    def hex(self) -> str:
        return "#" + "".join(f"{int(round(max(0, min(1, c)) * 255)):02X}" for c in self.color)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["hex"] = self.hex()
        return d


# ----------------------------------------------------------------------------
# small image ops (tensors are N,C,H,W)
# ----------------------------------------------------------------------------



















def parse_hex(text: str, default=(0.0, 0.69, 0.25)) -> tuple:
    s = str(text or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    try:
        if len(s) != 6:
            raise ValueError
        return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return default


# ----------------------------------------------------------------------------
# backdrop analysis and clean plate
# ----------------------------------------------------------------------------

def _small(frames_nchw: torch.Tensor, long_side: int = 160) -> torch.Tensor:
    h, w = frames_nchw.shape[-2:]
    s = min(1.0, long_side / float(max(h, w)))
    size = (max(8, int(round(h * s))), max(8, int(round(w * s))))
    return resize(frames_nchw, size, "area")


def _border(x: torch.Tensor, frac: float = 0.06) -> torch.Tensor:
    """Pixels of the outer band, as (N, 3)."""
    n, c, h, w = x.shape
    bh, bw = max(1, int(h * frac)), max(1, int(w * frac))
    parts = [x[..., :bh, :], x[..., -bh:, :], x[..., bh:-bh, :bw], x[..., bh:-bh, -bw:]]
    return torch.cat([p.permute(0, 2, 3, 1).reshape(-1, c) for p in parts], 0)


def classify_color(rgb, source="auto") -> BackdropInfo:
    r, g, b = [float(v) for v in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    warnings = []
    if mx - mn >= 0.12:
        kind, ch = "chroma", int(max(range(3), key=lambda i: (r, g, b)[i]))
    elif (r + g + b) / 3.0 < 0.35:
        kind, ch = "black", 1
    elif (r + g + b) / 3.0 > 0.6:
        kind, ch = "white", 1
    else:
        kind, ch = ("white" if (r + g + b) / 3.0 >= 0.47 else "black"), 1
        warnings.append(
            "The backdrop is a mid grey, which cannot be keyed cleanly. Regenerate over pure "
            "green, black or white (see the Backdrop recipe)."
        )
    return BackdropInfo(kind=kind, color=(r, g, b), channel=ch, source=source, warnings=warnings)


def detect_backdrop(frames: torch.Tensor, settings: KeySettings) -> BackdropInfo:
    """frames: T,H,W,3 (any device). Reads the border of up to 12 frames."""
    t = int(frames.shape[0])
    idx = torch.linspace(0, t - 1, steps=min(12, t)).round().long().unique()
    small = _small(to_nchw(frames[idx.to(frames.device)]).float())
    px = _border(small)
    med = px.median(0).values
    for _ in range(2):
        d = (px - med).abs().amax(1)
        near = px[d < 0.18]
        if near.shape[0] >= 16:
            med = near.median(0).values
    confidence = float(((px - med).abs().amax(1) < 0.12).float().mean())

    choice = str(settings.backdrop or "auto").lower()
    if choice == "auto":
        info = classify_color(med.tolist(), "auto")
    else:
        if choice == "custom":
            hint = parse_hex(settings.custom_color)
        else:
            hint = PRESET_COLORS.get(choice, PRESET_COLORS["green"])
        info = classify_color(hint, choice)
        if choice in ("black", "white"):
            info.kind = choice
            info.warnings = []
        # Use the measured border colour when it agrees with the requested type,
        # since a generated "green" is rarely the textbook green.
        measured = classify_color(med.tolist(), "auto")
        if measured.kind == info.kind and (info.kind != "chroma" or measured.channel == info.channel):
            info.color = measured.color
        elif confidence > 0.5:
            info.warnings.append(
                f"The border looks {measured.kind}"
                + (f" ({'RGB'[measured.channel]}-dominant)" if measured.kind == "chroma" else "")
                + f", not {choice}. Check the Backdrop setting, or use Auto."
            )
    info.confidence = confidence
    if confidence < 0.35:
        info.warnings.append(
            f"Only {confidence * 100:.0f}% of the frame border matches the backdrop. The subject "
            "may touch the edges, or the backdrop is uneven. Plate correction will compensate, "
            "but a cleaner backdrop gives a cleaner matte."
        )
    return info


def screen(x: torch.Tensor, ch: int, balance: float) -> torch.Tensor:
    """Colour-difference 'screen' signal: key channel minus the others."""
    others = [i for i in range(3) if i != ch]
    o1, o2 = x[:, others[0]:others[0] + 1], x[:, others[1]:others[1] + 1]
    o = (1.0 - balance) * torch.maximum(o1, o2) + balance * 0.5 * (o1 + o2)
    return x[:, ch:ch + 1] - o


def _bg_weight(x: torch.Tensor, info: BackdropInfo, settings: KeySettings,
               plate: Optional[torch.Tensor] = None) -> torch.Tensor:
    """Confidence that a pixel is backdrop. Without a plate the test is shading
    invariant (a vignetted corner is still backdrop); with one it is relative
    to the local plate, which is the precise test."""
    key = torch.tensor(info.color, dtype=x.dtype, device=x.device).view(1, 3, 1, 1)
    ref = key if plate is None else plate
    if info.kind == "chroma":
        bal = settings.screen_balance
        if plate is None:
            nx = x / x.amax(1, keepdim=True).clamp_min(0.05)
            nk = ref / ref.amax(1, keepdim=True).clamp_min(0.05)
            sk = screen(nk, info.channel, bal).clamp_min(0.04)
            a0 = 1.0 - screen(nx, info.channel, bal) / sk
            dark = (x.amax(1, keepdim=True) < 0.25 * ref.amax(1, keepdim=True)).to(x.dtype)
            a0 = torch.maximum(a0, dark)
        else:
            sk = screen(ref, info.channel, bal).clamp_min(0.04)
            a0 = 1.0 - screen(x, info.channel, bal) / sk
        # Relative to a plate the test can be strict, so faint smoke is never
        # mistaken for backdrop and absorbed into it.
        w = (1.0 - a0 / (0.2 if plate is None else 0.06)).clamp(0, 1)
    elif info.kind == "black":
        v = x.amax(1, keepdim=True) - ref.amax(1, keepdim=True)
        w = (1.0 - v / 0.05).clamp(0, 1)
    else:
        v = ref.amin(1, keepdim=True) - x.amin(1, keepdim=True)
        w = (1.0 - v / 0.05).clamp(0, 1)
    w = w * w
    # Stay away from soft edges: they are part subject.
    return min_pool(w, 1 if plate is None else 2)


def estimate_plates(frames: torch.Tensor, info: BackdropInfo, settings: KeySettings,
                    device, chunk: int = 32) -> tuple[torch.Tensor, dict]:
    """Low-res clean plate per frame, T,3,h,w on ``device``."""
    t = int(frames.shape[0])
    key = torch.tensor(info.color, dtype=torch.float32, device=device).view(1, 3, 1, 1)
    plates, cover = [], []
    for s in range(0, t, chunk):
        x = _small(to_nchw(frames[s:s + chunk]).to(device, torch.float32))
        w = _bg_weight(x, info, settings)
        p = push_pull(x, w, key)
        # Second pass relative to the first plate: precise near the subject.
        w = _bg_weight(x, info, settings, gaussian(p, 2.0))
        p = push_pull(x, w, key)
        cover.append(float(w.mean()))
        plates.append(p)
    plate = torch.cat(plates, 0)
    spatial = 2.0 if info.kind == "chroma" else 6.0
    plate = gaussian(plate, spatial)
    sigma_t = 3.0 * float(settings.temporal if settings.plate_temporal is None
                          else settings.plate_temporal)
    if sigma_t > 0.05 and t > 1:
        r = max(1, int(math.ceil(sigma_t * 2)))
        k = torch.exp(-(torch.arange(-r, r + 1, device=device, dtype=torch.float32) ** 2)
                      / (2 * sigma_t * sigma_t))
        k = (k / k.sum()).view(1, 1, -1)
        n, c, h, w_ = plate.shape
        flat = plate.permute(1, 2, 3, 0).reshape(-1, 1, n)
        flat = F.conv1d(F.pad(flat, (r, r), mode="replicate"), k)
        plate = flat.reshape(c, h, w_, n).permute(3, 0, 1, 2)
    if info.kind != "chroma":
        # Glow and smoke must never be absorbed into a black/white plate.
        plate = key + (plate - key).clamp(-0.12, 0.12)
    fix = max(0.0, min(1.0, float(settings.plate_fix)))
    plate = key + (plate - key) * fix
    unevenness = float((plate - key).abs().amax(1).mean())
    return plate.contiguous(), {"backdrop_coverage": sum(cover) / max(1, len(cover)),
                                "plate_unevenness": unevenness}


# ----------------------------------------------------------------------------
# matte
# ----------------------------------------------------------------------------

def raw_alpha(x: torch.Tensor, plate: torch.Tensor, info: BackdropInfo,
              settings: KeySettings) -> torch.Tensor:
    gain = float(settings.screen_gain)
    if info.kind == "chroma":
        bal = float(settings.screen_balance)
        sp = screen(plate, info.channel, bal).clamp_min(0.04)
        sx = screen(x, info.channel, bal)
        a = 1.0 - gain * sx / sp
        if str(settings.shadows).lower() == "remove":
            lx = x.amax(1, keepdim=True)
            lp = plate.amax(1, keepdim=True).clamp_min(0.05)
            ac = 1.0 - gain * (sx / (lx + 0.03)) / (sp / (lp + 0.03))
            a = torch.minimum(a, ac)
    elif info.kind == "black":
        a = gain * (x - plate).clamp_min(0).amax(1, keepdim=True) / (1.0 - plate.amax(1, keepdim=True)).clamp_min(0.2)
    else:
        a = gain * (1.0 - x / plate.clamp_min(0.2)).clamp_min(0).amax(1, keepdim=True)
    return a.clamp(0.0, 1.0)








def despeckle(alpha: torch.Tensor, area: int) -> torch.Tensor:
    if area <= 0:
        return alpha
    r = max(1, int(math.ceil(math.sqrt(area))))
    k = (2 * r + 1) ** 2
    count = box((alpha > 0.02).to(alpha.dtype), r) * k
    peak = max_pool(alpha, r)
    kill = (count < float(area)) & (peak < 0.5)
    return torch.where(kill, torch.zeros_like(alpha), alpha)








def choke(alpha: torch.Tensor, px: float) -> torch.Tensor:
    if abs(px) < 1e-3:
        return alpha
    op = min_pool if px > 0 else max_pool
    lo = int(math.floor(abs(px)))
    frac = abs(px) - lo
    a_lo = op(alpha, lo) if lo > 0 else alpha
    if frac < 1e-3:
        return a_lo
    a_hi = op(alpha, lo + 1)
    return a_lo + (a_hi - a_lo) * frac


def unmix(x, plate, a_solve, info: BackdropInfo, settings: KeySettings):
    f = (x - (1.0 - a_solve) * plate) / a_solve.clamp_min(0.04)
    if info.kind == "chroma" and settings.despill > 0:
        ch = info.channel
        others = [i for i in range(3) if i != ch]
        o1, o2 = f[:, others[0]:others[0] + 1], f[:, others[1]:others[1] + 1]
        bal = float(settings.screen_balance)
        limit = (1.0 - bal) * torch.maximum(o1, o2) + bal * 0.5 * (o1 + o2)
        k = f[:, ch:ch + 1]
        k = k - float(settings.despill) * (k - limit).clamp_min(0)
        f = torch.cat([k if i == ch else f[:, i:i + 1] for i in range(3)], 1)
    return f.clamp(0.0, 1.0)


def extend_edges(f, alpha):
    """Replace colour under near-transparent pixels with nearby solid colour."""
    w = alpha * alpha
    num, den = gaussian(f * w, 3.0), gaussian(w, 3.0)
    num2, den2 = gaussian(f * w, 12.0), gaussian(w, 12.0)
    ext = torch.where(den > 1e-3, num / den.clamp_min(1e-6), num2 / den2.clamp_min(1e-6))
    ext = torch.where(den2 > 1e-5, ext, f)
    t = (1.0 - alpha / 0.25).clamp(0, 1)
    return f * (1.0 - t) + ext.clamp(0, 1) * t


def _mask_to(mask: Optional[torch.Tensor], idx: torch.Tensor, size, device) -> Optional[torch.Tensor]:
    if mask is None:
        return None
    m = mask
    if m.ndim == 2:
        m = m[None]
    if m.ndim == 4:
        m = m[..., 0] if m.shape[-1] in (1, 3, 4) else m[:, 0]
    pick = idx.clamp(max=int(m.shape[0]) - 1)
    m = m[pick.to(m.device)].to(device, torch.float32)[:, None]
    return resize(m, size).clamp(0, 1)


# ----------------------------------------------------------------------------
# sequence driver
# ----------------------------------------------------------------------------

def chroma_detail_ratio(x: torch.Tensor) -> float:
    """High-frequency chroma relative to luma. 4:2:0 video (any MP4/H.264) sits
    far below 0.4; frames straight from a VAE decode sit near or above 1."""
    y = luma(x)
    cb, cr = x[:, 2:3] - y, x[:, 0:1] - y

    def hf(c):
        return (c[..., :, 1:] - c[..., :, :-1]).abs().mean() + (c[..., 1:, :] - c[..., :-1, :]).abs().mean()

    return float((hf(cb) + hf(cr)) / 2 / hf(y).clamp_min(1e-6))


def key_sequence(
    frames: torch.Tensor,
    settings: KeySettings,
    frames_b: Optional[torch.Tensor] = None,
    keep_mask: Optional[torch.Tensor] = None,
    garbage_mask: Optional[torch.Tensor] = None,
    device=None,
    chunk: int = 8,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> tuple[torch.Tensor, dict]:
    """Key a clip. frames: T,H,W,3 in 0..1 (CPU ok). Returns (rgba T,H,W,4 CPU, info)."""
    if frames.ndim != 4 or frames.shape[-1] < 3:
        raise ValueError(f"Expected frames shaped T,H,W,3, got {tuple(frames.shape)}")
    device = device or frames.device
    t, h, w = int(frames.shape[0]), int(frames.shape[1]), int(frames.shape[2])
    s = settings

    info = detect_backdrop(frames, s)
    plates, pstats = estimate_plates(frames, info, s, device)

    two_pass = None
    if frames_b is not None and not HAS_PRO:
        info.warnings.append("Pass B (two-pass triangulation) is a Pro feature; it was ignored.")
    elif frames_b is not None:
        if tuple(frames_b.shape[1:3]) != (h, w):
            info.warnings.append("Pass B has a different size; it was ignored.")
        else:
            tb = min(t, int(frames_b.shape[0]))
            info_b = detect_backdrop(frames_b[:tb], KeySettings(**{**asdict(s), "backdrop": "auto"}))
            dist = max(abs(a - b) for a, b in zip(info.color, info_b.color))
            if dist < 0.3:
                info.warnings.append(
                    "Pass B's backdrop is too close to pass A's to triangulate; it was ignored.")
            else:
                plates_b, _ = estimate_plates(frames_b[:tb], info_b, s, device)
                two_pass = (frames_b, plates_b, tb, info_b)

    probe = to_nchw(frames[: min(t, 4)]).to(device, torch.float32)
    detail_ratio = chroma_detail_ratio(probe)
    del probe

    out = torch.empty((t, h, w, 4), dtype=torch.float32)
    stats = {"solid": 0.0, "soft": 0.0, "clear": 0.0, "haze": 0.0, "holes": 0.0,
             "flicker": 0.0, "mismatch": 0.0}
    halo = 1
    prev_alpha = prev_x = None
    done = 0
    mismatch_n = 0
    for start in range(0, t, chunk):
        end = min(t, start + chunk)
        lo, hi = max(0, start - halo), min(t, end + halo)
        idx = torch.arange(lo, hi)
        x = to_nchw(frames[lo:hi]).to(device, torch.float32).clamp(0, 1)
        p = resize(plates[lo:hi], (h, w))
        a_raw = raw_alpha(x, p, info, s)
        if HAS_PRO and bool(s.edge_solve) and info.kind == "chroma":
            a_raw = pro.edge_solve(x, p, a_raw)

        if two_pass is not None:
            fb, pb_all, tb, _ = two_pass
            sel = [i for i in range(lo, hi) if i < tb]
            if sel:
                xb = to_nchw(fb[sel[0]:sel[-1] + 1]).to(device, torch.float32).clamp(0, 1)
                pb = resize(pb_all[sel[0]:sel[-1] + 1], (h, w))
                n = len(sel)
                a_tri, resid = pro.triangulate(x[:n], xb, p[:n], pb)
                stats["mismatch"] += float(resid[a_tri > 0.05].median()) if bool((a_tri > 0.05).any()) else 0.0
                mismatch_n += 1
                # Trust triangulation where the two passes agree, the key elsewhere.
                trust = (1.0 - (resid - 0.04) / 0.08).clamp(0, 1)
                a_raw = torch.cat([a_tri * trust + a_raw[:n] * (1 - trust), a_raw[n:]], 0)

        # Haze: what the raw key leaves on confident backdrop pixels.
        bgw = resize(_bg_weight(_small(x), info, s, _small(p)), (h, w)) > 0.9
        if bool(bgw.any()):
            stats["haze"] += float(a_raw[bgw].mean()) * (end - start)

        a = pro.temporal_alpha(a_raw, x, float(s.temporal)) if HAS_PRO else a_raw
        if int(s.edge_detail) > 0:
            a = guided_filter_color(x, a, int(s.edge_detail), 1e-3).clamp(0, 1)
        a_solve = a

        rng = max(1e-3, float(s.clip_white) - float(s.clip_black))
        a = ((a - float(s.clip_black)) / rng).clamp(0, 1)
        a = despeckle(a, int(s.despeckle))
        filled = None
        if HAS_PRO:
            a, filled = pro.fill_holes(a, int(s.fill_holes))
        a_fill = a
        km = _mask_to(keep_mask if HAS_PRO else None, idx, (h, w), device)
        if km is not None:
            # Shrunk so a hard segmentation mask (e.g. native Remove Background)
            # only fills holes inside the subject and never hardens soft edges.
            a = torch.maximum(a, min_pool(km, 3))
        gm = _mask_to(garbage_mask if HAS_PRO else None, idx, (h, w), device)
        if gm is not None:
            a = a * gm
        a = choke(a, float(s.choke))
        if float(s.softness) > 0:
            a = gaussian(a, float(s.softness)).clamp(0, 1)

        f = unmix(x, p, a_solve, info, s)
        if filled is not None:
            f = pro.fill_hole_colour(f, a_fill, filled, int(s.fill_holes))
        if bool(s.edge_extend):
            f = extend_edges(f, a)

        keep = slice(start - lo, start - lo + (end - start))
        a_k, f_k = a[keep], f[keep]
        out[start:end, ..., :3] = f_k.permute(0, 2, 3, 1).cpu()
        out[start:end, ..., 3] = a_k[:, 0].cpu()

        n = end - start
        stats["solid"] += float((a_k > 0.99).float().mean()) * n
        stats["clear"] += float((a_k < 0.01).float().mean()) * n
        solid_near = box((a_k > 0.95).to(a_k.dtype), 4) > 0.85
        stats["holes"] += float((solid_near & (a_k < 0.8)).float().mean()) * n
        x_k = x[keep]
        if prev_alpha is not None:
            a_seq, x_seq = torch.cat([prev_alpha[None], a_k], 0), torch.cat([prev_x[None], x_k], 0)
        else:
            a_seq, x_seq = a_k, x_k
        if a_seq.shape[0] > 1:
            still = (x_seq[1:] - x_seq[:-1]).abs().amax(1, keepdim=True) < 0.03
            da = (a_seq[1:] - a_seq[:-1]).abs()
            stats["flicker"] += float((da * still).sum() / still.sum().clamp_min(1)) * (a_seq.shape[0] - 1)
        prev_alpha, prev_x = a_k[-1], x_k[-1]
        done = end
        if on_progress:
            on_progress(done, t)

    for k in ("solid", "clear", "haze", "holes"):
        stats[k] /= max(1, t)
    stats["flicker"] /= max(1, t - 1)
    stats["soft"] = max(0.0, 1.0 - stats["solid"] - stats["clear"])
    stats["mismatch"] = stats["mismatch"] / mismatch_n if mismatch_n else None
    stats.update(pstats)
    stats["chroma_detail"] = detail_ratio
    result = {"backdrop": info.as_dict(), "stats": stats, "frames": t, "width": w, "height": h,
              "two_pass": two_pass is not None, "warnings": list(info.warnings)}
    result["warnings"] += advise(info, stats, s)
    return out, result


def advise(info: BackdropInfo, stats: dict, s: KeySettings) -> list:
    tips = []
    if stats.get("chroma_detail", 1.0) < 0.4:
        tips.append(
            "The input looks like compressed MP4/H.264 (4:2:0 chroma). Edges and smoke are fine, "
            "but detail finer than 2 px (hair strands, sparks) loses opacity. For the cleanest "
            "matte feed frames straight from VAE Decode instead of a saved MP4.")
    if stats["haze"] > max(0.02, float(s.clip_black)):
        tips.append(
            f"Faint haze of {stats['haze']:.3f} remains on the backdrop; raise Clip black to "
            f"about {min(0.3, stats['haze'] * 1.5):.2f} or raise Plate fix.")
    if stats["holes"] > 0.002 and not HAS_PRO:
        tips.append(
            "Semi-transparent holes inside the subject: it contains colours close to the backdrop "
            "(yellow fire on green, for example). Lower Clip white, or regenerate over a backdrop the "
            "subject does not contain (black for fire and glow, blue instead of green). "
            "Fill holes and keep_mask are Pro features.")
    elif stats["holes"] > 0.002:
        if int(s.fill_holes) <= 0:
            tips.append(
                "Semi-transparent holes inside the subject: it contains colours close to the backdrop "
                "(yellow fire on green, for example). Raise Fill holes to 3-6 px, or lower Clip white, "
                "connect a keep_mask, or regenerate over a backdrop the subject does not contain "
                "(black for fire and glow, blue instead of green).")
        else:
            tips.append(
                "Holes remain inside the subject after Fill holes: they are larger than the fill "
                "radius. Raise Fill holes, lower Clip white, or connect a keep_mask.")
    if stats["mismatch"] is not None and stats["mismatch"] > 0.06:
        tips.append(
            f"The two passes disagree (median residual {stats['mismatch']:.3f}), so the "
            "triangulated alpha was only trusted where they match. The single-pass key filled in.")
    if stats["flicker"] > 0.01:
        tips.append("Matte flicker is noticeable; raise Temporal smoothing."
                    if HAS_PRO else "Matte flicker is noticeable (Temporal smoothing is a Pro feature).")
    return tips
