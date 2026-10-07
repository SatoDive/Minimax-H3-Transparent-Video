"""Writers for transparent video. PyAV only (ComfyUI already ships it), no ffmpeg binary.

Every alpha file is read back after writing and checked for a real alpha
channel: some encoders silently fall back to an opaque format, and that is
otherwise only discovered once the clip is already in a timeline.
"""

from __future__ import annotations

import json
import os
from fractions import Fraction
from typing import Optional

import numpy as np
import torch

FORMATS = {
    "ProRes 4444 (.mov) - Premiere/AE/Resolve": "prores",
    "ProRes 4444 + PNG sequence": "prores+png",
    "PNG sequence (RGBA)": "png",
    "WebM VP9 alpha (web)": "webm",
    "QuickTime Animation (.mov, lossless)": "qtrle",
    "Don't save (preview only)": "none",
}


def _rate(fps: float) -> Fraction:
    return Fraction(float(fps)).limit_denominator(1001)


def _open(path: str, metadata: Optional[dict]):
    import av
    opts = {}
    if path.lower().endswith((".mov", ".mp4")):
        opts = {"movflags": "use_metadata_tags+faststart"}
    ct = av.open(path, "w", options=opts)
    for k, v in (metadata or {}).items():
        ct.metadata[k] = v if isinstance(v, str) else json.dumps(v)
    return ct


def _audio_stream(ct, audio, codec: str):
    """Add an audio stream; returns (stream, frames) or (None, None)."""
    if not isinstance(audio, dict) or not isinstance(audio.get("waveform"), torch.Tensor):
        return None, None
    import av
    wave = audio["waveform"].detach().float().cpu()
    if wave.ndim == 3:
        wave = wave[0]
    rate = int(audio.get("sample_rate") or 48000)
    ch = int(wave.shape[0])
    if ch < 1 or wave.shape[1] < 1:
        return None, None
    wave = wave[:2] if ch > 2 else wave
    layout = "stereo" if wave.shape[0] == 2 else "mono"
    if codec == "libopus" and rate not in (8000, 12000, 16000, 24000, 48000):
        out_rate = 48000
    else:
        out_rate = rate
    st = ct.add_stream(codec, rate=out_rate, layout=layout)
    src = av.AudioFrame.from_ndarray(wave.contiguous().numpy().astype(np.float32), format="fltp",
                                     layout=layout)
    src.sample_rate = rate
    frames = []
    res = av.AudioResampler(format=st.codec_context.format.name, layout=layout, rate=out_rate,
                            frame_size=st.codec_context.frame_size or None)
    frames += res.resample(src)
    frames += res.resample(None)
    return st, frames


def _finish_audio(ct, st, frames):
    if st is None:
        return
    for f in frames:
        for p in st.encode(f):
            ct.mux(p)
    for p in st.encode():
        ct.mux(p)


def _rgba_frames(rgba: torch.Tensor, premultiply: bool, bits: int):
    scale = 65535.0 if bits == 16 else 255.0
    dtype = torch.int32
    for i in range(int(rgba.shape[0])):
        f = rgba[i].float().clamp(0, 1)
        if premultiply:
            f = torch.cat([f[..., :3] * f[..., 3:4], f[..., 3:4]], -1)
        arr = (f * scale).round().to(dtype).numpy()
        yield arr.astype(np.uint16 if bits == 16 else np.uint8)


def _even(rgba: torch.Tensor) -> torch.Tensor:
    h, w = int(rgba.shape[1]), int(rgba.shape[2])
    return rgba[:, : h - (h % 2), : w - (w % 2)]


