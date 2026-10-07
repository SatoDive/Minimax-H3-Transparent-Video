"""H3 Shot: MiniMax H3 prompt + latent in seconds, with resolution presets, reference image and backdrop.

This node wraps ComfyUI's native MiniMax H3 conditioning nodes (``MiniMaxH3ImageToVideo`` for text /
first-last frame, ``MiniMaxH3ReferenceToVideo`` for reference images), so it keeps working when ComfyUI
updates them. Its outputs plug straight into the same sampler chain as the native node.
"""

from __future__ import annotations

try:
    from . import shot
except ImportError:  # imported standalone (tests)
    import shot

LOG = "[H3 Shot]"


def _native():
    """ComfyUI's own MiniMax H3 nodes (imported lazily so this file loads without ComfyUI)."""
    try:
        from comfy_extras import nodes_minimax_h3 as native
    except Exception as err:  # pragma: no cover
        raise RuntimeError(
            f"{LOG} ComfyUI's native MiniMax H3 nodes were not found ({err}). Update ComfyUI to a version "
            "that includes 'MiniMax H3 Image to Video'."
        ) from err
    return native


class H3Shot:
    CATEGORY = "SatoDive/H3 Transparent Video"
    FUNCTION = "build"
    RETURN_TYPES = ("CONDITIONING", "LATENT", "INT", "INT", "FLOAT", "INT", "INT", "STRING")
    RETURN_NAMES = ("positive", "latent", "frames", "fps", "seconds", "width", "height", "prompt_used")
    DESCRIPTION = (
        "MiniMax H3 shot setup: type the length in seconds, pick a resolution preset, add a reference image "
        "and name the object to use, and let the node append the backdrop text for transparent video."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "prompt": ("STRING", {"multiline": True, "dynamicPrompts": True, "default": "",
                                      "tooltip": "What happens in the shot. Refer to reference images as <Picture 1>, <Picture 2>..."}),
                "resolution": (list(shot.RESOLUTION_PRESETS), {"default": shot.DEFAULT_PRESET,
                               "tooltip": "Size preset. Pick 'Custom' to use width / height below."}),
                "width": ("INT", {"default": 960, "min": 32, "max": 4096, "step": 32,
                                  "tooltip": "Used only when resolution is Custom."}),
                "height": ("INT", {"default": 640, "min": 32, "max": 4096, "step": 32,
                                   "tooltip": "Used only when resolution is Custom."}),
                "seconds": ("FLOAT", {"default": 5.0, "min": shot.MIN_SECONDS, "max": shot.MAX_SECONDS, "step": 0.1,
                                      "tooltip": "Length in seconds at 24 fps. Snaps up to the model's frame grid: 5 s = 124 frames. "
                                                 "Trained range is about 5-15 s."}),
                "backdrop": (list(shot.BACKDROP_TEXT), {"default": "Green screen",
                             "tooltip": "Adds the matching 'isolated on a flat backdrop' text to the prompt. "
                                        "Use the same backdrop in the H3 Transparent Video node."}),
                "camera": (list(shot.CAMERA_TEXT), {"default": shot.DEFAULT_CAMERA}),
                "subject": ("STRING", {"default": "",
                                       "tooltip": "With a reference image: the object to take from it, e.g. 'the red sports car'. "
                                                  "Everything else in the reference is ignored."}),
                "audio_prompt": ("STRING", {"multiline": True, "default": "",
                                            "tooltip": "Optional sound description, added as an 'Audio:' line."}),
                "ref_image_size": (["match", "max"], {"default": "match",
                                   "tooltip": "match = reference scaled to the generation size (fast). max = 2048 px short edge "
                                              "(best identity, can be several times slower)."}),
            },
            "optional": {
                "ref_image_1": ("IMAGE", {"tooltip": "Reference image (<Picture 1>)."}),
                "ref_image_2": ("IMAGE", {"tooltip": "Reference image (<Picture 2>)."}),
                "ref_image_3": ("IMAGE", {"tooltip": "Reference image (<Picture 3>)."}),
                "first_frame": ("IMAGE", {"tooltip": "Start the video from this image. Cannot be combined with reference images."}),
                "last_frame": ("IMAGE", {"tooltip": "End the video on this image. Cannot be combined with reference images."}),
            },
        }

    def build(self, clip, vae, prompt, resolution, width, height, seconds, backdrop, camera, subject,
              audio_prompt, ref_image_size, ref_image_1=None, ref_image_2=None, ref_image_3=None,
              first_frame=None, last_frame=None):
        refs = [r for r in (ref_image_1, ref_image_2, ref_image_3) if r is not None]
        if refs and (first_frame is not None or last_frame is not None):
            raise ValueError(f"{LOG} Use either reference images or first/last frame, not both.")

        w, h = shot.resolve_resolution(resolution, width, height)
        frames = shot.seconds_to_frames(seconds)
        final_prompt = shot.build_prompt(prompt, backdrop=backdrop, camera=camera, audio=audio_prompt,
                                         subject=subject, ref_count=len(refs))
        native = _native()

        if refs:
            ref_dict = {f"ref_image_{i + 1}": img for i, img in enumerate(refs)}
            out = native.MiniMaxH3ReferenceToVideo.execute(
                clip=clip, prompt=final_prompt, width=w, height=h, length=frames,
                ref_image_size=ref_image_size, vae=vae, ref_images=ref_dict)
        else:
            out = native.MiniMaxH3ImageToVideo.execute(
                clip=clip, vae=vae, prompt=final_prompt, width=w, height=h, length=frames,
                first_frame=first_frame, last_frame=last_frame)

        positive, latent = out[0], out[1]
        print(f"{LOG} {w}x{h}, {frames} frames ({shot.frames_to_seconds(frames):.2f} s)"
              f"{', ' + str(len(refs)) + ' reference image(s)' if refs else ''}")
        return (positive, latent, frames, shot.FPS, shot.frames_to_seconds(frames), w, h, final_prompt)
