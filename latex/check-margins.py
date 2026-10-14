#!/usr/bin/env python3
"""check-margins.py — Verify that no ink lies outside the KDP safe margins.

Renders every page of the (print) PDF with poppler's pdftoppm, finds the
bounding box of all non-white pixels, and compares it against the safe zone
that the KDP print reviewer enforces for paperback interiors (no bleed):

  - top / bottom / outer edge: 0.25in
  - gutter (binding side):     page-count dependent, see GUTTER_TIERS
                               (max tier 701-828 pages -> 0.875in)

Page 1 of the PDF is a recto (right-hand page), so the gutter is on the
LEFT of odd pages and on the RIGHT of even pages.

Exit code 0 when all pages comply, 1 when violations were found, 2 on
tooling/usage errors. Stdlib only; requires pdfinfo + pdftoppm (poppler).

Usage:
  check-margins.py --pdf out/main-print.pdf
  check-margins.py --pdf out/main-print.pdf --pages 720-740 --verbose
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ─── KDP constants ────────────────────────────────────────────────────────────
# Minimum distance of any ink from the top, bottom and outer trim edges.
EDGE_MIN_IN = 0.25
# Gutter (binding-side) minimum by total page count — paperback tiers from
# KDP's "Set margins and gutter" help. Above 828 pages KDP prints no B&W
# paperback; the largest tier is used as a floor anyway.
GUTTER_TIERS = [
    (150, 0.375),
    (300, 0.500),
    (500, 0.625),
    (700, 0.750),
    (828, 0.875),
]

# Maximum page count for a KDP hardcover (case laminate) interior.
# Content is identical across hardcover/paperback/ebook, so the hardcover
# limit constrains every format.
KDP_HARDCOVER_MAX_PAGES = 550

# Pixels at least this dark count as ink (255 = white). Catches pale design
# elements such as black!5 ghost numbers (~242), which count as ink for KDP.
INK_THRESHOLD = 250

# Chunk size for pdftoppm runs (bounds temp-dir disk usage).
RENDER_CHUNK = 100


def gutter_required_in(pages):
    for limit, gutter in GUTTER_TIERS:
        if pages <= limit:
            return gutter
    return GUTTER_TIERS[-1][1]


def get_page_count(pdf):
    try:
        out = subprocess.run(
            ["pdfinfo", pdf], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"ERROR: pdfinfo failed for {pdf}: {exc}")
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        sys.exit(f"ERROR: could not read page count from pdfinfo output for {pdf}")
    return int(m.group(1))


def read_pgm(path):
    """Read a binary PGM (P5) as produced by pdftoppm -gray."""
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"P5"):
        raise ValueError(f"{path}: not a P5 PGM")
    idx, fields = 2, []
    while len(fields) < 3:
        while idx < len(data):
            c = data[idx : idx + 1]
            if c.isspace():
                idx += 1
            elif c == b"#":
                idx = data.index(b"\n", idx) + 1
            else:
                break
        j = idx
        while j < len(data) and not data[j : j + 1].isspace():
            j += 1
        fields.append(int(data[idx:j]))
        idx = j
    idx += 1  # single whitespace separator after maxval
    w, h, _maxval = fields
    return w, h, data[idx : idx + w * h]


# Translation table: ink pixels -> 0, white pixels -> 255.
_INK_MAP = bytes.maketrans(
    bytes(range(256)), bytes([0] * INK_THRESHOLD + [255] * (256 - INK_THRESHOLD))
)


def ink_bbox_px(w, h, pixels):
    """Bounding box (min_x, min_y, max_x, max_y) of ink pixels, or None."""
    t = pixels.translate(_INK_MAP)
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        row = t[y * w : (y + 1) * w]
        if 0 in row:
            left = row.find(0)
            right = row.rfind(0)
            if left < min_x:
                min_x = left
            if right > max_x:
                max_x = right
            if y < min_y:
                min_y = y
            max_y = y
    if max_x < 0:
        return None
    return min_x, min_y, max_x, max_y


def check_pdf(pdf, dpi, tolerance_in, first, last, verbose):
    pages = get_page_count(pdf)
    gutter = gutter_required_in(pages)
    if verbose:
        print(
            f"PDF: {pdf}\n"
            f"pages: {pages}, gutter requirement: {gutter}in, "
            f"outer/top/bottom: {EDGE_MIN_IN}in, render dpi: {dpi}, "
            f"tolerance: {tolerance_in}in"
        )

    page_limit_failure = None
    if pages > KDP_HARDCOVER_MAX_PAGES:
        page_limit_failure = (
            f"page count {pages} exceeds the KDP hardcover limit of "
            f"{KDP_HARDCOVER_MAX_PAGES} pages"
        )

    first = max(1, first or 1)
    last = min(pages, last or pages)

    tmp = None
    violations = []
    try:
        tmp = tempfile.mkdtemp(prefix="bcp-margins-")
        for chunk_start in range(first, last + 1, RENDER_CHUNK):
            chunk_end = min(chunk_start + RENDER_CHUNK - 1, last)
            prefix = os.path.join(tmp, "pg")
            subprocess.run(
                [
                    "pdftoppm", "-gray", "-r", str(dpi),
                    "-f", str(chunk_start), "-l", str(chunk_end),
                    pdf, prefix,
                ],
                capture_output=True,
                check=True,
            )
            files = sorted(glob.glob(prefix + "-*.pgm"))
            if len(files) != chunk_end - chunk_start + 1:
                raise RuntimeError(
                    f"pdftoppm produced {len(files)} pages, "
                    f"expected {chunk_end - chunk_start + 1}"
                )
            for i, path in enumerate(files):
                page = chunk_start + i
                w, h, pixels = read_pgm(path)
                os.unlink(path)
                bbox = ink_bbox_px(w, h, pixels)
                if bbox is None:
                    continue  # blank page
                min_x, min_y, max_x, max_y = bbox
                recto = page % 2 == 1
                left_req = gutter if recto else EDGE_MIN_IN
                right_req = EDGE_MIN_IN if recto else gutter
                checks = [
                    ("left", min_x / dpi, left_req),
                    ("right", (w - 1 - max_x) / dpi, right_req),
                    ("top", min_y / dpi, EDGE_MIN_IN),
                    ("bottom", (h - 1 - max_y) / dpi, EDGE_MIN_IN),
                ]
                for side, actual, required in checks:
                    if actual < required - tolerance_in:
                        violations.append(
                            (page, recto, side, actual, required)
                        )
            if verbose:
                print(f"  checked pages {chunk_start}-{chunk_end}", flush=True)
    except (OSError, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
        sys.exit(f"ERROR: {exc}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    if violations:
        by_page = {}
        for page, recto, side, actual, required in violations:
            by_page.setdefault(page, []).append((recto, side, actual, required))
        for page in sorted(by_page):
            for recto, side, actual, required in by_page[page]:
                print(
                    f"page {page:>4} ({'recto' if recto else 'verso'}): "
                    f"ink {actual:.3f}in from {side} edge, "
                    f"requires {required:.3f}in "
                    f"(overflow {required - actual:.3f}in)"
                )
        print(
            f"FAIL: {len(violations)} margin violation(s) on "
            f"{len(by_page)} page(s)"
        )
    if page_limit_failure:
        print(f"FAIL: {page_limit_failure}")
    if violations or page_limit_failure:
        return 1

    print(f"OK: pages {first}-{last} comply with KDP safe margins "
          f"and the {KDP_HARDCOVER_MAX_PAGES}-page hardcover limit")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", required=True, help="path to the (print) PDF")
    ap.add_argument("--dpi", type=int, default=48,
                    help="render resolution (default: 48; 1px = 0.021in)")
    ap.add_argument("--tolerance", type=float, default=0.0,
                    help="allowed overflow in inches (default: 0)")
    ap.add_argument("--pages", metavar="A[-B]",
                    help="restrict to a page range (PDF page numbers)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        sys.exit(f"ERROR: PDF not found: {args.pdf}")
    for tool in ("pdfinfo", "pdftoppm"):
        if shutil.which(tool) is None:
            sys.exit(f"ERROR: {tool} not found (install poppler)")

    first = last = None
    if args.pages:
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", args.pages)
        if not m:
            sys.exit(f"ERROR: invalid --pages range: {args.pages}")
        first = int(m.group(1))
        last = int(m.group(2)) if m.group(2) else first

    sys.exit(check_pdf(args.pdf, args.dpi, args.tolerance, first, last,
                       args.verbose))


if __name__ == "__main__":
    main()
