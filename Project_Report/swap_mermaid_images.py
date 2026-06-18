"""
swap_mermaid_images.py
-----------------------
Takes the user's hand-edited Full_Report.docx, re-renders diagrams 2, 3, 5, 8
from their updated .mmd files, and replaces only those images inside the docx.
All manual edits, formatting, and user-added images are fully preserved.
Output: Full_Report_Updated.docx
"""

import sys, os, subprocess, shutil, zipfile
from lxml import etree

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

INPUT_DOCX  = "Full_Report.docx"
OUTPUT_DOCX = "Full_Report_Updated.docx"
IMG_DIR     = "_mermaid_images"
DIAGRAMS    = [2, 3, 5, 8]

# ── Step 1: Re-render the four updated diagrams ───────────────────────────────
print("=" * 60)
print("  Step 1: Rendering updated diagrams")
print("=" * 60)

config_path = "_mmdc_tmp_cfg.json"
with open(config_path, "w") as f:
    f.write('{"theme": "default", "backgroundColor": "white"}')

new_png_bytes = {}
for i in DIAGRAMS:
    mmd_path = os.path.join(IMG_DIR, f"diagram_{i:02d}.mmd")
    tmp_png   = os.path.join(IMG_DIR, f"diagram_{i:02d}_NEW.png")
    cmd = ["cmd", "/c", "mmdc",
           "-i", mmd_path,
           "-o", tmp_png,
           "-c", config_path,
           "--scale", "2"]
    print(f"  Rendering diagram {i:02d}...", end=" ", flush=True)
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"FAILED\n    {r.stderr.decode(errors='replace')[:200]}")
        sys.exit(1)
    print("OK")
    with open(tmp_png, "rb") as f:
        new_png_bytes[i] = f.read()
    os.remove(tmp_png)

os.remove(config_path)
print()

# ── Step 2: Identify which media files inside the docx are which diagrams ─────
print("=" * 60)
print("  Step 2: Mapping diagram positions -> media filenames")
print("=" * 60)

R_NS  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS  = "http://schemas.openxmlformats.org/drawingml/2006/main"
BLIP  = f"{{{A_NS}}}blip"
EMBED = f"{{{R_NS}}}embed"

with zipfile.ZipFile(INPUT_DOCX, "r") as z:
    doc_xml  = z.read("word/document.xml")
    rels_xml = z.read("word/_rels/document.xml.rels")
    all_media = [n for n in z.namelist() if n.startswith("word/media/")]

# Build rId -> media filename map
rels_root = etree.fromstring(rels_xml)
rel_map = {}
for rel in rels_root:
    rId    = rel.get("Id")
    target = rel.get("Target", "")
    if "media/" in target:
        rel_map[rId] = target.replace("media/", "").replace("../media/", "")

# Walk the document XML to find blip elements in document order
doc_root   = etree.fromstring(doc_xml)
seen       = set()
image_order = []          # list of media filenames in appearance order
for elem in doc_root.iter():
    if elem.tag == BLIP:
        rId = elem.get(EMBED)
        if rId and rId in rel_map:
            fname = rel_map[rId]
            if fname not in seen:
                seen.add(fname)
                image_order.append(fname)

print(f"  Found {len(image_order)} unique images in document order:")
for idx, fname in enumerate(image_order, 1):
    with zipfile.ZipFile(INPUT_DOCX, "r") as z:
        try:
            size = z.getinfo(f"word/media/{fname}").file_size
        except KeyError:
            size = 0
    marker = " <-- WILL REPLACE" if idx in DIAGRAMS else ""
    print(f"    [{idx:2d}] {fname}  ({size:,} bytes){marker}")

print()

# Map: diagram index -> media filename inside the docx
diagram_to_media = {}
for d in DIAGRAMS:
    pos = d - 1   # 0-indexed
    if pos < len(image_order):
        diagram_to_media[d] = image_order[pos]
    else:
        print(f"  [warn] Diagram {d} position out of range — skipping")

# ── Step 3: Rebuild the docx, replacing only the target images ────────────────
print("=" * 60)
print("  Step 3: Rebuilding docx with new images")
print("=" * 60)

if os.path.exists(OUTPUT_DOCX):
    os.remove(OUTPUT_DOCX)

replaced_count = 0
with zipfile.ZipFile(INPUT_DOCX, "r") as zin, \
     zipfile.ZipFile(OUTPUT_DOCX, "w", compression=zipfile.ZIP_DEFLATED) as zout:

    for item in zin.infolist():
        replaced = False
        for diag_idx, media_fname in diagram_to_media.items():
            if item.filename == f"word/media/{media_fname}":
                zout.writestr(item, new_png_bytes[diag_idx])
                print(f"  Replaced word/media/{media_fname}  (diagram {diag_idx:02d})")
                replaced_count += 1
                replaced = True
                break
        if not replaced:
            zout.writestr(item, zin.read(item.filename))

print()
print(f"  {replaced_count} image(s) replaced.")
print()
print("=" * 60)
print(f"  Output: {OUTPUT_DOCX}")
print("=" * 60)
print()
print("  Your manual edits and added images are fully preserved.")
print("  Open the file in Word -> Ctrl+A -> F9 to refresh the TOC.")
