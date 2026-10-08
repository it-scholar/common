#!/usr/bin/env python3
"""kdp-metadata.py — Generate Amazon KDP title-setup metadata for a BCP Education book.

Reads the book's LaTeX configuration:
  config/metadata.tex   (required)  title, subtitle, author, edition, series, ...
  config/kdp.tex        (optional)  ISBN, keywords, categories, price, print options
  cover/cover.tex       (optional)  blurb + takeaways (fallback KDP description)

Computes (from the print PDF via pdfinfo):
  page count, exact KDP spine width, KDP printing cost and minimum list price.

Writes:
  <out-dir>/kdp-metadata.md    human-readable, structured like the KDP setup wizard
  <out-dir>/kdp-metadata.json  machine-readable

Also usable as a spine-width calculator for the Taskfile cover-print task:
  kdp-metadata.py --spine-only    # prints e.g. "0.675", exits 1 silently on failure

Stdlib only; requires Python 3.8+ and (for page-count features) poppler's pdfinfo.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date

# ─── KDP constants ────────────────────────────────────────────────────────────
# Trim size of all bcpedu books (bcpedu-layout.sty). 7in x 10in is a KDP
# "large trim size" (width > 6.12in or height > 9in), which affects cost.
TRIM_W_IN, TRIM_H_IN = 7.0, 10.0

# KDP spine width per page (inches), by interior paper/ink type.
# https://kdp.amazon.com/en_US/help/topic/G201834180
SPINE_PER_PAGE_IN = {
    "white": 0.002252,
    "cream": 0.0025,
    "premium-color": 0.002347,
}
SPINE_MIN_IN = 0.06  # keep in sync with the Taskfile fallback formula

# KDP paperback printing cost for LARGE trim sizes, per marketplace.
# (fixed, per_page, flat_below_pages, flat_cost): below flat_below_pages only
# the flat_cost applies. Rates as published 2025 — verify with KDP's
# Printing Cost & Royalty Calculator before publishing.
PRINT_COST_LARGE = {
    "black": {
        "com": ("USD", 1.00, 0.017, 110, 2.84),
        "eu":  ("EUR", 0.75, 0.016, 110, 2.48),  # de/es/fr/it/nl/ie/com.be
        "uk":  ("GBP", 0.85, 0.012, 110, 2.15),
    },
    "premium-color": {
        "com": ("USD", 1.00, 0.080, 41, 4.20),
        "eu":  ("EUR", 0.75, 0.0715, 41, 3.61),
        "uk":  ("GBP", 0.85, 0.0598, 41, 3.24),
    },
}

KDP_DESC_MAX_CHARS = 4000
KDP_MAX_KEYWORDS = 7
KDP_MAX_CATEGORIES = 3
AMAZON_ROYALTY_RATE = 0.60          # amazon.* distribution channel
EXPANDED_ROYALTY_RATE = 0.40        # expanded distribution channel


# ─── Minimal LaTeX macro parser ───────────────────────────────────────────────

def _strip_comments(text):
    """Remove LaTeX comments (% to EOL), respecting \% escapes."""
    out_lines = []
    for line in text.splitlines():
        out, i = [], 0
        while i < len(line):
            ch = line[i]
            if ch == "\\" and i + 1 < len(line):
                out.append(line[i:i + 2])
                i += 2
                continue
            if ch == "%":
                break
            out.append(ch)
            i += 1
        out_lines.append("".join(out))
    return "\n".join(out_lines)


def parse_macros(path):
    """Extract \\name{value} macros (brace-balanced, multiline-safe)."""
    with open(path, encoding="utf-8") as fh:
        text = _strip_comments(fh.read())
    macros = {}
    for m in re.finditer(r"\\([A-Za-z]+)\s*\{", text):
        name = m.group(1)
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "\\" and i + 1 < len(text):
                i += 2
                continue
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        macros[name] = text[m.end():i]
    return macros


def latex_to_text(raw):
    """Best-effort plain-text rendering of a LaTeX fragment."""
    t = raw
    t = t.replace("---", "—").replace("--", "–")
    t = t.replace("``", "“").replace("''", "”")
    t = t.replace("`", "‘").replace("'", "’")
    t = t.replace(r"\&", "&").replace(r"\%", "%").replace(r"\$", "$")
    t = t.replace(r"\#", "#").replace(r"\_", "_")
    t = re.sub(r"\\textcopyright\b", "©", t)
    t = re.sub(r"\\LaTeX\b", "LaTeX", t)
    t = re.sub(r"\\TeX\b", "TeX", t)
    t = re.sub(r"\\item\b", "\n- ", t)
    t = re.sub(r"\\newline|\\\\", "\n", t)
    # unwrap simple one-arg formatting commands (\emph{...}, \textbf{...}, ...)
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", "", t)  # drop leftover zero-arg commands
    t = t.replace("{", "").replace("}", "")
    t = t.replace("~", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines()]
    out, blank = [], False
    for ln in lines:
        if not ln:
            if not blank:
                out.append("")
            blank = True
        else:
            out.append(ln)
            blank = False
    return "\n".join(out).strip()


# ─── Field helpers ────────────────────────────────────────────────────────────

def merge_macros(*dicts):
    merged = {}
    for d in dicts:
        merged.update(d)
    return merged


def field(macros, name, default=""):
    val = macros.get(name, "")
    val = latex_to_text(val).strip()
    return val if val else default


def valid_isbn13(isbn):
    digits = re.sub(r"[- ]", "", isbn)
    if not re.fullmatch(r"\d{13}", digits):
        return False
    total = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(digits))
    return total % 10 == 0


def page_count(pdf_path):
    try:
        out = subprocess.run(
            ["pdfinfo", pdf_path], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    m = re.search(r"^Pages:\s+(\d+)", out, re.MULTILINE)
    return int(m.group(1)) if m else None


def spine_width_in(pages, paper):
    per_page = SPINE_PER_PAGE_IN.get(paper, SPINE_PER_PAGE_IN["white"])
    return max(pages * per_page, SPINE_MIN_IN)


def printing_costs(pages, ink):
    table = PRINT_COST_LARGE.get(ink, PRINT_COST_LARGE["black"])
    costs = {}
    for market, (currency, fixed, per_page, flat_below, flat_cost) in table.items():
        cost = flat_cost if pages < flat_below else fixed + pages * per_page
        costs[market] = {"currency": currency, "cost": round(cost, 2)}
    return costs


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--book-dir", default=os.getcwd())
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--main", default="main", help="root .tex basename")
    ap.add_argument("--spine-only", action="store_true",
                    help="print only the spine width in inches (for Taskfile)")
    args = ap.parse_args()

    book_dir = os.path.abspath(args.book_dir)
    metadata_tex = os.path.join(book_dir, "config", "metadata.tex")
    kdp_tex = os.path.join(book_dir, "config", "kdp.tex")
    cover_tex = os.path.join(book_dir, "cover", "cover.tex")
    print_pdf = os.path.join(book_dir, args.out_dir, "%s-print.pdf" % args.main)

    macros = {}
    if os.path.isfile(metadata_tex):
        macros = merge_macros(macros, parse_macros(metadata_tex))
    if os.path.isfile(kdp_tex):
        macros = merge_macros(macros, parse_macros(kdp_tex))
    if not macros:
        if args.spine_only:
            sys.exit(1)
        sys.exit("ERROR: no config/metadata.tex found in %s" % book_dir)

    paper = field(macros, "bookpapertype", "white").lower()
    ink = field(macros, "bookink", "black").lower()
    spine_key = paper if ink == "black" else "premium-color"
    pages = page_count(print_pdf) if os.path.isfile(print_pdf) else None

    if args.spine_only:
        if pages is None:
            sys.exit(1)
        print("%.3f" % spine_width_in(pages, spine_key))
        return

    cover_macros = parse_macros(cover_tex) if os.path.isfile(cover_tex) else {}

    warnings = []
    if not os.path.isfile(kdp_tex):
        warnings.append(
            "config/kdp.tex not found — using defaults. Create it (see "
            "common/latex/README.md) to set ISBN, keywords, categories, price, "
            "and print options."
        )
    if pages is None:
        warnings.append(
            "Print PDF not found at %s — page count, spine width, and printing "
            "cost unknown. Run `task print` first, then re-run `task kdp`."
            % os.path.relpath(print_pdf, book_dir)
        )

    title = field(macros, "booktitle", "Untitled Book")
    subtitle = field(macros, "booksubtitle")
    if len(title) > 200 or len(subtitle) > 200:
        warnings.append("KDP limits title and subtitle to 200 characters each.")

    description = field(macros, "booklongdescription") \
        or field(cover_macros, "bookblurb") \
        or field(macros, "bookdescription")
    if not description:
        warnings.append("No description found (set \\booklongdescription or a cover \\bookblurb).")
    elif len(description) > KDP_DESC_MAX_CHARS:
        warnings.append(
            "Description is %d chars — KDP allows at most %d."
            % (len(description), KDP_DESC_MAX_CHARS)
        )

    keywords = [k.strip() for k in field(macros, "bookkeywords").split(",") if k.strip()]
    if not keywords:
        warnings.append("No KDP keywords set (\\bookkeywords) — up to %d allowed." % KDP_MAX_KEYWORDS)
    elif len(keywords) > KDP_MAX_KEYWORDS:
        warnings.append("%d keywords set — KDP allows at most %d." % (len(keywords), KDP_MAX_KEYWORDS))

    categories = [c.strip() for c in field(macros, "bookcategories").split(",") if c.strip()]
    if not categories:
        warnings.append("No browse categories set (\\bookcategories) — up to %d allowed." % KDP_MAX_CATEGORIES)
    elif len(categories) > KDP_MAX_CATEGORIES:
        warnings.append("%d categories set — KDP allows at most %d." % (len(categories), KDP_MAX_CATEGORIES))

    isbn = field(macros, "bookisbn")
    if isbn and not valid_isbn13(isbn):
        warnings.append("ISBN %r is not a valid ISBN-13 (check digit failed)." % isbn)
    eisbn = field(macros, "bookeisbn")
    if eisbn and not valid_isbn13(eisbn):
        warnings.append("eBook ISBN %r is not a valid ISBN-13 (check digit failed)." % eisbn)

    list_price_raw = field(macros, "booklistprice")
    list_price = None
    if list_price_raw:
        try:
            list_price = float(list_price_raw)
        except ValueError:
            warnings.append("\\booklistprice %r is not a number." % list_price_raw)
    else:
        warnings.append("No list price set (\\booklistprice).")

    currency = field(macros, "bookcurrency", "USD")
    spine = spine_width_in(pages, spine_key) if pages else None
    costs = printing_costs(pages, ink) if pages else {}

    if list_price is not None and "com" in costs:
        com = costs["com"]
        if com["currency"] == currency:
            royalty = round(AMAZON_ROYALTY_RATE * list_price - com["cost"], 2)
            if royalty < 0:
                warnings.append(
                    "List price %.2f %s is below the Amazon.com minimum "
                    "(printing cost %.2f / 0.60 = %.2f)."
                    % (list_price, currency, com["cost"], com["cost"] / AMAZON_ROYALTY_RATE)
                )
        else:
            warnings.append(
                "List price currency %s differs from the com marketplace "
                "currency — set the price per marketplace in KDP." % currency
            )

    data = {
        "generated": date.today().isoformat(),
        "details": {
            "language": field(macros, "booklanguage", "English"),
            "title": title,
            "subtitle": subtitle,
            "series": field(macros, "bookseries"),
            "series_number": field(macros, "bookseriesnumber"),
            "edition": field(macros, "bookedition"),
            "version": field(macros, "bookversion"),
            "author": field(macros, "bookauthor"),
            "description": description,
            "keywords": keywords,
            "categories": categories,
            "adult_content": field(macros, "bookadultcontent", "no"),
            "ai_content": field(macros, "bookaicontent", "(declare in KDP)"),
        },
        "content": {
            "isbn_paperback": isbn or "(use free KDP ISBN)",
            "isbn_ebook": eisbn or "(optional — KDP assigns ASIN)",
            "imprint": field(macros, "bookimprint", "BCP Education"),
            "publication_date": field(macros, "bookpubdate") or "(publish immediately)",
            "trim_size": "%.0f x %.0f in" % (TRIM_W_IN, TRIM_H_IN),
            "ink": ink,
            "paper": paper,
            "bleed": field(macros, "bookbleed", "no"),
            "cover_finish": field(macros, "bookcoverfinish", "matte"),
            "interior_pdf": os.path.relpath(print_pdf, book_dir),
            "cover_pdf": os.path.join(args.out_dir, "cover-print.pdf"),
        },
        "measured": {
            "page_count": pages,
            "spine_width_in": round(spine, 3) if spine else None,
        },
        "pricing": {
            "rates_note": "KDP large-trim printing rates as published 2025 — "
                          "verify with the KDP Printing Cost & Royalty Calculator.",
            "printing_cost": costs,
            "list_price": list_price,
            "currency": currency,
            "min_list_price": {
                m: round(c["cost"] / AMAZON_ROYALTY_RATE, 2) for m, c in costs.items()
            },
            "royalty_at_list_price": (
                round(AMAZON_ROYALTY_RATE * list_price - costs["com"]["cost"], 2)
                if list_price is not None and "com" in costs
                and costs["com"]["currency"] == currency else None
            ),
            "royalty_note": "Amazon channel: %.0f%% of list minus printing cost; "
                            "expanded distribution: %.0f%%."
                            % (AMAZON_ROYALTY_RATE * 100, EXPANDED_ROYALTY_RATE * 100),
        },
        "warnings": warnings,
    }

    md = render_markdown(data)

    out_dir = os.path.join(book_dir, args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, "kdp-metadata.md")
    json_path = os.path.join(out_dir, "kdp-metadata.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("==> Wrote %s" % os.path.relpath(md_path, book_dir))
    print("==> Wrote %s" % os.path.relpath(json_path, book_dir))
    for w in warnings:
        print("WARNING: %s" % w, file=sys.stderr)


def render_markdown(data):
    d, c, m, p = data["details"], data["content"], data["measured"], data["pricing"]
    kw_lines = "\n".join(
        "| %d | %s |" % (i + 1, d["keywords"][i] if i < len(d["keywords"]) else "")
        for i in range(KDP_MAX_KEYWORDS)
    )
    cat_lines = "\n".join("- %s" % cat for cat in d["categories"]) or "- *(not set)*"

    pricing_rows = ""
    if m["page_count"]:
        for market, info in p["printing_cost"].items():
            min_price = p["min_list_price"][market]
            pricing_rows += "| Amazon.%s | %.2f %s | %.2f %s |\n" % (
                market, info["cost"], info["currency"], min_price, info["currency"])

    list_price_line = (
        "%.2f %s" % (p["list_price"], p["currency"]) if p["list_price"] else "*(not set)*")
    royalty_line = (
        "%.2f %s per sale (Amazon.com channel)" % (p["royalty_at_list_price"], p["currency"])
        if p["royalty_at_list_price"] is not None else "*(depends on list price)*")

    warnings_block = "\n".join("- ⚠️ %s" % w for w in data["warnings"]) \
        or "- ✅ No issues found."

    return """# KDP Publishing Sheet — {title}{subtitle_suffix}

