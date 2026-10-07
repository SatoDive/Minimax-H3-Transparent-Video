"""Small server routes for the Transparent Video panel."""

import os

from aiohttp import web
from server import PromptServer

import folder_paths

from . import edition
from .tv_node import OUTPUT_ROOT

VIEWABLE = (".mov", ".webm", ".mp4", ".png", ".txt", ".json")


# The project library is a Pro feature: the Free edition does not register the route.
if edition.IS_PRO:
    @PromptServer.instance.routes.get("/h3tv/projects")
    async def list_projects(request):
        """Recent project folders and their files, newest first."""
        try:
            limit = max(1, min(100, int(request.query.get("limit", "20"))))
        except ValueError:
            limit = 20
        root = os.path.join(folder_paths.get_output_directory(), OUTPUT_ROOT)
        items = []
        if os.path.isdir(root):
            dirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
            dirs.sort(key=lambda d: os.path.getmtime(os.path.join(root, d)), reverse=True)
            for d in dirs[:limit]:
                files = []
                for sub in ("alpha", "png", "preview", ""):
                    folder = os.path.join(root, d, sub)
                    if not os.path.isdir(folder):
                        continue
                    names = sorted(n for n in os.listdir(folder)
                                   if os.path.isfile(os.path.join(folder, n)) and n.lower().endswith(VIEWABLE))
                    if sub == "png" and names:
                        files.append({"filename": names[0], "subfolder": f"{OUTPUT_ROOT}/{d}/png",
                                      "type": "output", "label": f"PNG sequence ({len(names)} frames)"})
                        continue
                    for n in names:
                        files.append({"filename": n, "subfolder": "/".join(x for x in (OUTPUT_ROOT, d, sub) if x),
                                      "type": "output", "label": n})
                items.append({"name": d, "path": os.path.join(root, d),
                              "mtime": os.path.getmtime(os.path.join(root, d)), "files": files})
        return web.json_response({"root": root, "projects": items})
