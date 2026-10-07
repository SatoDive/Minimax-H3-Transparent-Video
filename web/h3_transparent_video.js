import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Studio skin for H3 Transparent Video. It only edits the node's own widgets, so a
// workflow saved with this UI loads fine without it (plain widgets).

const NODE_TYPE = "H3TransparentVideo_SatoDive";
const PANEL_H = 720;

// build.py rewrites the next two lines for the Free / Pro zips.
const EDITION = "pro"; // @edition
const PATREON_URL = ""; // @patreon
const IS_PRO = EDITION === "pro";
const YOUTUBE_URL = "https://www.youtube.com/@SatoDive";
const LOGO = "data:image/png;base64,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";

// Free edition: these are shown locked (click opens the Patreon page).
const PRO_KEYS = ["edge_solve", "temporal", "fill_holes"];
const PRO_PRESETS = ["Fire & glow", "Fire on green"];
const PRO_BACKDROPS = ["Custom colour"];
const isProFormat = (name) => /WebM|Animation/i.test(String(name));

const RECIPES = {
    subject: {
        label: "Person / object",
        backdrop: "Green screen",
        text:
            "isolated on a perfectly flat, evenly lit chroma-key green backdrop (#00B140) that fills the entire " +
            "frame edge to edge. No floor, no horizon, no set, no props, no cast shadows, no gradient, no vignette, " +
            "no reflections, no green light on the subject. The backdrop stays the identical solid green for the " +
            "whole clip and the camera never reveals anything beyond it.",
        tip: "Use Blue instead if the subject is green (plants, green clothes, slime).",
    },
    glow: {
        label: "Fire / glow / sparks",
        backdrop: "Black (fire / glow / sparks)",
        text:
            "isolated against a pure black void (#000000) that fills the entire frame. Nothing else is lit: no floor, " +
            "no ground, no environment, no haze, no smoke layer behind it, no reflections. Only the element itself " +
            "emits light; everything around it stays perfectly black for the whole clip.",
        tip: "Exports as unmultiplied light: bright = opaque, dim = see-through. Composite in Normal mode.",
    },
    smoke: {
        label: "Dark smoke / ink / dust",
        backdrop: "White (smoke / ink / dust)",
        text:
            "isolated against a pure, evenly lit white seamless backdrop (#FFFFFF) that fills the entire frame. No floor " +
            "line, no shadows on the backdrop, no gradient, no vignette, no other objects. The backdrop stays the " +
            "identical clean white for the whole clip.",
        tip: "For white smoke or steam use the black backdrop instead.",
    },
};

const PRESETS = {
    Balanced: { screen_gain: 1.0, screen_balance: 0.0, clip_black: 0.03, clip_white: 0.95, edge_detail: 2, choke: 0, softness: 0, despill: 1, despeckle: 8, temporal: 0.5, fill_holes: 0 },
    "Hair & smoke": { screen_gain: 0.95, screen_balance: 0.2, clip_black: 0.015, clip_white: 0.98, edge_detail: 3, choke: 0, softness: 0, despill: 1, despeckle: 4, temporal: 0.6, fill_holes: 0 },
    "Hard edges": { screen_gain: 1.1, screen_balance: 0.0, clip_black: 0.06, clip_white: 0.9, edge_detail: 2, choke: 0.5, softness: 0.25, despill: 1, despeckle: 20, temporal: 0.5, fill_holes: 0 },
    "Fire & glow": { screen_gain: 1.0, screen_balance: 0.0, clip_black: 0.02, clip_white: 1.0, edge_detail: 1, choke: 0, softness: 0, despill: 0, despeckle: 0, temporal: 0.4, fill_holes: 0 },
    "Fire on green": { screen_gain: 0.8, screen_balance: 0.0, clip_black: 0.03, clip_white: 0.85, edge_detail: 1, choke: 0, softness: 0, despill: 0, despeckle: 0, temporal: 0.4, fill_holes: 4 },
};

