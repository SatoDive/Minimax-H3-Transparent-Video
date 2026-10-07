<h1 align="center">H3 Transparent Video Pro - SatoDive</h1>

<p align="center">
  <b>Transparent video from MiniMax H3, in one ComfyUI node.</b><br>
  ProRes 4444 <code>.mov</code> with a real alpha channel, or an RGBA PNG sequence, straight into Premiere, After Effects, DaVinci Resolve or Final Cut.
</p>

<p align="center">
  <img alt="Edition" src="https://img.shields.io/badge/edition-PRO-f96854">
  <a href="https://www.youtube.com/@SatoDive"><img alt="YouTube" src="https://img.shields.io/badge/YouTube-SatoDive-red"></a>
  <a href="https://www.patreon.com/SatoDive"><img alt="Patreon" src="https://img.shields.io/badge/Patreon-SatoDive-f96854"></a>
</p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=4L4lTf_NCSg">
    <img src="https://img.youtube.com/vi/4L4lTf_NCSg/maxresdefault.jpg" alt="Watch the Tutorial on YouTube" width="85%">
  </a>
  <br>
  <i>▶️ Click the preview above to watch the full tutorial and breakdown on YouTube</i>
</p>

Generate directly from text, image-to-video, or reference images over a flat backdrop, and the Studio turns it into a clean transparent video. One generation, one node, no two-pass tricks.

## Features

- **Text-to-Video & Image-to-Video**: Full support for text prompts, first frame, and last frame conditioning.
- **Reference Images & Subject Selection**: Steer generation and lock character/prop consistency.
- **Dedicated H3 Shot Node**: Built-in duration (seconds), resolution presets, and backdrop prompt integration.
- **Transparent Keying Studio**: Complete matte controls, edge fine-tuning, despill, and automated mask cleanup.
- **Production-Ready Exports**: ProRes 4444 (12-bit alpha), RGBA PNG sequences, WebM, and QTRLE with embedded audio.

## Install

1. Copy the `ComfyUI-H3-TransparentVideo-SatoDive` folder into `ComfyUI/custom_nodes/`.
2. Restart ComfyUI. No extra Python packages needed: it uses `torch`, `PyAV`, `numpy`, and `Pillow`, which are already bundled with ComfyUI.
3. Load a workflow from `workflows/` or grab the workflow on [Patreon](https://www.patreon.com/SatoDive/posts/make-easy-videos-171699610).

**Requirements:** A ComfyUI version recent enough to include native MiniMax H3 nodes, and this pack. Nothing else.

## Workflows

| File | What it does |
|---|---|
| `H3_Generate_Transparent_Clip.json` | **H3 Shot** → Sampler → VAE Decode → **H3 Transparent Video**, audio included. Frames pass directly from the VAE into the Studio with no intermediate MP4 compression loss. |

> 📥 **Download Workflow:** Get the ready-to-use workflow on Patreon: [Make Easy Videos (H3 Transparent Video)](https://www.patreon.com/SatoDive/posts/make-easy-videos-171699610)

The workflow uses native nodes alongside H3 Shot: `UNETLoader` → `ModelSamplingMiniMaxH3` (6 / 3) → `LoraLoaderModelOnly` (turbo, 0.8), `CLIPLoader` (type *minimax*), two `VAELoader`s, **H3 Shot** (864×480, 5 s = 124 frames), `KSamplerSelect` (*res_multistep*), `BasicScheduler` (*simple*, 7 steps), `RandomNoise`, `BasicGuider`, `SamplerCustomAdvanced`, `VAEDecode`, `VAEDecodeAudio`. *(Without a turbo LoRA, bypass it and use ~20 steps).*

**Importing:** 
- **Premiere / After Effects / DaVinci Resolve:** Import the `.mov` directly; alpha is automatically recognized as *straight*.
- **PNG sequence:** *File › Import*, select the first frame, and check *PNG Sequence*.
- *(MP4/H.264 files do not support alpha channels and are generated for in-node preview only).*

## Limits (honest list)

- The model must produce an actual backdrop. Floors, horizons, or props not prevented by the prompt will be keyed as part of the subject (regenerate or adjust the backdrop prompt if this happens).
- A subject containing the backdrop color (e.g., green clothing on a green backdrop) will create holes: switch to Blue, use `keep_mask`, reduce *Clip white*, or increase *Fill holes*.
- For fire, sparks, or yellow/orange elements, key over **black** or use the *Fire on green* preset.
- Dark-on-white mode treats dark grey as partially transparent by design (ideal for ink and smoke, but not solid grey objects). Use green for solid objects.

## Support & credits

Made by **SatoDive**: [YouTube](https://www.youtube.com/@SatoDive) · [Patreon](https://www.patreon.com/SatoDive)  
Get the full workflow & assets: [Patreon Workflow Post](https://www.patreon.com/SatoDive/posts/make-easy-videos-171699610)
