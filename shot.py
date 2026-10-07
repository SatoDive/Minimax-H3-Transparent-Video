"""Pure helpers for the H3 Shot node: seconds -> frames, resolution presets, prompt assembly.

No ComfyUI imports here, so everything in this file can be unit-tested on its own.
"""

from __future__ import annotations

import math
import re

FPS = 24                      # MiniMax H3 renders at 24 fps
MULTIPLE = 32                 # canvas sizes must be multiples of 32
MAX_PIXELS = 768 * 1344       # area the model was trained up to
MIN_SECONDS = 0.2
MAX_SECONDS = 150.0           # trained range is ~5-15 s; longer is untested

CUSTOM = "Custom (use width / height)"

# label -> (width, height).  Every size is a multiple of 32 and stays inside the trained pixel area.
RESOLUTION_PRESETS: dict[str, tuple[int, int] | None] = {
    CUSTOM: None,
    "16:9  HD - 1344x768": (1344, 768),
    "16:9  Balanced - 960x544": (960, 544),
    "16:9  Fast - 864x480": (864, 480),
    "21:9  Cinema - 1344x576": (1344, 576),
    "3:2  Photo - 960x640": (960, 640),
    "4:3  Classic - 1024x768": (1024, 768),
    "1:1  Square - 768x768": (768, 768),
    "1:1  Square Fast - 576x576": (576, 576),
    "3:4  Portrait - 768x1024": (768, 1024),
    "9:16  Vertical HD - 768x1344": (768, 1344),
    "9:16  Vertical Balanced - 544x960": (544, 960),
    "9:16  Vertical Fast - 480x864": (480, 864),
}
DEFAULT_PRESET = "16:9  Fast - 864x480"

NO_BACKDROP = "None (do not add backdrop text)"

# Same wording and same names as the Backdrop tab of the H3 Transparent Video node, so the two stay in sync.
BACKDROP_TEXT: dict[str, str] = {
    NO_BACKDROP: "",
    "Green screen": (
        "This is isolated on a perfectly flat, evenly lit chroma-key green backdrop (#00B140) that fills the entire "
        "frame edge to edge. No floor, no horizon, no set, no props, no cast shadows, no gradient, no vignette, "
        "no reflections, no green light on the subject. The backdrop stays the identical solid green for the "
        "whole clip and the camera never reveals anything beyond it."
    ),
    "Blue screen": (
        "This is isolated on a perfectly flat, evenly lit chroma-key blue backdrop (#1C5CFF) that fills the entire "
        "frame edge to edge. No floor, no horizon, no set, no props, no cast shadows, no gradient, no vignette, "
        "no reflections, no blue light on the subject. The backdrop stays the identical solid blue for the "
        "whole clip and the camera never reveals anything beyond it."
    ),
    "Black (fire / glow / sparks)": (
        "This is isolated against a pure black void (#000000) that fills the entire frame. Nothing else is lit: "
        "no floor, no ground, no environment, no haze, no smoke layer behind it, no reflections. Only the element "
        "itself emits light; everything around it stays perfectly black for the whole clip."
    ),
    "White (smoke / ink / dust)": (
        "This is isolated against a pure, evenly lit white seamless backdrop (#FFFFFF) that fills the entire frame. "
        "No floor line, no shadows on the backdrop, no gradient, no vignette, no other objects. The backdrop stays "
        "the identical clean white for the whole clip."
    ),
}

CAMERA_TEXT: dict[str, str] = {
    "Locked-off static (best for keying)": "Locked-off static camera, wide shot, the entire subject always fully in frame.",
    "Slow push-in": "Slow, smooth push-in toward the subject, the subject always fully in frame.",
    "Slow pull-out": "Slow, smooth pull-out away from the subject, the subject always fully in frame.",
    "Slow orbit": "Slow, smooth orbit around the subject, the subject always fully in frame.",
    "Handheld": "Subtle handheld camera with gentle natural movement, the subject always fully in frame.",
    "Tracking shot": "Smooth tracking shot that follows the subject, the subject always fully in frame.",
    "None (do not add camera text)": "",
}
DEFAULT_CAMERA = "Locked-off static (best for keying)"


def align_frame_count(n: int) -> int:
    """Snap up to the model's 17k+5 frame grid (5, 22, 39, ... 124, 141, ...)."""
    n = max(5, int(n))
    while n % 17 != 5:
        n += 1
    return n


def seconds_to_frames(seconds: float) -> int:
    """Seconds at 24 fps, snapped up to the frame grid. 5 s -> 124 frames."""
    seconds = min(MAX_SECONDS, max(MIN_SECONDS, float(seconds)))
    return align_frame_count(math.ceil(seconds * FPS - 1e-6))


def frames_to_seconds(frames: int) -> float:
    return frames / FPS


def snap32(value: int) -> int:
    return max(MULTIPLE, int(round(int(value) / MULTIPLE)) * MULTIPLE)


def resolve_resolution(preset: str, width: int, height: int) -> tuple[int, int]:
    """Preset size, or (width, height) snapped to a multiple of 32 for the Custom entry."""
    size = RESOLUTION_PRESETS.get(preset)
    if size is None:
        return snap32(width), snap32(height)
    return size


def _the(subject: str) -> str:
    """'red car', 'a red car' and 'the red car' all become 'the red car'."""
    subject = re.sub(r"^(the|a|an)\s+", "", subject.strip(), flags=re.IGNORECASE)
    return f"the {subject}" if subject else ""


def build_prompt(
    prompt: str,
    *,
    backdrop: str = NO_BACKDROP,
    camera: str = DEFAULT_CAMERA,
    audio: str = "",
    subject: str = "",
    ref_count: int = 0,
) -> str:
    """Assemble the final H3 prompt: [reference lead] + prompt + camera + backdrop + audio line."""
    prompt = (prompt or "").strip()
    subject = (subject or "").strip().rstrip(".")
    blocks: list[str] = []

    has_tags = "<picture" in prompt.lower()
    if ref_count > 0 and not has_tags:
        if subject:
            lead = (
                f"Use only {_the(subject)} from <Picture 1> as the subject. Keep its exact look, shape and colours, "
                "and ignore everything else in the reference image (its background, other objects and lighting)."
            )
        elif ref_count == 1:
            lead = "Use the subject of <Picture 1>. Keep its exact look, shape and colours."
        else:
            lead = "Use the subjects of " + ", ".join(f"<Picture {i}>" for i in range(1, ref_count + 1)) + "."
        blocks.append(lead)
    elif ref_count > 0 and subject:
        blocks.append(f"The subject to extract from the reference image is {_the(subject)}.")

    if prompt:
        blocks.append(prompt)
    cam = CAMERA_TEXT.get(camera, "")
    if cam:
        blocks.append(cam)
    back = BACKDROP_TEXT.get(backdrop, "")
    if back:
        if ref_count > 0:
            back = "Do not reuse the reference image's background. " + back
        blocks.append(back)
    if (audio or "").strip():
        blocks.append("Audio: " + audio.strip())
    return "\n\n".join(blocks)
