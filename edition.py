"""Edition switch for H3 Transparent Video - SatoDive.

The build script (build.py) writes EDITION = "free" or "pro" into the shipped copy.
Everything that differs between the two editions reads from here.
"""

EDITION = "pro"                      # "free" | "pro"   (set by build.py)
IS_PRO = EDITION == "pro"

YOUTUBE_URL = "https://www.youtube.com/@SatoDive"
PATREON_URL = ""                     # <- your Patreon page; shown on locked Pro features in the Free edition

FREE_MAX_FRAMES = 124                # Free keys the first 124 frames (about 5 s at 24 fps)
PRO_FORMATS = ("webm", "qtrle")      # output kinds that are Pro-only
