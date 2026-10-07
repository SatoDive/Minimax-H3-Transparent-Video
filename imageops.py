"""Small tensor image ops shared by the keyer (tensors are N,C,H,W). Pure torch."""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F

LUMA = (0.2126, 0.7152, 0.0722)


def to_nchw(x: torch.Tensor) -> torch.Tensor:
    return x[..., :3].permute(0, 3, 1, 2)


def luma(x: torch.Tensor) -> torch.Tensor:
    w = torch.tensor(LUMA, dtype=x.dtype, device=x.device).view(1, 3, 1, 1)
    return (x * w).sum(1, keepdim=True)


def box(x: torch.Tensor, r: int) -> torch.Tensor:
    if r <= 0:
        return x
    k = 2 * r + 1
    # Cumulative sums keep this O(1) in r, which matters on CPU.
    p = F.pad(x, (r + 1, r, r + 1, r), mode="replicate")
    c = p.cumsum(-1).cumsum(-2)
    s = c[..., k:, k:] - c[..., :-k, k:] - c[..., k:, :-k] + c[..., :-k, :-k]
    return s / float(k * k)


def gaussian(x: torch.Tensor, sigma: float) -> torch.Tensor:
    if sigma <= 0.05:
        return x
    r = max(1, int(math.ceil(sigma * 3.0)))
    t = torch.arange(-r, r + 1, dtype=x.dtype, device=x.device)
    k = torch.exp(-(t * t) / (2.0 * sigma * sigma))
    k = k / k.sum()
    c = x.shape[1]
    kh = k.view(1, 1, 1, -1).repeat(c, 1, 1, 1)
    kv = k.view(1, 1, -1, 1).repeat(c, 1, 1, 1)
    y = F.conv2d(F.pad(x, (r, r, 0, 0), mode="replicate"), kh, groups=c)
    return F.conv2d(F.pad(y, (0, 0, r, r), mode="replicate"), kv, groups=c)


def max_pool(x: torch.Tensor, r: int) -> torch.Tensor:
    if r <= 0:
        return x
    return F.max_pool2d(F.pad(x, (r, r, r, r), mode="replicate"), 2 * r + 1, stride=1)


def min_pool(x: torch.Tensor, r: int) -> torch.Tensor:
    return -max_pool(-x, r)


def resize(x: torch.Tensor, size, mode="bilinear") -> torch.Tensor:
    if tuple(x.shape[-2:]) == tuple(size):
        return x
    if mode == "area":
        return F.interpolate(x, size=size, mode="area")
    return F.interpolate(x, size=size, mode=mode, align_corners=False)


def guided_filter_color(guide: torch.Tensor, p: torch.Tensor, r: int, eps: float) -> torch.Tensor:
    """He et al. guided filter with an RGB guide. guide N,3,H,W; p N,1,H,W."""
    if r <= 0:
        return p
    mI = box(guide, r)
    mp = box(p, r)
    mIp = box(guide * p, r)
    cov = mIp - mI * mp                                   # N,3,H,W
    r_, g_, b_ = guide[:, 0:1], guide[:, 1:2], guide[:, 2:3]
    vrr = box(r_ * r_, r) - mI[:, 0:1] ** 2 + eps
    vrg = box(r_ * g_, r) - mI[:, 0:1] * mI[:, 1:2]
    vrb = box(r_ * b_, r) - mI[:, 0:1] * mI[:, 2:3]
    vgg = box(g_ * g_, r) - mI[:, 1:2] ** 2 + eps
    vgb = box(g_ * b_, r) - mI[:, 1:2] * mI[:, 2:3]
    vbb = box(b_ * b_, r) - mI[:, 2:3] ** 2 + eps
    # Inverse of the symmetric 3x3 covariance via its adjugate.
    i_rr = vgg * vbb - vgb * vgb
    i_rg = vgb * vrb - vrg * vbb
    i_rb = vrg * vgb - vgg * vrb
    i_gg = vrr * vbb - vrb * vrb
    i_gb = vrb * vrg - vrr * vgb
    i_bb = vrr * vgg - vrg * vrg
    det = vrr * i_rr + vrg * i_rg + vrb * i_rb
    det = torch.where(det.abs() < 1e-12, torch.full_like(det, 1e-12), det)
    cr, cg, cb = cov[:, 0:1], cov[:, 1:2], cov[:, 2:3]
    a_r = (i_rr * cr + i_rg * cg + i_rb * cb) / det
    a_g = (i_rg * cr + i_gg * cg + i_gb * cb) / det
    a_b = (i_rb * cr + i_gb * cg + i_bb * cb) / det
    b = mp - a_r * mI[:, 0:1] - a_g * mI[:, 1:2] - a_b * mI[:, 2:3]
    return (box(a_r, r) * r_ + box(a_g, r) * g_ + box(a_b, r) * b_ + box(b, r))


def push_pull(color: torch.Tensor, weight: torch.Tensor, fallback: torch.Tensor) -> torch.Tensor:
    """Fill low-weight areas from their surroundings (Gortler push-pull)."""
    h, w = color.shape[-2:]
    weight = weight.clamp(0.0, 1.0)
    if min(h, w) <= 2:
        tot = weight.sum((2, 3), keepdim=True)
        mean = (color * weight).sum((2, 3), keepdim=True) / tot.clamp_min(1e-6)
        mean = torch.where(tot > 1e-3, mean, fallback.expand_as(mean))
        return color * weight + mean * (1.0 - weight)
    size = ((h + 1) // 2, (w + 1) // 2)
    wd = resize(weight, size, "area")
    cd = resize(color * weight, size, "area") / wd.clamp_min(1e-6)
    coarse = push_pull(cd, (wd * 2.0).clamp(max=1.0), fallback)
    up = resize(coarse, (h, w))
    return color * weight + up * (1.0 - weight)
