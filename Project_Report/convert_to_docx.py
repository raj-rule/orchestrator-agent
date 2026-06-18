"""
convert_to_docx.py
------------------
1. Reads Full_Report.md
2. Extracts every ```mermaid ... ``` block
3. Renders each one as a PNG with mmdc (Mermaid CLI)
4. Replaces the code fences with a Markdown image reference
5. Runs pandoc to produce Full_Report.docx with a reference style doc
"""

import os
import re
import subprocess
import sys
import textwrap

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
INPUT_MD     = os.path.join(SCRIPT_DIR, "Full_Report.md")
OUTPUT_MD    = os.path.join(SCRIPT_DIR, "_report_rendered.md")   # intermediate
OUTPUT_DOCX  = os.path.join(SCRIPT_DIR, "Full_Report_V3.docx")
IMG_DIR      = os.path.join(SCRIPT_DIR, "_mermaid_images")
MMDC_CMD     = None   # resolved below — Windows uses powershell wrapper

def _build_mmdc_cmd(mmd_file, png_file, cfg_file):
    """Build the correct mmdc command for this OS."""
    # On Windows, mmdc is installed as a .cmd/.ps1 wrapper — call via cmd.exe
    args = [
        "cmd", "/c", "mmdc",
        "-i", mmd_file,
        "-o", png_file,
        "-c", cfg_file,
        "--scale", "2",
    ]
    return args

# ── Mermaid config: white background, higher DPI ─────────────────────────────
MMDC_CONFIG = os.path.join(SCRIPT_DIR, "_mmdc_config.json")
MMDC_CONFIG_CONTENT = """{
  "theme": "default",
  "backgroundColor": "white"
}
"""

# ── Pandoc reference doc (creates default then we reuse it) ──────────────────
REF_DOCX = os.path.join(SCRIPT_DIR, "_reference.docx")


def write_mmdc_config():
    with open(MMDC_CONFIG, "w", encoding="utf-8") as f:
        f.write(MMDC_CONFIG_CONTENT)
    print(f"[config] Written: {MMDC_CONFIG}")


def ensure_img_dir():
    os.makedirs(IMG_DIR, exist_ok=True)


def render_mermaid_blocks(md_text: str) -> str:
    """Find all ```mermaid blocks, render to PNG, replace with ![](path)."""
    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
    counter = [0]
    errors  = []

    def replacer(match: re.Match) -> str:
        counter[0] += 1
        idx        = counter[0]
        diagram    = match.group(1).strip()
        mmd_file   = os.path.join(IMG_DIR, f"diagram_{idx:02d}.mmd")
        png_file   = os.path.join(IMG_DIR, f"diagram_{idx:02d}.png")
        rel_path   = os.path.relpath(png_file, SCRIPT_DIR).replace("\\", "/")

        # Write .mmd source
        with open(mmd_file, "w", encoding="utf-8") as f:
            f.write(diagram)

        # Call mmdc via the OS-appropriate wrapper
        cmd = _build_mmdc_cmd(mmd_file, png_file, MMDC_CONFIG)
        print(f"  [mmdc] Rendering diagram {idx:02d}...", end=" ", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FAILED\n    stderr: {result.stderr[:300]}")
            errors.append(idx)
            # Return a placeholder so the rest of the doc is unaffected
            return f"\n> ⚠️ *Diagram {idx} failed to render.*\n"
        else:
            print("OK")

        return f"\n![Figure {idx}]({rel_path})\n"

    rendered = pattern.sub(replacer, md_text)

    if errors:
        print(f"\n[warn] {len(errors)} diagram(s) failed to render: {errors}")
    else:
        print(f"\n[ok] All {counter[0]} diagrams rendered successfully.")

    return rendered


def ensure_reference_docx():
    """Generate a default reference.docx if one doesn't exist."""
    if not os.path.exists(REF_DOCX):
        print("[pandoc] Generating reference.docx...")
        subprocess.run(
            ["pandoc", "--print-default-data-file", "reference.docx"],
            stdout=open(REF_DOCX, "wb"),
            check=True,
        )
        print(f"[pandoc] Reference doc created: {REF_DOCX}")
    else:
        print(f"[pandoc] Using existing reference.docx")


def convert_to_docx(intermediate_md: str):
    """Run pandoc on the intermediate Markdown to produce a .docx."""
    cmd = [
        "pandoc",
        intermediate_md,
        "-o", OUTPUT_DOCX,
        "--from",  "markdown+raw_html+fenced_code_blocks",
        "--to",    "docx",
        "--reference-doc", REF_DOCX,
        "--wrap",  "none",
        "--toc",
        "--toc-depth", "3",
        "--syntax-highlighting", "tango",
    ]
    print(f"\n[pandoc] Converting to Word...\n  CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[pandoc] ERROR:\n{result.stderr}")
        sys.exit(1)
    print(f"[pandoc] Done: {OUTPUT_DOCX}")


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 60)
    print("  CriticAI Report -> Word Converter")
    print("=" * 60)

    # Validate input
    if not os.path.exists(INPUT_MD):
        print(f"[error] Input not found: {INPUT_MD}")
        sys.exit(1)

    # Auto-detect BOM encoding (VS Code sometimes saves as UTF-16 LE)
    raw_bytes = open(INPUT_MD, "rb").read(4)
    if raw_bytes[:2] in (b'\xff\xfe', b'\xfe\xff'):
        file_enc = "utf-16"
    elif raw_bytes[:3] == b'\xef\xbb\xbf':
        file_enc = "utf-8-sig"
    else:
        file_enc = "utf-8"
    print(f"[info] Detected encoding: {file_enc}")
    with open(INPUT_MD, "r", encoding=file_enc) as f:
        md_text = f.read()

    diagram_count = len(re.findall(r"```mermaid", md_text))
    print(f"[info] Found {diagram_count} Mermaid diagram(s) in {INPUT_MD}")

    # Setup
    write_mmdc_config()
    ensure_img_dir()
    ensure_reference_docx()

    # Step 1: Render diagrams
    print(f"\n[step 1] Rendering Mermaid diagrams to PNG...")
    rendered_md = render_mermaid_blocks(md_text)

    # Step 2: Write intermediate Markdown
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(rendered_md)
    print(f"[step 2] Intermediate MD written: {OUTPUT_MD}")

    # Step 3: Pandoc -> docx
    convert_to_docx(OUTPUT_MD)

    # Cleanup intermediate file
    os.remove(OUTPUT_MD)
    os.remove(MMDC_CONFIG)
    print("\n[done] Temporary files cleaned up.")
    print(f"\nOutput: {OUTPUT_DOCX}")
    print("=" * 60)


if __name__ == "__main__":
    main()