const CSS = `
.h3tv{--bg:#15171c;--card:#1c1f26;--line:#2a2e38;--txt:#d9dce3;--dim:#8a90a0;--acc:#4fd1a5;--acc2:#6aa8ff;--warn:#e8b04b;
 display:flex;flex-direction:column;gap:8px;width:100%;height:100%;box-sizing:border-box;padding:8px;background:var(--bg);
 color:var(--txt);font:12px/1.4 Inter,system-ui,sans-serif;border-radius:10px;overflow:hidden}
.h3tv *{box-sizing:border-box}
.h3tv-head{display:flex;align-items:center;gap:8px}
.h3tv-logo{width:22px;height:22px;border-radius:6px;overflow:hidden;flex:none;display:block;cursor:pointer;box-shadow:0 0 0 1px #ffffff22;transition:transform .12s}
.h3tv-logo:hover{transform:scale(1.12);box-shadow:0 0 0 1px var(--acc)}
.h3tv-logo img{width:100%;height:100%;object-fit:cover;display:block;pointer-events:none}
.h3tv-badge{padding:1px 6px;border-radius:5px;font-size:9.5px;font-weight:700;letter-spacing:.08em;border:1px solid var(--line);color:var(--dim)}
.h3tv-badge.pro{color:#f5c542;border-color:#6b5a1e;background:#2a2410}
.h3tv-badge.free{cursor:pointer}.h3tv-badge.free:hover{color:var(--txt);border-color:var(--acc)}
.h3tv-lock{position:relative}
.h3tv-lock>*:not(.h3tv-lockbadge){opacity:.38;pointer-events:none}
.h3tv-lockbadge{position:absolute;right:2px;top:50%;transform:translateY(-50%);z-index:2;font-size:9.5px;font-weight:700;letter-spacing:.06em;color:#f5c542;background:#2a2410;border:1px solid #6b5a1e;border-radius:5px;padding:1px 6px;cursor:pointer}
.h3tv-seg-lock{opacity:.5}.h3tv-seg-lock:after{content:"PRO";font-size:9px;font-weight:700;color:#f5c542;margin-left:4px}
.h3tv-upsell{border-color:#6b5a1e;background:#1f1c10}
.h3tv-upsell b{color:#f5c542}
.h3tv-title{font-weight:700;font-size:13px;letter-spacing:.02em}
.h3tv-sp{flex:1}
.h3tv-chip{padding:2px 8px;border-radius:99px;background:var(--card);border:1px solid var(--line);color:var(--dim);font-size:11px;white-space:nowrap}
.h3tv-chip.ok{color:var(--acc);border-color:#2c5a4b}.h3tv-chip.run{color:var(--acc2);border-color:#2c4266}.h3tv-chip.warn{color:var(--warn);border-color:#5e4a22}
.h3tv-tabs{display:flex;gap:2px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:2px}
.h3tv-tab{flex:1;text-align:center;padding:5px 0;border-radius:6px;cursor:pointer;color:var(--dim);user-select:none}
.h3tv-tab:hover{color:var(--txt)}.h3tv-tab.on{background:#262a33;color:var(--txt);box-shadow:inset 0 -2px 0 var(--acc)}
.h3tv-body{flex:1;overflow:auto;display:flex;flex-direction:column;gap:8px;padding-right:2px}
.h3tv-card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;display:flex;flex-direction:column;gap:7px}
.h3tv-lbl{color:var(--dim);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase}
.h3tv-seg{display:flex;flex-wrap:wrap;gap:3px}
.h3tv-seg button{flex:1 1 auto;min-width:54px;padding:5px 7px;border-radius:6px;border:1px solid var(--line);background:#20242c;color:var(--dim);cursor:pointer;font:inherit;display:flex;gap:5px;align-items:center;justify-content:center}
.h3tv-seg button:hover{color:var(--txt)}.h3tv-seg button.on{background:#24332e;border-color:#2f6b57;color:var(--txt)}
.h3tv-sw{width:10px;height:10px;border-radius:3px;border:1px solid #0006;display:inline-block}
.h3tv-row{display:grid;grid-template-columns:96px 1fr 60px;gap:8px;align-items:center}
.h3tv-row span{color:var(--dim)}
.h3tv-row input[type=range]{width:100%;accent-color:var(--acc)}
.h3tv-row input[type=number],.h3tv-in{width:100%;background:#20242c;border:1px solid var(--line);color:var(--txt);border-radius:5px;padding:3px 5px;font:inherit}
.h3tv-tog{display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--dim)}
.h3tv-tog i{width:28px;height:16px;border-radius:99px;background:#333846;position:relative;flex:none}
.h3tv-tog i:after{content:"";position:absolute;top:2px;left:2px;width:12px;height:12px;border-radius:50%;background:#aab;transition:.15s}
.h3tv-tog.on i{background:#2f6b57}.h3tv-tog.on i:after{left:14px;background:var(--acc)}
.h3tv-recipe{background:#111318;border:1px dashed var(--line);border-radius:6px;padding:7px;color:#c6cbd6;max-height:96px;overflow:auto;font-size:11.5px}
.h3tv-btn{padding:5px 10px;border-radius:6px;border:1px solid var(--line);background:#262a33;color:var(--txt);cursor:pointer;font:inherit}
.h3tv-btn:hover{border-color:var(--acc)}
.h3tv-view{position:relative;background:repeating-conic-gradient(#3a3d45 0 25%,#2b2e35 0 50%) 0 0/16px 16px;border-radius:8px;border:1px solid var(--line);aspect-ratio:16/9;overflow:hidden;display:flex;align-items:center;justify-content:center}
.h3tv-view img,.h3tv-view video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}
.h3tv-wipe{position:absolute;top:0;bottom:0;width:2px;background:var(--acc);pointer-events:none}
.h3tv-empty{color:var(--dim);text-align:center;padding:16px}
.h3tv-strip{display:flex;gap:4px;overflow-x:auto}
.h3tv-strip img{height:40px;border-radius:4px;border:2px solid transparent;cursor:pointer;opacity:.7}
.h3tv-strip img.on{border-color:var(--acc);opacity:1}
.h3tv-stats{display:flex;flex-wrap:wrap;gap:4px}
.h3tv-warn{color:var(--warn);font-size:11.5px;border-left:2px solid var(--warn);padding-left:7px}
.h3tv-file{display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #ffffff08}
.h3tv-file a{color:var(--acc2);text-decoration:none;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.h3tv-prog{height:4px;background:#262a33;border-radius:99px;overflow:hidden}
.h3tv-prog div{height:100%;width:0;background:linear-gradient(90deg,var(--acc),var(--acc2));transition:width .2s}
.h3tv-foot{display:flex;gap:6px;align-items:center;color:var(--dim);font-size:11px}
`;