def write_video(path: str, kind: str, rgba: torch.Tensor, fps: float, audio=None,
                metadata: Optional[dict] = None, premultiply: bool = False, progress=None) -> str:
    import av
    rgba = _even(rgba)
    t, h, w = int(rgba.shape[0]), int(rgba.shape[1]), int(rgba.shape[2])
    ct = _open(path, metadata)
    try:
        if kind == "prores":
            st = ct.add_stream("prores_ks", rate=_rate(fps))
            st.pix_fmt = "yuva444p10le"
            st.options = {"profile": "4444", "vendor": "apl0", "alpha_bits": "16"}
            fmt, bits, acodec = "rgba64le", 16, "pcm_s16le"
        elif kind == "qtrle":
            st = ct.add_stream("qtrle", rate=_rate(fps))
            st.pix_fmt = "argb"
            fmt, bits, acodec = "rgba", 8, "pcm_s16le"
        elif kind == "webm":
            st = ct.add_stream("libvpx-vp9", rate=_rate(fps))
            st.pix_fmt = "yuva420p"
            st.options = {"crf": "18", "b": "0", "auto-alt-ref": "0", "row-mt": "1",
                          "deadline": "good", "cpu-used": "2"}
            fmt, bits, acodec = "rgba", 8, "libopus"
        else:
            raise ValueError(f"unknown alpha format {kind}")
        st.width, st.height = w, h
        st.time_base = Fraction(1, 1) / _rate(fps)
        a_st, a_frames = _audio_stream(ct, audio, acodec)
        for i, arr in enumerate(_rgba_frames(rgba, premultiply, bits)):
            frame = av.VideoFrame.from_ndarray(arr, format=fmt)
            frame.pts = i
            for p in st.encode(frame):
                ct.mux(p)
            if progress:
                progress(i + 1, t)
        for p in st.encode():
            ct.mux(p)
        _finish_audio(ct, a_st, a_frames)
    finally:
        ct.close()
    verify_alpha(path)
    return path


def verify_alpha(path: str) -> None:
    import av
    with av.open(path) as ct:
        st = ct.streams.video[0]
        pix = str(st.codec_context.pix_fmt or "")
        meta = {k.lower(): str(v) for k, v in dict(st.metadata).items()}
    if any(tag in pix for tag in ("yuva", "argb", "rgba", "bgra", "gbra")) or meta.get("alpha_mode") == "1":
        return
    try:
        os.remove(path)
    except OSError:
        pass
    raise RuntimeError(f"{os.path.basename(path)} was encoded without alpha ({pix}); it was deleted.")


def write_png_sequence(folder: str, stem: str, rgba: torch.Tensor, metadata: Optional[dict] = None,
                       premultiply: bool = False, progress=None) -> list:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    os.makedirs(folder, exist_ok=True)
    info = None
    if metadata:
        info = PngInfo()
        for k, v in metadata.items():
            info.add_text(k, v if isinstance(v, str) else json.dumps(v), zip=True)
    files = []
    t = int(rgba.shape[0])
    for i, arr in enumerate(_rgba_frames(rgba, premultiply, 8)):
        name = f"{stem}_{i:05d}.png"
        Image.fromarray(arr, mode="RGBA").save(os.path.join(folder, name), pnginfo=info, compress_level=4)
        files.append(name)
        if progress:
            progress(i + 1, t)
    return files


def write_preview_mp4(path: str, rgb: torch.Tensor, fps: float, audio=None,
                      metadata: Optional[dict] = None) -> str:
    """Small H.264 file for the in-node player (not for editing: no alpha)."""
    import av
    rgb = _even(rgb)
    t, h, w = int(rgb.shape[0]), int(rgb.shape[1]), int(rgb.shape[2])
    ct = _open(path, metadata)
    try:
        st = ct.add_stream("libx264", rate=_rate(fps))
        st.width, st.height, st.pix_fmt = w, h, "yuv420p"
        st.options = {"crf": "20", "preset": "veryfast"}
        a_st, a_frames = _audio_stream(ct, audio, "aac")
        for i in range(t):
            arr = (rgb[i, ..., :3].float().clamp(0, 1) * 255).round().to(torch.uint8).numpy()
            frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
            frame.pts = i
            for p in st.encode(frame):
                ct.mux(p)
        for p in st.encode():
            ct.mux(p)
        _finish_audio(ct, a_st, a_frames)
    finally:
        ct.close()
    return path
