"""H3 Transparent Video: one node from generated frames to a transparent video file."""

from __future__ import annotations

import json
import os
import re
import time

import torch

import folder_paths

try:
    from . import edition, writer
    from .keyer import KeySettings, key_sequence
except ImportError:  # imported standalone (tests)
    import edition
    import writer
    from keyer import KeySettings, key_sequence

LOG = "[H3 Transparent Video]"
OUTPUT_ROOT = "H3_Transparent_Video"

BACKDROP_CHOICES = {
    "Auto": "auto",
    "Green screen": "green",
    "Blue screen": "blue",
    "Black (fire / glow / sparks)": "black",
    "White (smoke / ink / dust)": "white",
    "Custom colour": "custom",
}
PREVIEW_CHOICES = ["Checkerboard", "Grey", "Black", "White", "Plate input"]
ALPHA_CHOICES = ["Straight (recommended)", "Premultiplied"]


PRO_TAG = "" if edition.IS_PRO else "[Pro feature - ignored in the Free edition] "


def _trim_audio(audio, seconds: float):
    """Cut an AUDIO dict to ``seconds`` (used when the Free edition caps the clip length)."""
    try:
        wave, sr = audio["waveform"], int(audio["sample_rate"])
        return {**audio, "waveform": wave[..., : max(1, int(seconds * sr))]}
    except Exception:
        return audio


def _send(event: str, data: dict) -> None:
    try:
        from server import PromptServer
        PromptServer.instance.send_sync(event, data)
    except Exception:
        pass


def _device():
    try:
        import comfy.model_management as mm
        return mm.get_torch_device()
    except Exception:
        return torch.device("cpu")


def _clean_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(name or "").strip()).strip("_") or "h3_transparent"


def _project_folder(stem: str) -> tuple[str, str]:
    root = os.path.join(folder_paths.get_output_directory(), OUTPUT_ROOT)
    os.makedirs(root, exist_ok=True)
    index = 1
    pattern = re.compile(rf"^{re.escape(stem)}_(\d+)$")
    for entry in os.listdir(root):
        m = pattern.match(entry)
        if m:
            index = max(index, int(m.group(1)) + 1)
    rel = f"{stem}_{index:03d}"
    path = os.path.join(root, rel)
    os.makedirs(path, exist_ok=True)
    return path, f"{OUTPUT_ROOT}/{rel}"


def _metadata(prompt, extra_pnginfo) -> dict:
    try:
        from comfy.cli_args import args
        if args.disable_metadata:
            return {}
    except Exception:
        pass
    meta = {}
    if prompt is not None:
        meta["prompt"] = json.dumps(prompt)
    if isinstance(extra_pnginfo, dict):
        for k, v in extra_pnginfo.items():
            meta[k] = json.dumps(v)
    return meta


def _video_parts(video):
    """Images, audio and fps from a ComfyUI VIDEO, tolerating API differences."""
    comps = video.get_components() if hasattr(video, "get_components") else video
    images = getattr(comps, "images", None)
    audio = getattr(comps, "audio", None)
    rate = getattr(comps, "frame_rate", None)
    try:
        rate = float(rate) if rate is not None else None
    except Exception:
        rate = None
    return images, audio, rate