function el(tag, attrs = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === "class") n.className = v;
        else if (k === "style") n.style.cssText = v;
        else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
        else if (v !== undefined && v !== null) n.setAttribute(k, v);
    }
    for (const kid of kids.flat()) {
        if (kid === null || kid === undefined || kid === false) continue; // null-safe append
        n.append(kid instanceof Node ? kid : String(kid));
    }
    return n;
}

function fill(node, ...kids) {
    node.replaceChildren();
    for (const kid of kids.flat(Infinity)) {
        if (kid === null || kid === undefined || kid === false) continue;
        node.append(kid instanceof Node ? kid : String(kid));
    }
    return node;
}

function viewUrl(f) {
    if (!f) return "";
    const q = new URLSearchParams({ filename: f.filename, subfolder: f.subfolder || "", type: f.type || "output" });
    return api.apiURL(`/view?${q}`);
}

function injectCss() {
    if (document.getElementById("h3tv-css")) return;
    document.head.append(el("style", { id: "h3tv-css" }, CSS));
}

const fmt = (v, step) => {
    const d = step >= 1 ? 0 : step >= 0.1 ? 1 : step >= 0.01 ? 2 : 3;
    return Number(v).toFixed(d);
};

class Studio {
    constructor(node) {
        this.node = node;
        this.tab = "Backdrop";
        this.recipe = "subject";
        this.result = node.properties?.h3tv_last || null;
        this.frame = 0;
        this.view = "composite";
        this.wipe = 0.5;
        this.progress = null;
        this.timer = null;
        this.root = el("div", { class: "h3tv" });
        this.controls = [];
        this.render();
    }

    w(name) { return this.node.widgets?.find((x) => x.name === name); }
    get(name) { return this.w(name)?.value; }
    set(name, value) {
        const w = this.w(name);
        if (!w || w.value === value) return;
        w.value = value;
        try { w.callback?.(value, app.canvas, this.node); } catch (_) { /* widget callbacks are optional */ }
        this.node.setDirtyCanvas?.(true, true);
    }

    // ---- controls bound to widgets ------------------------------------
    seg(name, options, labels = {}, swatches = {}, isLocked = () => false) {
        const box = el("div", { class: "h3tv-seg" });
        const paint = () => {
            for (const b of box.children) b.classList.toggle("on", b.dataset.v === String(this.get(name)) && !b.classList.contains("h3tv-seg-lock"));
        };
        for (const opt of options) {
            const locked = !IS_PRO && isLocked(opt);
            box.append(el("button", {
                "data-v": opt, title: locked ? `${opt} (Pro)` : opt, class: locked ? "h3tv-seg-lock" : "",
                onclick: () => {
                    if (locked) return this.upsell();
                    this.set(name, opt); paint(); this.afterChange(name);
                },
            }, swatches[opt] ? el("i", { class: "h3tv-sw", style: `background:${swatches[opt]}` }) : null, labels[opt] || opt));
        }
        paint();
        this.controls.push(paint);
        return box;
    }

