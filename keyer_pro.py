"""Pro keying stages: edge solve, two-pass triangulation, temporal matte smoothing, hole filling.

This module ships only in the Patreon (Pro) edition. The free edition runs without it.
"""

from __future__ import annotations

import math
from typing import Optional

import torch
import torch.nn.functional as F

try:
    from .imageops import box, gaussian, max_pool, min_pool, push_pull, resize
except ImportError:  # imported standalone (tests)
    from imageops import box, gaussian, max_pool, min_pool, push_pull, resize


def edge_solve(x: torch.Tensor, plate: torch.Tensor, a_cd: torch.Tensor, rtol: float = 0.08,
               sigma: float = 12.0, ds: int = 2, erode: int = 3, iters: int = 3) -> torch.Tensor:
    """Fix colour-difference alpha on blends of strongly coloured subjects.

    The screen formula assumes the subject has no key-channel excess. A
    saturated red car has a large *negative* excess, so a 50% motion-blurred
    edge already reads as 100% and the blur turns into a hard, olive fringe.

    Here the local subject colour F is sampled from solid pixels a few pixels
    inside the subject and spread outward, and alpha is solved by projecting
    each pixel onto the plate->F colour line. Solid is re-derived from the
    corrected alpha and the solve repeated, so the estimate walks out along the
    blur. It is only trusted where the pixel really lies on that line (small
    residual), so smoke, glass, or anything whose colour is not known nearby
    keeps the colour-difference answer.
    """
    h, w_ = x.shape[-2:]
    sz = (max(4, h // ds), max(4, w_ // ds))
    xs = resize(x, sz, "area")
    gate = ((a_cd - 0.01) / 0.04).clamp(0, 1)
    a = a_cd
    for _ in range(max(1, int(iters))):
        solid = min_pool((a > 0.97).to(x.dtype), erode)
        ss = (resize(solid, sz, "area") > 0.99).to(x.dtype)
        if float(ss.amax()) <= 0:
            return a
        fill = resize(gaussian(push_pull(xs, ss, xs.mean((2, 3), keepdim=True)), 1.0), (h, w_))
        sg = sigma / ds
        den_s = gaussian(ss, sg)
        near = resize(gaussian(xs * ss, sg) / den_s.clamp_min(1e-4), (h, w_))
        conf = (resize(den_s, (h, w_)) / 0.1).clamp(0, 1)
        fhat = near * conf + fill * (1 - conf)
        d = fhat - plate
        dd = (d * d).sum(1, keepdim=True)
        ap = (((x - plate) * d).sum(1, keepdim=True) / dd.clamp_min(1e-4)).clamp(0, 1)
        resid = (x - (plate + ap * d)).abs().amax(1, keepdim=True)
        sep = ((dd.sqrt() - 0.1) / 0.15).clamp(0, 1)
        wgt = torch.exp(-(resid / rtol) ** 2) * sep * (1 - min_pool(solid, 1)) * gate
        a = a_cd * (1 - wgt) + ap * wgt
    return a


def triangulate(xa, xb, pa, pb):
    """Exact alpha from two passes over different known plates."""
    d = pa - pb
    den = (d * d).sum(1, keepdim=True).clamp_min(1e-4)
    a = 1.0 - ((xa - xb) * d).sum(1, keepdim=True) / den
    a = a.clamp(0.0, 1.0)
    resid = ((xa - xb) - (1.0 - a) * d).abs().amax(1, keepdim=True)
    return a, resid


def temporal_alpha(alpha: torch.Tensor, frames: torch.Tensor, strength: float) -> torch.Tensor:
    """Motion-gated smoothing over t-1, t, t+1 (alpha/frames include a 1-frame halo)."""
    if strength <= 0.0 or alpha.shape[0] < 2:
        return alpha
    diff = box((frames[1:] - frames[:-1]).abs().mean(1, keepdim=True), 1)
    w = torch.exp(-(diff / 0.035) ** 2) * float(strength)          # between t and t+1
    zero = torch.zeros_like(w[:1])
    w_prev = torch.cat([zero, w], 0)
    w_next = torch.cat([w, zero], 0)
    a_prev = torch.cat([alpha[:1], alpha[:-1]], 0)
    a_next = torch.cat([alpha[1:], alpha[-1:]], 0)
    return (alpha + w_prev * a_prev + w_next * a_next) / (1.0 + w_prev + w_next)


def _reach(solid: torch.Tensor, d: int) -> torch.Tensor:
    """1 where solid exists within ``d`` px on all four sides (left, right, above, below)."""
    h, w = solid.shape[-2:]
    left = F.max_pool2d(F.pad(solid, (d, 0, 0, 0)), (1, d), stride=1)[..., :, :w]
    right = F.max_pool2d(F.pad(solid, (0, d, 0, 0)), (1, d), stride=1)[..., :, 1:]
    up = F.max_pool2d(F.pad(solid, (0, 0, d, 0)), (d, 1), stride=1)[..., :h, :]
    down = F.max_pool2d(F.pad(solid, (0, 0, 0, d)), (d, 1), stride=1)[..., 1:, :]
    return left * right * up * down


def fill_holes(alpha: torch.Tensor, r: int) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
    """Close small holes that are enclosed by solid matte.

    A morphological closing fills every dip up to ``2r+1`` px, but on its own it also merges
    sparks and bridges thin gaps between objects. So it is only applied to pixels that have
    solid matte on all four sides within ``r+2`` px, i.e. real pinholes. Open notches, gaps
    between separate shapes and holes larger than ``r`` are left alone.

    Returns (alpha, filled) where ``filled`` is how much alpha was added (None when off).
    """
    r = int(r)
    if r <= 0:
        return alpha, None
    closed = min_pool(max_pool(alpha, r), r)
    enclosed = _reach((alpha > 0.95).to(alpha.dtype), r + 2)
    out = alpha + (closed - alpha).clamp_min(0.0) * enclosed
    return out, out - alpha


def fill_hole_colour(f: torch.Tensor, alpha: torch.Tensor, filled: Optional[torch.Tensor],
                     r: int) -> torch.Tensor:
    """Colour for filled pixels comes from the nearby solid subject, not from the un-mix.

    The un-mix divides by the original (low) alpha, so a pinhole would come back dark or
    green even though its matte is now solid.
    """
    if filled is None:
        return f
    solid = ((alpha > 0.95) & (filled < 0.02)).to(f.dtype)
    sigma = max(1.5, 0.75 * float(r))
    num, den = gaussian(f * solid, sigma), gaussian(solid, sigma)
    near = num / den.clamp_min(1e-4)
    t = (filled / 0.08).clamp(0.0, 1.0) * (den > 1e-3).to(f.dtype)
    return f * (1.0 - t) + near.clamp(0.0, 1.0) * t