Generated {date} by `task kdp` (common/latex/kdp-metadata.py).
Fields map to the three tabs of the KDP paperback setup wizard.

## 1. Paperback Details

| KDP field | Value |
|---|---|
| Language | {language} |
| Book title | {title} |
| Subtitle | {subtitle} |
| Series | {series}{series_no} |
| Edition number | {edition} (version {version}) |
| Author | {author} |
| Adult content | {adult} |
| AI-generated content | {ai} |

### Description (paste into KDP, max {desc_max} chars)

{description}

### Keywords (up to {kw_max})

| # | Keyword |
|---|---|
{kw_lines}

### Categories (up to {cat_max})

{cat_lines}

## 2. Paperback Content

| KDP field | Value |
|---|---|
| ISBN | {isbn} |
| Imprint | {imprint} |
| Publication date | {pubdate} |
| Trim size | {trim} |
| Ink | {ink} |
| Paper | {paper} |
| Bleed | {bleed} |
| Cover finish | {cover_finish} |
| Interior file | `{interior}` |
| Cover file | `{cover}` |

Leave a clear 2" × 1.2" area in the lower right of the back cover — KDP prints
the ISBN barcode there (the bcpedu cover template already marks this spot).

## 3. Paperback Pricing

- **Page count:** {pages}
- **Spine width:** {spine}
- **List price:** {list_price}
- **Estimated royalty:** {royalty}
- {royalty_note}
- _{rates_note}_