    slider(name, label, min, max, step) {
        const range = el("input", { type: "range", min, max, step });
        const num = el("input", { type: "number", min, max, step });
        const paint = () => {
            const v = Number(this.get(name));
            range.value = v;
            num.value = fmt(v, step);
        };
        const commit = (v) => {
            v = Math.min(max, Math.max(min, Number(v)));
            if (Number.isNaN(v)) return paint();
            if (step >= 1) v = Math.round(v);
            this.set(name, v);
            paint();
        };
        range.addEventListener("input", () => commit(range.value));
        num.addEventListener("change", () => commit(num.value));
        paint();
        this.controls.push(paint);
        return el("label", { class: "h3tv-row" }, el("span", {}, label), range, num);
    }

    toggle(name, label) {
        const t = el("div", { class: "h3tv-tog" }, el("i"), label);
        const paint = () => t.classList.toggle("on", !!this.get(name));
        t.addEventListener("click", () => { this.set(name, !this.get(name)); paint(); });
        paint();
        this.controls.push(paint);
        return t;
    }

    text(name, attrs = {}) {
        const i = el("input", { class: "h3tv-in", ...attrs });
        const paint = () => { if (document.activeElement !== i) i.value = this.get(name) ?? ""; };
        i.addEventListener("change", () => this.set(name, i.value));
        paint();
        this.controls.push(paint);
        return i;
    }

    // Free edition: dim a control and make a click open the Patreon page.
    lock(node) {
        if (IS_PRO) return node;
        return el("div", { class: "h3tv-lock", title: "Pro feature", onclick: () => this.upsell() },
            node, el("span", { class: "h3tv-lockbadge" }, "🔒 PRO"));
    }

    upsell() {
        if (PATREON_URL) window.open(PATREON_URL, "_blank", "noopener,noreferrer");
        else this.flash("This is a Pro feature - available to Patreon supporters.");
    }

    flash(text) {
        if (!this.footText) return;
        this.footText.textContent = text;
        clearTimeout(this.flashTimer);
        this.flashTimer = setTimeout(() => { if (this.footText) this.footText.textContent = this.footer(); }, 3500);
    }

    proCard() {
        if (IS_PRO) return null;
        return el("div", { class: "h3tv-card h3tv-upsell" },
            el("div", {}, el("b", {}, "Pro edition"), " adds Edge solve, Fill holes, Temporal smoothing, keep / garbage masks, ",
                "Pass B, Custom colour, Fire presets, WebM + QuickTime Animation output, the project Library and no length limit."),
            el("div", {}, el("button", { class: "h3tv-btn", onclick: () => this.upsell() }, "Get Pro on Patreon")));
    }

    afterChange(name) {
        if (name === "backdrop") this.render();
    }

    sync() { for (const p of this.controls) p(); }

    // ---- layout ---------------------------------------------------------
    render() {
        this.controls = [];
        const tabs = ["Backdrop", "Matte", "Edges", "Output", "Result", "Library"];
        const status = this.statusChip();
        fill(this.root,
            el("div", { class: "h3tv-head" },
                el("a", { class: "h3tv-logo", href: YOUTUBE_URL, target: "_blank", rel: "noopener noreferrer", title: "SatoDive on YouTube" },
                    el("img", { src: LOGO, alt: "SatoDive", draggable: "false" })),
                el("div", { class: "h3tv-title" }, "H3 Transparent Video"),
                el("span", IS_PRO ? { class: "h3tv-badge pro", title: "Pro edition" } : { class: "h3tv-badge free", title: "Free edition - click for Pro", onclick: () => this.upsell() }, IS_PRO ? "PRO" : "FREE"),
                el("div", { class: "h3tv-sp" }),
                status),
            el("div", { class: "h3tv-tabs" }, tabs.map((t) => el("div", {
                class: "h3tv-tab" + (t === this.tab ? " on" : ""),
                onclick: () => { this.tab = t; this.render(); },
            }, t === "Result" && this.result ? "Result •" : t))),
            el("div", { class: "h3tv-body" }, this[`tab${this.tab}`]()),
            el("div", { class: "h3tv-prog" }, this.progBar = el("div", { style: `width:${this.progress?.percent || 0}%` })),
            el("div", { class: "h3tv-foot" }, this.footText = el("span", {}, this.footer())),
        );
    }

    statusChip() {
        if (this.progress && this.progress.percent < 100)
            return this.statusEl = el("div", { class: "h3tv-chip run" }, `${this.progress.stage} ${Math.round(this.progress.percent)}%`);
        const warn = this.result?.info?.warnings?.length;
        if (this.result) return this.statusEl = el("div", { class: "h3tv-chip " + (warn ? "warn" : "ok") }, warn ? `Done · ${warn} tip${warn > 1 ? "s" : ""}` : "Done · clean");
        return this.statusEl = el("div", { class: "h3tv-chip" }, "Ready");
    }

