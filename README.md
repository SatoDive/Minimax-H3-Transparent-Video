# H3 Transparent Video - SatoDive

**Pro edition** (Patreon). Thank you for supporting the channel. MIT licensed, see `LICENSE`.

By [SatoDive](https://www.youtube.com/@SatoDive) on YouTube.

Transparent video from MiniMax H3, in **one ComfyUI node**. Generate the shot over a backdrop,
and the Studio turns it into a **ProRes 4444 `.mov` with a real alpha channel** (or an RGBA PNG
sequence) that drops straight into Premiere, After Effects, DaVinci Resolve or Final Cut.

<p align="center"><img src="docs/result_tab.jpg" width="420"> <img src="docs/backdrop_tab.jpg" width="420"></p>

## What's new in 1.4

- **H3 Shot node** (`SatoDive/H3 Transparent Video`): type the length in **seconds**, pick a **resolution preset**
  (Custom keeps width / height), add up to 3 **reference images** and name the **subject** to take from them,
  and the backdrop text for transparent video is added to the prompt for you. See `workflows/H3_TV_03_...`.

## What's new in 1.3

- **Renamed** to *H3 Transparent Video - SatoDive*: the node, the pack, the folder, the output folder
  (`output/H3_Transparent_Video`) and all internal names. Workflows saved with 1.2 and earlier use the old
  node id; load the new example workflows, or re-add the node.
- New panel logo; click it to open the SatoDive YouTube channel.
- Single Pro build (MIT).

## What's new in 1.1

- **Fully standalone.** Both example workflows use only native ComfyUI nodes plus this pack
  (no other custom node packs needed).
- Workflow 02 follows the official MiniMax H3 template: `MiniMaxH3ImageToVideo` → `SamplerCustomAdvanced`
  → `VAEDecode` + `VAEDecodeAudio` → H3 Transparent Video.
- **Model auto-pick:** if a loader's file name in the shipped workflow is not installed, the closest
  installed H3 file is selected on load (only loaders of these workflows are touched).
- `keep_mask` is shrunk 3 px before use, so a hard segmentation mask (e.g. native *Remove Background*)
  fills holes without hardening soft edges.

## What's new in 1.0

- **One node** replaces Alpha Matte + Save RGBA + Save Transparent MOV and the two-pass Region Mask recipe.
- **One generation instead of two.** No more "identical subject in both passes" requirement.
- **Per-pixel backdrop model.** Gradients, vignettes and colour drift from the generation leave no haze.
- **Edge solve.** Motion-blurred edges of strongly coloured subjects (a red car, orange fire) stay soft
  instead of turning hard with an olive fringe.
- **Clean colour.** Unmix + despill + edge colour extend: no green, dark or light outlines in the edit.
- **Verified output.** Every alpha file is decoded again after writing; an opaque file is never handed to you.
- **Studio UI.** Tabs, presets, copy-ready backdrop prompts, a result viewer with wipe and playback,
  quality tips, and a library of past runs.

## Why the old method could not work

The two-pass approach (render over green, re-render over magenta with the subject held at denoise 0,
then triangulate) breaks for structural reasons, not tuning ones:

1. Holding the subject at denoise 0 also holds **whatever was behind its soft edges**. Smoke, motion
   blur and hair keep the *same* old background in both passes, so the maths returns
   *alpha = 1* there: the soft edges come out opaque, with the old background baked in.
2. The Region Mask lives on the 16-pixel latent grid with a ~32 px feather. Inside the feather
   the subject is partially regenerated and differs between passes, which the solve turns into
   coloured noise along every edge.
3. The VAE decoder mixes neighbouring latents, so even bit-exact tokens decode to different pixels
   next to anything that changed.
4. The passes went through H.264 (4:2:0 chroma + compression), and the solve *divides* by the
   background difference, amplifying that noise. The generated "flat green" is also never the exact
   preset colour the solve assumed.

So H3 Transparent Video keys **one** generation against a **measured** backdrop instead.

## Install

1. Copy `ComfyUI-H3-TransparentVideo-SatoDive` into `ComfyUI/custom_nodes/`.
2. Restart ComfyUI. No extra Python packages: it uses torch, PyAV, numpy and Pillow, which ComfyUI already ships.
3. Load a workflow from `workflows/`.

## Workflows

| File | What it does |
|---|---|
| `H3_TV_01_Key_a_Clip.json` | Load Video → **H3 Transparent Video**. Key any clip already generated on a backdrop. 3 nodes. |
| `H3_TV_02_Generate_Transparent_Shot.json` | Native H3 generation → VAE Decode → **H3 Transparent Video**, audio included. Frames go straight from the VAE into the Studio: no MP4 in between. |

Requirements: a ComfyUI recent enough to include the native MiniMax H3 nodes, and this pack. Nothing else.

Workflow 02, all native: `UNETLoader` → `ModelSamplingMiniMaxH3` (6 / 3) → `LoraLoaderModelOnly` (turbo, 0.8),
`CLIPLoader` (type *minimax*), two `VAELoader`s, `MiniMaxH3ImageToVideo` (864×480, 124 frames ≈ 5 s),
`KSamplerSelect` (*res_multistep*), `BasicScheduler` (*simple*, 7 steps), `RandomNoise`, `BasicGuider`,
`SamplerCustomAdvanced`, `VAEDecode`, `VAEDecodeAudio`. Without a turbo LoRA, bypass it and use ~20 steps.
For image-to-video connect a `Load Image` to `first_frame`.

<p align="center"><img src="docs/workflow_02.jpg" width="860"></p>

## How to get a clean result

**1 · Generate on the right backdrop.** Studio → *Backdrop* tab → pick the recipe and press *Copy*,
then paste it at the end of your H3 prompt:

| Element | Backdrop | Why |
|---|---|---|
| Person, car, object, creature | **Green** (Blue if the subject is green) | colour-difference key, full semi-transparency |
| Fire, explosions, sparks, glow, magic | **Black** | exported as unmultiplied light: bright = opaque |
| Dark smoke, ink, dust, silhouettes | **White** | the mirror of the black mode |

**2 · Feed frames straight from VAE Decode** (workflow 02). A saved MP4 has 4:2:0 chroma; edges and
smoke are still fine, but detail finer than 2 px loses opacity. The Studio detects this and tells you.

**3 · Queue.** The *Result* tab shows composite / matte / source / wipe, a player, and quality chips.
If something needs attention, the tips say exactly which slider to move.

## Output

```
output/H3_Transparent_Video/<name>_NNN/
  alpha/<name>.mov        ProRes 4444, 12-bit alpha, H3 audio track (or .webm / QTRLE)
  png/<name>_00000.png    RGBA PNG sequence (if chosen)
  preview/<name>_preview.mp4, <name>_matte.mp4   small files for the in-node player
  report.txt              backdrop, matte statistics, tips
  workflow.json           the workflow that made it (also embedded in every file)
```

**Importing:** Premiere / After Effects / Resolve: import the `.mov`, nothing to set; alpha is
detected as *straight*. PNG sequence: *File › Import*, pick the first frame, tick *PNG Sequence*.
MP4/H.264 can never carry transparency, which is why it is only used for previews.

## Settings (all on the node)

| Tab | Setting | Default | What it does |
|---|---|---|---|
| Backdrop | Generated on | Auto | Auto reads the frame border; or force Green / Blue / Black / White / Custom hex |
| Matte | Preset | - | Balanced · Hair & smoke · Hard edges · Fire & glow · Fire on green |
| | Strength | 1.00 | more = removes more backdrop |
| | Balance | 0.00 | 0 protects yellows/cyans; up = softer edges |
| | Plate fix | 1.00 | per-pixel backdrop compensation (0 = flat colour) |
| | Shadows | Keep | keep backdrop shadows as soft alpha, or remove them |
| | Clip black / white | 0.03 / 0.95 | kill leftover haze / fill faint holes |
| Edges | Edge solve | on | correct blur on strongly coloured subjects |
| | Edge detail | 2 | edge-aware refinement radius (px) |
| | Choke / Softness | 0 / 0 | shrink-grow / blur the matte (px) |
| | Despill | 1.00 | remove backdrop colour reflected on the subject |
| | Edge colour extend | on | no fringes after compositing or scaling |
| | Despeckle / Temporal | 8 / 0.5 | remove faint specks / motion-aware flicker smoothing |
| | Fill holes | 0 | fill pinholes enclosed by the subject (px radius, 3-6 typical); colour is taken from nearby solid pixels |
| Output | Save as | ProRes 4444 | ProRes 4444 · ProRes + PNG · PNG · WebM VP9 alpha · QuickTime Animation · preview only |
| | Alpha | Straight | Premultiplied only if your compositor asks for it |

Optional inputs: `audio`, `keep_mask` (areas that must stay solid; the native *Load Background Removal
Model* → *Remove Background* nodes make a good one when a subject has backdrop-coloured holes), `garbage_mask`
(everything black is forced clear), `pass_b` (advanced: the same shot on a second backdrop;
triangulated only where both passes agree), `preview_plate` (a background to judge the composite on).

Outputs: `foreground` (straight RGB), `alpha` (MASK), `rgba`, `preview` (composite), `report`.

## Quality, measured

On a synthetic shot with known ground truth (a tumbling red object with motion blur, a semi-transparent
smoke trail, debris, a vignetted gradient green with noise and spill, saved as H.264), decoded back
from the saved `.mov`:

| | alpha error | blurred-edge error | backdrop leak | composite error |
|---|---|---|---|---|
| H3 Transparent Video 1.0 | 0.031 | 0.082 | 0.0001 | 0.015 |

<p align="center"><img src="docs/quality_check.jpg" width="760"><br>
<sub>Top: source and matte. Bottom: our composite over a new plate (left) vs. ground truth (right).</sub></p>

## Limits (honest list)

- The model must actually produce a backdrop. Floors, horizons or props the prompt did not prevent
  get keyed as subject (use `garbage_mask`, or regenerate).
- A subject that contains the backdrop colour (green clothes on green) gets holes: use Blue,
  `keep_mask`, lower *Clip white*, or raise *Fill holes* for small pinholes. Yellow and orange fire on
  green is the classic case (yellow = red + green): key fire over **black** instead, or use the
  *Fire on green* preset.
- Dark-on-white mode treats dark grey as partly transparent by design; ink and smoke look right,
  a solid grey object does not. Use green for solid objects.
- Not tested on real H3 weights (no GPU where this was built); tested on synthetic shots with ground
  truth and through the full ComfyUI frontend on CPU.

## Memory

The matte runs in 8-frame chunks on the GPU (CPU fallback on out-of-memory), so VRAM stays well
under 2 GB at 1344×768. RAM holds the input, the RGBA result and the preview: roughly
10 GB for 10 s at 1344×768. Comfortable on 32 GB.

## Tests

```
cd ComfyUI/custom_nodes/ComfyUI-H3-TransparentVideo-SatoDive
python -m pytest
```
