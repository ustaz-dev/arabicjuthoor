"""Cross-link audit: find every internal link, verify the target exists."""
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACK = "\\"
FWD = "/"
ROOT = Path(".")
EXCLUDE = {".git", "node_modules", "fonts", ".venv", ".claude"}


def normalize(s: str) -> str:
    return s.replace(BACK, FWD)


# Collect all files for resolution
all_files = set()
for p in ROOT.rglob("*"):
    if any(part in EXCLUDE for part in p.parts):
        continue
    if p.is_file():
        all_files.add(normalize(str(p.relative_to(ROOT))))

viewer_rx = re.compile(r"viewer\.html\?file=([^\"'>&)\s]+)")
md_link_rx = re.compile(r"\]\(([^)]+)\)")
href_rx = re.compile(r"href=[\"']([^\"'#]+)[\"']")

ROOT_ASSETS = {
    "fonts.css", "favicon.svg", "manifest.webmanifest",
    "og-image.png", "og-image-ar.png",
    "feed.xml", "sitemap.xml", "robots.txt",
    "index.html", "viewer.html",
}

scan_files = []
for ext in ("*.html", "*.md"):
    for p in ROOT.rglob(ext):
        if any(part in EXCLUDE for part in p.parts):
            continue
        if "Data raw" in str(p):
            continue
        scan_files.append(p)

broken = []
total_links = 0
checked = 0

for fp in scan_files:
    try:
        text = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    rel = normalize(str(fp.relative_to(ROOT)))

    links = set()
    for m in viewer_rx.finditer(text):
        links.add(("viewer", m.group(1)))
    for m in md_link_rx.finditer(text):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#", "<")):
            continue
        links.add(("md", target.split("#")[0]))
    for m in href_rx.finditer(text):
        target = m.group(1)
        if target.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
            continue
        if target.startswith("viewer.html?file="):
            continue
        if target in ROOT_ASSETS:
            continue
        if "fonts/" in target:
            continue
        links.add(("href", target.split("#")[0]))

    total_links += len(links)

    for kind, target in links:
        if not target or target.startswith("?"):
            continue
        target = unquote(target)

        if kind == "viewer":
            resolved = target
        else:
            base = os.path.dirname(rel)
            resolved = normalize(os.path.normpath(os.path.join(base, target)))

        if resolved.startswith("./"):
            resolved = resolved[2:]

        # Also consider an absolute-from-root resolution
        alt = normalize(target).lstrip(FWD)

        if resolved in all_files or alt in all_files:
            checked += 1
        else:
            broken.append((rel, kind, target, resolved))

print(f"Scanned: {len(scan_files)} files")
print(f"Total internal links: {total_links}")
print(f"Resolved cleanly:    {checked}")
print(f"Broken:              {len(broken)}")
if broken:
    print(f"\n--- BROKEN LINKS ---")
    by_source = {}
    for src, kind, tgt, res in broken:
        by_source.setdefault(src, []).append((kind, tgt, res))
    for src, items in sorted(by_source.items()):
        print(f"\n{src}:")
        for kind, tgt, res in items[:15]:
            print(f"  [{kind}] {tgt}  ->  {res}")
        if len(items) > 15:
            print(f"  ... and {len(items) - 15} more")