    footer() {
        if (this.progress && this.progress.percent < 100) return `${this.progress.stage}: ${this.progress.done}/${this.progress.total} · ${this.progress.elapsed.toFixed(1)}s`;
        if (this.result) return `Last run ${this.result.elapsed?.toFixed?.(1) ?? "?"}s · ${this.result.folder ? "output/" + this.result.folder : "not saved"}`;
        return "Generate on a backdrop (see Backdrop tab), then queue.";
    }

    tabBackdrop() {
        const sw = { Auto: "linear-gradient(135deg,#00b140,#1c5cff,#000,#fff)", "Green screen": "#00b140", "Blue screen": "#1c5cff", "Black (fire / glow / sparks)": "#000", "White (smoke / ink / dust)": "#fff", "Custom colour": this.get("custom_color") };
        const labels = { "Black (fire / glow / sparks)": "Black", "White (smoke / ink / dust)": "White", "Custom colour": "Custom" };
        const opts = this.w("backdrop")?.options?.values || Object.keys(sw);
        const det = this.result?.info?.backdrop;
        const rec = RECIPES[this.recipe];
        const custom = this.get("backdrop") === "Custom colour";
        const picker = el("input", { type: "color", value: /^#[0-9a-f]{6}$/i.test(this.get("custom_color")) ? this.get("custom_color") : "#00b140", style: "width:40px;height:24px;border:0;background:none" });
        picker.addEventListener("input", () => this.set("custom_color", picker.value.toUpperCase()));
        return [
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Generated on"),
                this.seg("backdrop", opts, labels, sw, (o) => PRO_BACKDROPS.includes(o)),
                custom ? el("div", { class: "h3tv-row" }, el("span", {}, "Colour"), this.text("custom_color"), picker) : null,
                det ? el("div", { class: "h3tv-stats" },
                    el("span", { class: "h3tv-chip ok" }, el("i", { class: "h3tv-sw", style: `background:${det.hex};margin-right:5px` }), `Detected ${det.kind} ${det.hex}`),
                    el("span", { class: "h3tv-chip" }, `border match ${Math.round(det.confidence * 100)}%`)) : null),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Backdrop recipe — add to your H3 prompt"),
                el("div", { class: "h3tv-seg" }, Object.entries(RECIPES).map(([k, r]) => el("button", {
                    class: k === this.recipe ? "on" : "", onclick: () => { this.recipe = k; this.render(); },
                }, r.label))),
                el("div", { class: "h3tv-recipe" }, rec.text),
                el("div", { style: "display:flex;gap:6px;align-items:center" },
                    el("button", { class: "h3tv-btn", onclick: (e) => this.copy(rec.text, e.target) }, "Copy"),
                    el("button", { class: "h3tv-btn", onclick: () => { this.set("backdrop", rec.backdrop); this.render(); } }, "Use this backdrop"),
                    el("span", { style: "color:var(--dim);font-size:11px" }, rec.tip))),
        ];
    }

    copy(text, btn) {
        const done = () => { btn.textContent = "Copied"; setTimeout(() => (btn.textContent = "Copy"), 1200); };
        if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(done, () => this.copyFallback(text, done));
        else this.copyFallback(text, done);
    }
    copyFallback(text, done) {
        const t = el("textarea", { style: "position:fixed;opacity:0" }); t.value = text;
        document.body.append(t); t.select();
        try { document.execCommand("copy"); done(); } catch (_) { /* clipboard blocked */ }
        t.remove();
    }

