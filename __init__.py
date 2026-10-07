"""H3 Transparent Video - transparent video from MiniMax H3 (SatoDive)."""

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"

if __package__:  # empty when a test runner loads this file outside ComfyUI
    from .shot_node import H3Shot
    from .tv_node import H3TransparentVideo

    NODE_CLASS_MAPPINGS["H3TransparentVideo_SatoDive"] = H3TransparentVideo
    NODE_DISPLAY_NAME_MAPPINGS["H3TransparentVideo_SatoDive"] = "H3 Transparent Video - SatoDive"
    NODE_CLASS_MAPPINGS["H3Shot_SatoDive"] = H3Shot
    NODE_DISPLAY_NAME_MAPPINGS["H3Shot_SatoDive"] = "H3 Shot (seconds, presets, reference) - SatoDive"
    try:
        from . import tv_routes  # noqa: F401  (UI helpers; the node works without them)
    except Exception as err:  # pragma: no cover
        print(f"[H3 Transparent Video] UI routes unavailable: {err}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
