// H3 Shot: show width / height only when the resolution preset is "Custom".
import { app } from "../../scripts/app.js";

const NODE = "H3Shot_SatoDive";

app.registerExtension({
    name: "SatoDive.H3Shot",
    nodeCreated(node) {
        if (node.comfyClass !== NODE) return;
        try {
            const find = (n) => node.widgets?.find((w) => w.name === n);
            const preset = find("resolution");
            const dims = ["width", "height"].map(find).filter(Boolean);
            if (!preset || dims.length === 0) return;
            const stash = new Map(dims.map((w) => [w, { type: w.type, computeSize: w.computeSize }]));

            const apply = () => {
                const custom = String(preset.value).startsWith("Custom");
                for (const w of dims) {
                    const orig = stash.get(w);
                    if (custom) {
                        w.type = orig.type;
                        w.computeSize = orig.computeSize;
                        w.hidden = false;
                    } else {
                        w.type = "hidden";
                        w.computeSize = () => [0, -4];
                        w.hidden = true;
                    }
                }
                const size = node.computeSize();
                node.setSize([Math.max(node.size[0], size[0]), size[1]]);
                node.setDirtyCanvas?.(true, true);
            };

            const prev = preset.callback;
            preset.callback = function () {
                const r = prev ? prev.apply(this, arguments) : undefined;
                apply();
                return r;
            };
            setTimeout(apply, 0); // after a saved workflow restores its values
        } catch (err) {
            console.warn("[H3 Shot] could not set up the resolution toggle", err);
        }
    },
});