    tabMatte() {
        return [
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Preset"),
                el("div", { class: "h3tv-seg" }, Object.keys(PRESETS).map((p) => {
                    const locked = !IS_PRO && PRO_PRESETS.includes(p);
                    return el("button", {
                        class: locked ? "h3tv-seg-lock" : "", title: locked ? `${p} (Pro)` : p,
                        onclick: () => {
                            if (locked) return this.upsell();
                            for (const [k, v] of Object.entries(PRESETS[p])) {
                                if (!IS_PRO && PRO_KEYS.includes(k)) continue;
                                this.set(k, v);
                            }
                            this.sync();
                        },
                    }, p);
                }))),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Key"),
                this.slider("screen_gain", "Strength", 0.5, 2, 0.01),
                this.slider("screen_balance", "Balance", 0, 1, 0.05),
                this.slider("plate_fix", "Plate fix", 0, 1, 0.05),
                el("div", { class: "h3tv-row", style: "grid-template-columns:96px 1fr" }, el("span", {}, "Shadows"), this.seg("shadows", ["Keep", "Remove"]))),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Levels"),
                this.slider("clip_black", "Clip black", 0, 0.5, 0.005),
                this.slider("clip_white", "Clip white", 0.5, 1, 0.005)),
        ];
    }

    tabEdges() {
        return [
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Edge"),
                this.lock(this.toggle("edge_solve", "Edge solve (motion blur on coloured subjects)")),
                this.slider("edge_detail", "Edge detail", 0, 8, 1),
                this.slider("choke", "Choke", -4, 4, 0.25),
                this.slider("softness", "Softness", 0, 4, 0.25),
                this.slider("despill", "Despill", 0, 1, 0.05),
                this.toggle("edge_extend", "Edge colour extend (no fringes)")),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Clean-up"),
                this.slider("despeckle", "Despeckle px", 0, 200, 1),
                this.lock(this.slider("fill_holes", "Fill holes px", 0, 16, 1)),
                this.lock(this.slider("temporal", "Temporal", 0, 1, 0.05))),
            this.proCard(),
        ];
    }

    tabOutput() {
        const fm = this.w("output_format")?.options?.values || [];
        const short = (s) => s.replace(" - Premiere/AE/Resolve", "").replace(" (web)", "").replace(" (preview only)", "");
        return [
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, "Save as"),
                this.seg("output_format", fm, Object.fromEntries(fm.map((f) => [f, short(f)])), {}, isProFormat),
                el("div", { style: "color:var(--dim);font-size:11px" }, "ProRes 4444 keeps real alpha in Premiere, After Effects, Resolve and Final Cut. MP4/H.264 can never be transparent.")),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-row", style: "grid-template-columns:96px 1fr" }, el("span", {}, "Name"), this.text("filename")),
                this.slider("fps", "FPS (0=auto)", 0, 120, 0.001),
                el("div", { class: "h3tv-row", style: "grid-template-columns:96px 1fr" }, el("span", {}, "Alpha"), this.seg("alpha_type", this.w("alpha_type")?.options?.values || [], { "Straight (recommended)": "Straight", "Premultiplied": "Premultiplied" })),
                el("div", { class: "h3tv-row", style: "grid-template-columns:96px 1fr" }, el("span", {}, "Preview on"), this.seg("preview_on", this.w("preview_on")?.options?.values || [])),
                this.toggle("preview_video", "Write preview videos for the player")),
        ];
    }

    tabResult() {
        const r = this.result;
        if (!r) return el("div", { class: "h3tv-card h3tv-empty" }, "No result yet. Queue the workflow; the matte, a player and the saved files appear here.");
        const thumbs = r.thumbs || [];
        this.frame = Math.min(this.frame, Math.max(0, thumbs.length - 1));
        const views = ["composite", "matte", "source", "wipe"];
        if (r.videos?.composite) views.push("play");
        const view = el("div", { class: "h3tv-view" });
        this.paintView(view, thumbs[this.frame]);
        const s = r.info?.stats || {};
        const pct = (x) => `${((x || 0) * 100).toFixed(1)}%`;
        return [
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-seg" }, views.map((v) => el("button", {
                    class: v === this.view ? "on" : "", onclick: () => { this.view = v; this.render(); },
                }, { composite: "Composite", matte: "Matte", source: "Source", wipe: "Wipe", play: "▶ Play" }[v]))),
                view,
                this.view !== "play" && thumbs.length > 1 ? el("div", { class: "h3tv-strip" }, thumbs.map((t, i) => el("img", {
                    src: viewUrl(t.composite), class: i === this.frame ? "on" : "", title: `frame ${t.frame}`,
                    onclick: () => { this.frame = i; this.render(); },
                }))) : null),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-stats" },
                    el("span", { class: "h3tv-chip ok" }, `solid ${pct(s.solid)}`),
                    el("span", { class: "h3tv-chip" }, `soft ${pct(s.soft)}`),
                    el("span", { class: "h3tv-chip" }, `clear ${pct(s.clear)}`),
                    el("span", { class: "h3tv-chip" + (s.haze > 0.02 ? " warn" : "") }, `haze ${(s.haze || 0).toFixed(3)}`),
                    el("span", { class: "h3tv-chip" + (s.flicker > 0.01 ? " warn" : "") }, `flicker ${(s.flicker || 0).toFixed(3)}`),
                    el("span", { class: "h3tv-chip" }, `${r.info?.frames} fr · ${r.info?.width}×${r.info?.height} · ${r.fps} fps`)),
                (r.info?.warnings || []).map((w) => el("div", { class: "h3tv-warn" }, w)),
                r.info?.warnings?.length ? null : el("div", { style: "color:var(--acc)" }, "No issues found.")),
            el("div", { class: "h3tv-card" },
                el("div", { class: "h3tv-lbl" }, r.saved_to_output ? "Saved" : "Not saved (preview only)"),
                r.saved_to_output ? el("div", { style: "font-family:ui-monospace,monospace;font-size:11px;color:var(--txt)" }, `output/${r.folder}`) : null,
                (r.files || []).map((f) => this.fileRow(f))),
        ];
    }

    paintView(view, t) {
        if (this.view === "play" && this.result?.videos?.composite) {
            const v = el("video", { src: viewUrl(this.result.videos.composite), controls: "", loop: "", muted: "", autoplay: "", playsinline: "" });
            v.muted = true;
            view.append(v);
            return;
        }
        if (!t) { view.append(el("div", { class: "h3tv-empty" }, "Preview images expired (temp folder). Re-run to refresh.")); return; }
        if (this.view === "wipe") {
            const under = el("img", { src: viewUrl(t.source) });
            const over = el("img", { src: viewUrl(t.composite) });
            const line = el("div", { class: "h3tv-wipe" });
            const apply = () => { over.style.clipPath = `inset(0 0 0 ${this.wipe * 100}%)`; line.style.left = `${this.wipe * 100}%`; };
            view.append(under, over, line);
            view.addEventListener("pointermove", (e) => {
                const r = view.getBoundingClientRect();
                this.wipe = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
                apply();
            });
            apply();
            return;
        }
        const img = el("img", { src: viewUrl(t[this.view]) });
        img.onerror = () => img.replaceWith(el("div", { class: "h3tv-empty" }, "Preview images expired. Re-run to refresh."));
        view.append(img);
    }

    fileRow(f) {
        return el("div", { class: "h3tv-file" },
            el("span", { class: "h3tv-chip" }, (f.filename.split(".").pop() || "").toUpperCase()),
            el("a", { href: viewUrl(f), target: "_blank", title: `${f.subfolder}/${f.filename}` }, f.label || f.filename));
    }

    tabLibrary() {
        if (!IS_PRO) return [
            el("div", { class: "h3tv-card h3tv-empty" }, "The project Library (every past run, one click away) is part of the Pro edition."),
            this.proCard(),
        ];
        const box = el("div", { class: "h3tv-card" }, el("div", { class: "h3tv-empty" }, "Loading…"));
        api.fetchApi("/h3tv/projects?limit=20").then((r) => r.json()).then((data) => {
            fill(box,
                el("div", { style: "display:flex;align-items:center;gap:6px" },
                    el("div", { style: "flex:1;font-family:ui-monospace,monospace;font-size:11px;color:var(--dim)" }, `output/H3_Transparent_Video · ${data.projects.length} recent`),
                    el("button", { class: "h3tv-btn", onclick: () => this.render() }, "Refresh")),
                data.projects.length ? null : el("div", { class: "h3tv-empty" }, "No projects yet."),
                data.projects.map((p) => el("div", { style: "padding:4px 0;border-top:1px solid var(--line)" },
                    el("div", { style: "font-weight:600" }, p.name, el("span", { style: "color:var(--dim);font-weight:400;margin-left:6px" }, new Date(p.mtime * 1000).toLocaleString())),
                    p.files.map((f) => this.fileRow(f)))));
        }).catch(() => fill(box,el("div", { class: "h3tv-empty" }, "Project list unavailable.")));
        return box;
    }

    // ---- live updates -------------------------------------------------
    onProgress(d) {
        this.progress = d;
        if (this.progBar) this.progBar.style.width = `${d.percent}%`;
        if (this.footText) this.footText.textContent = this.footer();
        if (this.statusEl) this.statusEl.replaceWith(this.statusChip());
    }

    onResult(payload) {
        this.result = payload;
        this.progress = { percent: 100, stage: "Done", done: 1, total: 1, elapsed: payload.elapsed || 0 };
        this.node.properties = this.node.properties || {};
        this.node.properties.h3tv_last = payload;
        this.frame = Math.floor((payload.thumbs?.length || 1) / 2);
        this.tab = "Result";
        this.render();
    }
}