def _backdrop_plate(kind: str, h: int, w: int, plate=None, index: int = 0) -> torch.Tensor:
    if kind == "Plate input" and isinstance(plate, torch.Tensor):
        frame = plate[min(index, int(plate.shape[0]) - 1), ..., :3].float()
        if tuple(frame.shape[:2]) != (h, w):
            frame = torch.nn.functional.interpolate(
                frame.permute(2, 0, 1)[None], size=(h, w), mode="bilinear", align_corners=False
            )[0].permute(1, 2, 0)
        return frame
    if kind == "Grey":
        return torch.full((h, w, 3), 0.5)
    if kind == "Black":
        return torch.zeros((h, w, 3))
    if kind == "White":
        return torch.ones((h, w, 3))
    cell = max(8, min(h, w) // 24)
    yy = torch.arange(h)[:, None] // cell
    xx = torch.arange(w)[None, :] // cell
    c = (((yy + xx) % 2).float() * 0.18 + 0.32)[..., None]
    return c.expand(h, w, 3)


def composite_preview(rgba: torch.Tensor, kind: str, plate=None) -> torch.Tensor:
    t, h, w = int(rgba.shape[0]), int(rgba.shape[1]), int(rgba.shape[2])
    out = torch.empty((t, h, w, 3), dtype=torch.float32)
    static = None if (kind == "Plate input" and isinstance(plate, torch.Tensor)) else _backdrop_plate(kind, h, w)
    for i in range(t):
        bg = static if static is not None else _backdrop_plate(kind, h, w, plate, i)
        a = rgba[i, ..., 3:4]
        out[i] = rgba[i, ..., :3] * a + bg * (1.0 - a)
    return out


def _thumbs(source, rgba, preview, uid) -> list:
    """A few small frames per view for the in-node viewer (temp folder)."""
    from PIL import Image
    tmp = folder_paths.get_temp_directory()
    sub = "h3tv"
    os.makedirs(os.path.join(tmp, sub), exist_ok=True)
    t = int(rgba.shape[0])
    picks = sorted({int(round(i * (t - 1) / 5)) for i in range(6)}) if t > 1 else [0]
    stamp = int(time.time() * 1000) % 10_000_000
    out = []
    for i in picks:
        views = {
            "source": source[i, ..., :3],
            "matte": rgba[i, ..., 3:4].expand(-1, -1, 3),
            "composite": preview[i],
        }
        entry = {"frame": i}
        for view, img in views.items():
            arr = (img.float().clamp(0, 1) * 255).round().to(torch.uint8).numpy()
            im = Image.fromarray(arr, mode="RGB")
            im.thumbnail((640, 640))
            name = f"{_clean_name(str(uid))}_{stamp}_{i:05d}_{view}.jpg"
            im.save(os.path.join(tmp, sub, name), quality=88)
            entry[view] = {"filename": name, "subfolder": sub, "type": "temp"}
        out.append(entry)
    return out


def format_report(info: dict, saved: list, folder_rel: str, elapsed: float) -> str:
    b, s = info["backdrop"], info["stats"]
    lines = [
        f"{info['frames']} frames, {info['width']}x{info['height']}  ({elapsed:.1f}s)",
        f"Backdrop: {b['kind']} {b['hex']}  ({b['source']}, border match {b['confidence'] * 100:.0f}%)"
        + ("  + pass B (triangulated)" if info.get("two_pass") else ""),
        f"Matte:    solid {s['solid'] * 100:.1f}%   soft {s['soft'] * 100:.1f}%   clear {s['clear'] * 100:.1f}%",
        f"Quality:  haze {s['haze']:.4f}   flicker {s['flicker']:.4f}   plate unevenness {s['plate_unevenness']:.3f}",
    ]
    if saved:
        lines.append(f"Saved to output/{folder_rel}:")
        lines += [f"  {x}" for x in saved]
    for w in info.get("warnings", []):
        lines.append(f"! {w}")
    if not info.get("warnings"):
        lines.append("No issues found.")
    return "\n".join(lines)


def _as_int(v, default=0):
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return default


class H3TransparentVideo:
    """Key a generated clip into a transparent video, in one node."""

    CATEGORY = "SatoDive/H3 Transparent Video"
    FUNCTION = "run"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("foreground", "alpha", "rgba", "preview", "report")
    DESCRIPTION = (
        "Turns an H3 clip generated over a backdrop (green, blue, black or white) into a "
        "transparent video. The backdrop is modelled per pixel and per frame, so gradients and "
        "vignettes from the generation do not leave haze; edges, smoke and motion blur keep "
        "real semi-transparency. Saves ProRes 4444 (.mov) and/or an RGBA PNG sequence."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "backdrop": (list(BACKDROP_CHOICES), {"default": "Auto", "tooltip":
                    "What the clip was generated on. Auto reads it from the frame border."}),
                "custom_color": ("STRING", {"default": "#00B140", "tooltip": PRO_TAG +
                    "Only for 'Custom colour': the backdrop colour as hex."}),
                "screen_gain": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.01, "tooltip":
                    "How strongly the backdrop is removed. Raise if a faint veil remains, lower if "
                    "thin or soft parts disappear."}),
                "screen_balance": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip":
                    "0 compares the key channel with the strongest other channel (protects yellows "
                    "and cyans). Raise toward 1 for softer, more transparent edges."}),
                "shadows": (["Keep", "Remove"], {"default": "Keep", "tooltip":
                    "Shadows on a green/blue backdrop: Keep exports them as soft dark alpha, Remove "
                    "drops them (slightly thins very dark edges)."}),
                "plate_fix": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip":
                    "Compensate an uneven backdrop (gradients, vignette). 1 = full per-pixel plate."}),
                "clip_black": ("FLOAT", {"default": 0.03, "min": 0.0, "max": 0.5, "step": 0.005, "tooltip":
                    "Alpha below this becomes fully clear. Removes leftover haze."}),
                "clip_white": ("FLOAT", {"default": 0.95, "min": 0.5, "max": 1.0, "step": 0.005, "tooltip":
                    "Alpha above this becomes fully solid. Fills faint holes in the subject."}),
                "edge_solve": ("BOOLEAN", {"default": edition.IS_PRO, "tooltip": PRO_TAG +
                    "Solve motion-blurred and anti-aliased edges of strongly coloured subjects (red car, "
                    "orange fire) from the local subject colour. Without it such edges come out too hard "
                    "with a dark fringe."}),
                "edge_detail": ("INT", {"default": 2, "min": 0, "max": 8, "tooltip":
                    "Edge-aware refinement radius in pixels: snaps the matte to image edges. 0 = off."}),
                "choke": ("FLOAT", {"default": 0.0, "min": -4.0, "max": 4.0, "step": 0.25, "tooltip":
                    "Shrink (+) or grow (-) the matte, in pixels."}),
                "softness": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 4.0, "step": 0.25, "tooltip":
                    "Blur the final matte edge, in pixels."}),
                "despill": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip":
                    "Remove backdrop colour reflected onto the subject (green/blue spill)."}),
                "edge_extend": ("BOOLEAN", {"default": True, "tooltip":
                    "Fill colour under near-transparent pixels from the subject, so edges never "
                    "show a dark or coloured fringe after compositing or scaling."}),
                "despeckle": ("INT", {"default": 8, "min": 0, "max": 200, "tooltip":
                    "Remove isolated faint specks up to this area in pixels. Strong sparks are kept."}),
                "temporal": ("FLOAT", {"default": 0.5 if edition.IS_PRO else 0.0, "min": 0.0, "max": 1.0, "step": 0.05,
                                      "tooltip": PRO_TAG + "Smooth matte flicker across frames. Motion-aware, so moving edges do not ghost."}),
                "output_format": (list(writer.FORMATS), {"default": "ProRes 4444 (.mov) - Premiere/AE/Resolve",
                    "tooltip": "ProRes 4444 carries real alpha in Premiere, After Effects, Resolve and "
                               "Final Cut. MP4/H.264 can never be transparent."}),
                "filename": ("STRING", {"default": "h3_transparent", "tooltip":
                    "Project folder name under output/H3_Transparent_Video. Each run gets a new numbered folder."}),
                "fps": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 120.0, "step": 0.001, "tooltip":
                    "0 = take it from the video input, or 24 (H3) for images."}),
                "alpha_type": (ALPHA_CHOICES, {"default": ALPHA_CHOICES[0], "tooltip":
                    "Straight is what editors expect for ProRes 4444 and PNG."}),
                "preview_on": (PREVIEW_CHOICES, {"default": "Checkerboard", "tooltip":
                    "Background for the preview output and the in-node player."}),
                "preview_video": ("BOOLEAN", {"default": True, "tooltip":
                    "Also write small preview/matte MP4s for the player inside the node."}),
                # Last widget on purpose: keeps widgets_values of existing workflows aligned.
                "fill_holes": ("INT", {"default": 0, "min": 0, "max": 16, "tooltip": PRO_TAG +
                    "Fill pinholes enclosed by the subject, up to about this radius in pixels. Fixes "
                    "black specks in yellow fire keyed from green. 0 = off, 3-6 is typical. Open notches "
                    "and gaps between separate shapes are never filled."}),
            },
            "optional": {
                "images": ("IMAGE", {"tooltip": "Frames straight from VAE Decode (best quality)."}),
                "video": ("VIDEO", {"tooltip": "Or a loaded video; its audio and fps are used."}),
                "audio": ("AUDIO", {"tooltip": "Muxed into the saved file."}),
                "keep_mask": ("MASK", {"tooltip": PRO_TAG + "Optional: areas that must be solid (from any "
                                                  "segmentation node)."}),
                "garbage_mask": ("MASK", {"tooltip": PRO_TAG + "Optional: white where the subject may be; "
                                                     "everything black is forced clear."}),
                "pass_b": ("IMAGE", {"tooltip": PRO_TAG + "Advanced: the same shot over a second backdrop. Used "
                                                "for exact triangulation only where both passes agree."}),
                "preview_plate": ("IMAGE", {"tooltip": "Optional background for 'Plate input' preview."}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO", "unique_id": "UNIQUE_ID"},
        }

    def run(self, backdrop="Auto", custom_color="#00B140", screen_gain=1.0, screen_balance=0.0,
            shadows="Keep", plate_fix=1.0, clip_black=0.03, clip_white=0.95, edge_solve=edition.IS_PRO, edge_detail=2,
            choke=0.0, softness=0.0, despill=1.0, edge_extend=True, despeckle=8, temporal=0.5 if edition.IS_PRO else 0.0,
            output_format="ProRes 4444 (.mov) - Premiere/AE/Resolve", filename="h3_transparent", fps=0.0,
            alpha_type="Straight (recommended)", preview_on="Checkerboard", preview_video=True,
            fill_holes=0, images=None, video=None, audio=None, keep_mask=None, garbage_mask=None, pass_b=None,
            preview_plate=None, prompt=None, extra_pnginfo=None, unique_id=None):
        started = time.time()
        uid = str(unique_id)
        v_audio, v_fps = None, None
        if images is None and video is not None:
            images, v_audio, v_fps = _video_parts(video)
        if not isinstance(images, torch.Tensor):
            raise ValueError("Connect frames to 'images' (from VAE Decode) or a 'video'.")
        if audio is None:
            audio = v_audio
        rate = float(fps) if float(fps) > 0 else (v_fps or 24.0)

        notes = []
        if not edition.IS_PRO:
            # Free edition: Pro settings are switched off here (the Pro code is not shipped at all).
            if backdrop == "Custom colour":
                backdrop = "Auto"
                notes.append("Custom colour backdrop is a Pro feature; used Auto instead.")
            if edge_solve:
                edge_solve = False
                notes.append("Edge solve is a Pro feature; it was skipped.")
            if float(temporal) > 0:
                temporal = 0.0
                notes.append("Temporal smoothing is a Pro feature; it was skipped.")
            if _as_int(fill_holes) > 0:
                fill_holes = 0
                notes.append("Fill holes is a Pro feature; it was skipped.")
            if any(m is not None for m in (keep_mask, garbage_mask)):
                keep_mask = garbage_mask = None
                notes.append("keep_mask / garbage_mask are Pro features; they were ignored.")
            if writer.FORMATS.get(output_format) in edition.PRO_FORMATS:
                notes.append(f"'{output_format}' is a Pro format; saved ProRes 4444 instead.")
                output_format = "ProRes 4444 (.mov) - Premiere/AE/Resolve"
            cap = int(edition.FREE_MAX_FRAMES)
            if int(images.shape[0]) > cap:
                notes.append(f"The Free edition keys the first {cap} frames (about {cap / rate:.1f} s); "
                             f"your clip has {int(images.shape[0])}. Pro has no length limit.")
                images = images[:cap]
                if audio is not None:
                    audio = _trim_audio(audio, cap / rate)
                if pass_b is not None:
                    pass_b = None

        settings = KeySettings(
            backdrop=BACKDROP_CHOICES.get(backdrop, "auto"), custom_color=custom_color,
            screen_gain=screen_gain, screen_balance=screen_balance, shadows=str(shadows).lower(),
            plate_fix=plate_fix, clip_black=clip_black, clip_white=max(clip_white, clip_black + 0.01),
            edge_solve=edge_solve, edge_detail=edge_detail, choke=choke, softness=softness, despill=despill,
            edge_extend=edge_extend, despeckle=despeckle, temporal=temporal,
            fill_holes=_as_int(fill_holes),
            plate_temporal=None if edition.IS_PRO else 0.5,
        )

        try:
            import comfy.utils
            bar = comfy.utils.ProgressBar(100)
        except Exception:
            bar = None

        def report(stage, done, total, lo, hi):
            pct = lo + (hi - lo) * done / max(1, total)
            if bar:
                bar.update_absolute(int(pct), 100)
            _send("h3tv.progress", {"node": uid, "stage": stage, "done": done, "total": total,
                                       "percent": pct, "elapsed": time.time() - started})

        device = _device()
        try:
            rgba, info = key_sequence(
                images, settings, frames_b=pass_b, keep_mask=keep_mask, garbage_mask=garbage_mask,
                device=device, chunk=8,
                on_progress=lambda d, t: report("Keying", d, t, 0, 70))
        except RuntimeError as err:
            if "out of memory" not in str(err).lower() or str(device) == "cpu":
                raise
            # Never fail the run over VRAM: the matte is light enough for the CPU.
            print(f"{LOG} Out of GPU memory; retrying on CPU.")
            _free()
            rgba, info = key_sequence(
                images, settings, frames_b=pass_b, keep_mask=keep_mask, garbage_mask=garbage_mask,
                device=torch.device("cpu"), chunk=4,
                on_progress=lambda d, t: report("Keying (CPU)", d, t, 0, 70))
        _free()
        info["warnings"] = notes + list(info.get("warnings", []))

        preview = composite_preview(rgba, preview_on, preview_plate)
        kind = writer.FORMATS.get(output_format, "prores")
        premult = alpha_type.startswith("Premult")
        meta = _metadata(prompt, extra_pnginfo)
        stem = _clean_name(filename)
        saved, files, videos = [], [], {}
        folder_rel = ""

        if kind != "none" or preview_video:
            if kind != "none":
                folder, folder_rel = _project_folder(stem)
            else:
                folder = os.path.join(folder_paths.get_temp_directory(), "h3tv", f"{stem}_{int(started)}")
                folder_rel = f"h3tv/{stem}_{int(started)}"
                os.makedirs(folder, exist_ok=True)
            base_type = "output" if kind != "none" else "temp"

            def add(path, label):
                rel_dir = os.path.relpath(os.path.dirname(path), folder)
                sub = folder_rel if rel_dir == "." else f"{folder_rel}/{rel_dir}".replace("\\", "/")
                files.append({"filename": os.path.basename(path), "subfolder": sub, "type": base_type,
                              "label": label})
                saved.append(os.path.relpath(path, folder).replace("\\", "/"))

            if kind in ("prores", "prores+png", "webm", "qtrle"):
                vk = "prores" if kind == "prores+png" else kind
                ext = ".webm" if vk == "webm" else ".mov"
                path = os.path.join(folder, "alpha", f"{stem}{ext}")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                try:
                    writer.write_video(path, vk, rgba, rate, audio, meta, premult,
                                       progress=lambda d, t: report("Encoding", d, t, 70, 90))
                    add(path, "Transparent video")
                except Exception as err:
                    # Never lose the result: fall back to PNGs, which always carry alpha.
                    print(f"{LOG} {output_format} failed ({err}); writing a PNG sequence instead.")
                    info["warnings"].append(f"{output_format} could not be written ({err}); "
                                            "saved a PNG sequence instead.")
                    kind = "png"
            if kind in ("png", "prores+png"):
                pdir = os.path.join(folder, "png")
                names = writer.write_png_sequence(pdir, stem, rgba, meta, premult,
                                                  progress=lambda d, t: report("PNG", d, t, 70, 95))
                if names:
                    add(os.path.join(pdir, names[0]), f"PNG sequence ({len(names)} frames)")
            if preview_video:
                pv = os.path.join(folder, "preview")
                os.makedirs(pv, exist_ok=True)
                try:
                    p1 = writer.write_preview_mp4(os.path.join(pv, f"{stem}_preview.mp4"), preview, rate, audio, meta)
                    videos["composite"] = {"filename": os.path.basename(p1), "subfolder": f"{folder_rel}/preview",
                                           "type": base_type}
                    p2 = writer.write_preview_mp4(os.path.join(pv, f"{stem}_matte.mp4"),
                                                  rgba[..., 3:4].expand(-1, -1, -1, 3), rate, None, meta)
                    videos["matte"] = {"filename": os.path.basename(p2), "subfolder": f"{folder_rel}/preview",
                                       "type": base_type}
                    saved += [f"preview/{os.path.basename(p1)}", f"preview/{os.path.basename(p2)}"]
                except Exception as err:
                    print(f"{LOG} Preview video skipped: {err}")
            elapsed = time.time() - started
            text = format_report(info, saved, folder_rel, elapsed)
            if kind != "none":
                with open(os.path.join(folder, "report.txt"), "w", encoding="utf-8") as fh:
                    fh.write(text + "\n")
                if meta.get("workflow"):
                    with open(os.path.join(folder, "workflow.json"), "w", encoding="utf-8") as fh:
                        fh.write(meta["workflow"])
        else:
            text = format_report(info, [], "", time.time() - started)

        report("Done", 1, 1, 100, 100)
        print(f"{LOG} " + text.replace("\n", f"\n{LOG} "))
        try:
            thumbs = _thumbs(images, rgba, preview, uid)
        except Exception as err:
            print(f"{LOG} Thumbnails skipped: {err}")
            thumbs = []
        payload = {
            "report": text, "info": _jsonable(info), "files": files, "videos": videos,
            "thumbs": thumbs, "folder": folder_rel, "saved_to_output": kind != "none",
            "fps": rate, "elapsed": time.time() - started, "edition": edition.EDITION,
        }
        alpha = rgba[..., 3]
        return {"ui": {"h3tv": [payload]},
                "result": (rgba[..., :3], alpha, rgba, preview, text)}


def _free():
    try:
        import comfy.model_management as mm
        mm.soft_empty_cache()
    except Exception:
        pass


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, float):
        return round(x, 5)
    return x