| Marketplace | Printing cost | Minimum list price |
|---|---|---|
{pricing_rows}
## 4. Kindle eBook (optional)

- **eBook ISBN:** {eisbn}
- Title, subtitle, author, description, and keywords can be reused as-is.
- Royalty plan: 70% (list 2.99–9.99) or 35%.

## Checklist

{warnings_block}
""".format(
        title=d["title"],
        subtitle=d["subtitle"] or "*(none)*",
        subtitle_suffix=(" — %s" % d["subtitle"]) if d["subtitle"] else "",
        date=data["generated"],
        language=d["language"],
        series=d["series"] or "*(none)*",
        series_no=(" (vol. %s)" % d["series_number"]) if d["series_number"] else "",
        edition=d["edition"], version=d["version"], author=d["author"],
        adult=d["adult_content"], ai=d["ai_content"],
        desc_max=KDP_DESC_MAX_CHARS, description=description_or_placeholder(d),
        kw_max=KDP_MAX_KEYWORDS, kw_lines=kw_lines,
        cat_max=KDP_MAX_CATEGORIES, cat_lines=cat_lines,
        isbn=c["isbn_paperback"], imprint=c["imprint"], pubdate=c["publication_date"],
        trim=c["trim_size"], ink=c["ink"], paper=c["paper"], bleed=c["bleed"],
        cover_finish=c["cover_finish"], interior=c["interior_pdf"], cover=c["cover_pdf"],
        pages=m["page_count"] if m["page_count"] else "*(build `task print` first)*",
        spine=("%.3f in" % m["spine_width_in"]) if m["spine_width_in"] else "*(unknown)*",
        list_price=list_price_line, royalty=royalty_line,
        royalty_note=p["royalty_note"], rates_note=p["rates_note"],
        pricing_rows=pricing_rows or "| — | *(page count unknown)* | — |\n",
        eisbn=data["content"]["isbn_ebook"],
        warnings_block=warnings_block,
    )


def description_or_placeholder(details):
    return details["description"] or "*(not set — add \\booklongdescription or a cover \\bookblurb)*"


if __name__ == "__main__":
    main()