// Loaders in the shipped workflows carry properties.h3tv_role. When the saved
// file name is not installed, pick the closest installed file instead of
// leaving a red "missing model" node. Nodes without the tag are never touched.
const ROLE_KEYS = {
    dit: [["fl2va", 6], ["fl2v", 4], ["ref2va", 3], ["h3", 2], ["minimax", 2]],
    te: [["qwen3vl", 6], ["qwen", 3], ["minimax", 2], ["h3", 2]],
    video_vae: [["video_vae", 6], ["video", 2], ["h3", 2], ["minimax", 2]],
    audio_vae: [["audio_vae", 6], ["audio", 2], ["h3", 2], ["minimax", 2]],
    lora: [["turbo", 5], ["h3", 2], ["minimax", 2], ["fl2v", 1]],
};
const ROLE_NEEDS = { dit: ["h3", "minimax"], te: ["qwen"], video_vae: ["video"], audio_vae: ["audio"], lora: ["h3", "minimax"] };

export function pickModel(role, options) {
    const keys = ROLE_KEYS[role];
    if (!keys || !options?.length) return null;
    let best = null, bestScore = 0;
    for (const name of options) {
        const n = String(name).toLowerCase();
        if (!ROLE_NEEDS[role].some((k) => n.includes(k))) continue;
        const score = keys.reduce((s, [k, w]) => s + (n.includes(k) ? w : 0), 0);
        if (score > bestScore) { best = name; bestScore = score; }
    }
    return best;
}

function autoPickModels(graph) {
    for (const node of graph?._nodes || graph?.nodes || []) {
        const role = node.properties?.h3tv_role;
        if (!role) continue;
        const w = node.widgets?.find((x) => Array.isArray(x.options?.values));
        if (!w || w.options.values.includes(w.value)) continue;
        const pick = pickModel(role, w.options.values);
        if (pick) {
            console.info(`[H3 Transparent Video] ${node.type}: '${w.value}' is not installed, using '${pick}'.`);
            w.value = pick;
        }
    }
}

function hideWidget(w) {
    w.hidden = true;
    w.options = w.options || {};
    w.options.hidden = true;
    w.computeSize = () => [0, -4];
}

app.registerExtension({
    name: "SatoDive.H3TransparentVideo",
    async afterConfigureGraph() {
        try { autoPickModels(app.graph); } catch (err) { console.warn("[H3 Transparent Video] model auto-pick skipped:", err); }
    },
    setup() {
        api.addEventListener("h3tv.progress", ({ detail }) => {
            const node = app.graph?.getNodeById?.(detail?.node) ?? app.graph?._nodes?.find((n) => String(n.id) === String(detail?.node));
            node?.__h3tv?.onProgress(detail);
        });
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_TYPE) return;
        injectCss();
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = created?.apply(this, arguments);
            try {
                for (const w of this.widgets || []) hideWidget(w);
                const studio = new Studio(this);
                this.__h3tv = studio;
                // Added last so widgets_values stay aligned with the Python inputs.
                this.addDOMWidget("h3tv_panel", "div", studio.root, {
                    serialize: false, hideOnZoom: false, hideInPanel: true,
                    getMinHeight: () => PANEL_H, getHeight: () => PANEL_H,
                });
                this.setSize([Math.max(this.size?.[0] || 0, 480), Math.max(this.size?.[1] || 0, PANEL_H + 150)]);
            } catch (err) {
                console.warn("[H3 Transparent Video] UI unavailable, using plain widgets:", err);
            }
            return r;
        };
        const configure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const r = configure?.apply(this, arguments);
            const fh = this.widgets?.find((x) => x.name === "fill_holes");
            if (fh && !Number.isFinite(Number(fh.value))) fh.value = 0;   // workflows saved before 1.2.0
            else if (fh && typeof fh.value !== "number") fh.value = Number(fh.value);
            if (!IS_PRO) {   // a workflow saved with the Pro edition: switch Pro-only settings off
                const set = (n, v) => { const w = this.widgets?.find((x) => x.name === n); if (w) w.value = v; };
                set("edge_solve", false); set("temporal", 0); set("fill_holes", 0);
                const bd = this.widgets?.find((x) => x.name === "backdrop");
                if (bd && PRO_BACKDROPS.includes(bd.value)) bd.value = "Auto";
                const of = this.widgets?.find((x) => x.name === "output_format");
                if (of && isProFormat(of.value)) of.value = of.options?.values?.[0] ?? of.value;
            }
            const s = this.__h3tv;
            if (s) {
                s.result = this.properties?.h3tv_last || s.result;
                s.render();
            }
            return r;
        };
        const executed = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (output) {
            const r = executed?.apply(this, arguments);
            const payload = output?.h3tv?.[0];
            if (payload) this.__h3tv?.onResult(payload);
            return r;
        };
    },
});
