# BCP Education LaTeX Template — Setup & Usage

## Overview

All BCP Education books use the `bcpedu` document class, defined in this folder (`common/latex/`). It provides consistent layout, typography, code environments, callout boxes, cross-references, glossary, and index across all books. One source compiles to two outputs: a full-color digital PDF and a grayscale print-ready PDF.

---

## Required Tools

Install all of the following before building any book.

### 1. LaTeX Distribution

Install **TeX Live 2024+** (or MacTeX on macOS, which includes TeX Live).

**macOS:**
```bash
brew install --cask mactex
# Adds xelatex, latexmk, biber to PATH after restart or:
eval "$(/usr/libexec/path_helper)"
```

**Ubuntu/Debian:**
```bash
sudo apt-get install texlive-full biber latexmk
```

Verify:
```bash
xelatex --version
latexmk --version
biber --version
```

### 2. Python 3 + Pygments (for `minted` syntax highlighting)

```bash
# macOS
brew install python3
pip3 install pygments

# Ubuntu
sudo apt-get install python3 python3-pip
pip3 install pygments

# Verify
pygmentize --version
```

### 3. Inkscape (for SVG diagram inclusion)

The `svg` LaTeX package calls Inkscape to convert SVG files to PDF at build time. This must be on your PATH.

```bash
# macOS
brew install --cask inkscape

# Ubuntu
sudo apt-get install inkscape

# Verify
inkscape --version
```

### 4. Fonts

The template uses three open-source font families. They must be installed as system fonts.

#### IBM Plex Serif + IBM Plex Sans
Download from: https://github.com/IBM/plex/releases (look for the latest release, download `TrueType.zip`)

**macOS:** Double-click each `.ttf` file → Install, or drag to Font Book.

**Ubuntu:**
```bash
mkdir -p ~/.local/share/fonts/IBMPlex
cd ~/.local/share/fonts/IBMPlex
# Download and extract IBM Plex .ttf files here
fc-cache -f -v
```

#### JetBrains Mono
Download from: https://www.jetbrains.com/lp/mono/ or:
```bash
# macOS
brew install --cask font-jetbrains-mono

# Ubuntu
mkdir -p ~/.local/share/fonts/JetBrainsMono
# Download from https://github.com/JetBrains/JetBrainsMono/releases
# Extract .ttf files into the folder above
fc-cache -f -v
```

#### STIX Two Math (for mathematical notation)
Usually included in TeX Live. If not:
```bash
# macOS
brew install --cask font-stix-two
```

Verify font installation:
```bash
# macOS: Check Font Book, or:
fc-list | grep "IBM Plex"
fc-list | grep "JetBrains"
fc-list | grep "STIX Two"
```

---

## File Structure

```
common/
  latex/
    bcpedu.cls            Main document class (load with \documentclass{bcpedu})
    bcpedu-colors.sty     Color palette; print/digital mode switching
    bcpedu-fonts.sty      Font setup (IBM Plex + JetBrains Mono)
    bcpedu-layout.sty     Page geometry (7"×10") + running headers/footers
    bcpedu-headings.sty   Chapter/section/part heading styles
    bcpedu-code.sty       Code + terminal environments (minted + tcolorbox)
    bcpedu-callouts.sty   9 callout/admonition box types
    bcpedu-crossref.sty   Cross-book references + hyperref configuration
    bcpedu-front.sty      Title page, ToC, LoF/LoT/LoL, preface
    bcpedu-back.sty       Glossary, index, bibliography, appendix
    bcpedu-index.ist      MakeIndex style for back-of-book index
    kdp-metadata.py       KDP title-setup metadata generator (`task kdp`)
    check-margins.py      KDP safe-margin verifier for the print PDF (`task check-margins`)
    Taskfile.yml          Shared build rules (included from each book's Taskfile)
    README.md             This file
```

Each book lives in `courses/<topic>/book/` with this structure:
```
courses/<topic>/book/
  main.tex                Root document
  Makefile                Includes Makefile.common
  chapters/
    ch00-preface.tex
    ch01-*.tex
    ...
  back/
    glossary.tex
    references.bib
  assets/                 SVG diagrams for this book
```

---

## Creating a New Book

1. Create the directory structure:
   ```bash
   mkdir -p courses/mytopic/book/{chapters,back,assets}
   ```

2. Create `courses/mytopic/book/Makefile`:
   ```makefile
   MAIN      := main
   TEXENGINE := xelatex
   include ../../../common/latex/Makefile.common
   ```

3. Create `courses/mytopic/book/main.tex` — see the skeleton in `courses/linux/book/main.tex`.

4. Build:
   ```bash
   cd courses/mytopic/book
   make digital        # full-color PDF
   make print          # grayscale PDF
   make watch          # live rebuild
   ```

---

## Document Commands Reference

### Book Metadata (in preamble)
```latex
\booktitle{Linux for Application Developers}
\booksubtitle{A Comprehensive Guide}           % optional
\bookauthor{Your Name}
\bookversion{1.0}
\bookedition{First Edition}
\bookaccentcolor{1A4980}                        % hex, no #; overrides default blue
\bookseries{BCP Education}
\booksubject{Linux}
```

### Per-Book Accent Color Override
```latex
% After \documentclass{bcpedu}, before \begin{document}:
\colorlet{bcpAccent}{bcpAccentBase}             % use default steel blue (default)
\definecolor{bcpAccent}{HTML}{8B0000}           % override to dark red for this book
```

### Code Environments

```latex
% Named file with syntax highlighting + line numbers
\begin{codefile}[bash]{/etc/nginx/nginx.conf}
server {
    listen 80;
}
\end{codefile}

% Anonymous code block
\begin{codeblock}[yaml]
apiVersion: v1
kind: Pod
\end{codeblock}

% Shell input (dark terminal)
\begin{terminalin}[My Server]
$ kubectl get pods -n default
$ kubectl describe pod my-pod
\end{terminalin}

% Command output
\begin{terminalout}
NAME      READY   STATUS    RESTARTS   AGE
my-pod    1/1     Running   0          5d
\end{terminalout}
```

Inline: `\code{git commit}`, `\filename{/etc/hosts}`, `\envvar{HOME}`, `\cmdname{kubectl}`

### Callout Boxes

```latex
\begin{notebox}[Custom Title]
  Informational note here.
\end{notebox}

\begin{tipbox}
  Best practice or shortcut.
\end{tipbox}

\begin{warningbox}[Be Careful]
  Something that could go wrong.
\end{warningbox}

\begin{dangerbox}
  This will destroy data.
\end{dangerbox}

\begin{exercisebox}[Install Nginx]
  Follow these steps to install Nginx on your system.
\end{exercisebox}

\begin{definitionbox}[Container]
  A lightweight, isolated process runtime.
\end{definitionbox}

\begin{examplebox}[Real-world deployment]
  At Company X, this pattern is used because...
\end{examplebox}

\begin{objectivesbox}
  \begin{itemize}
    \item Understand the Linux process model
    \item Configure systemd services
  \end{itemize}
\end{objectivesbox}

% Numbered lab exercise (auto-increments per chapter)
\begin{labexercise}{Deploy Your First Pod}
  In this exercise you will...
\end{labexercise}
```

### Cross-References

```latex
% Cross-book callout box
\seealsobook{Docker Fundamentals}
            {Chapter 4 --- Images and Layers}
            {Covers the build context and image layering in detail.}

% Inline cross-book link (clickable in digital, footnote URL in print)
\bookhref{https://books.bcpedu.com/docker}{Docker Fundamentals}[Chapter 4]

% QR code (print only, link text in digital)
\qrlink{https://books.bcpedu.com/docker}{Docker Fundamentals}

% Internal cross-references
\chapterref{ch:containers}   % "Chapter 3"
\sectionref{sec:namespaces}  % "Section 3.2"
\figureref{fig:pod-diagram}  % "Figure 3.1"
\listingref{lst:dockerfile}  % "Listing 3.2"
```

### Glossary and Index

```latex
% In text: use a defined term (auto-links to glossary)
The \term{container} isolates processes from the host.

% Define a term inline (or put \newglossaryentry in back/glossary.tex)
\termdef{cgroup}{cgroup}{A Linux kernel feature for resource isolation.}

% Add to index without printing
\idx{systemd!unit files}

% Bold page reference (marks the definition location)
\idxbold{namespace}
```

### SVG Diagrams (from Mermaid)

```latex
\begin{figure}[htbp]
  \centering
  \includesvg[width=0.85\textwidth]{assets/mermaid/pod-lifecycle}
  \caption{Kubernetes Pod Lifecycle}
  \label{fig:pod-lifecycle}
\end{figure}
```

> **Note:** The `.svg` extension is omitted. Inkscape converts it to PDF at build time.
> Inkscape must be on your PATH. Build with `--shell-escape` (handled by `Makefile.common`).

---

## Build Outputs

| Target | Output | Mode |
|--------|--------|------|
| `make digital` | `main-digital.pdf` | Color links, colored callouts, dark terminal backgrounds |
| `make print` | `main-print.pdf` | `hidelinks`, white callout backgrounds, light terminal |
| `make watch` | `main-digital.pdf` | Auto-rebuilds on save |
| `make clean` | — | Removes aux files |
| `make distclean` | — | Removes aux files + PDFs |

---

## KDP Publishing Metadata

Each book can generate the information needed for the Amazon KDP title-setup
wizard (paperback details, content, and pricing) from its existing LaTeX
configuration:

```bash
cd courses/<topic>/books/<book>
task print   # needed once, for page count / spine width / printing cost
task kdp     # writes out/kdp-metadata.md (copy-paste sheet) + out/kdp-metadata.json
```

The generator (`kdp-metadata.py`) reads `config/metadata.tex`, the optional
`config/kdp.tex`, and the blurb/takeaways from `cover/cover.tex`. It validates
KDP rules (title ≤ 200 chars, description ≤ 4000 chars, ≤ 7 keywords, ≤ 3
categories, ISBN-13 check digit) and prints warnings for anything missing.

### Per-book KDP settings — `config/kdp.tex`

Create `config/kdp.tex` next to `config/metadata.tex` and `\input{config/kdp}`
at the end of `metadata.tex`. All commands are optional (sensible defaults in
`bcpedu.cls`); a book compiles fine without this file, but `task kdp` will warn
about the missing fields.

```latex
%% config/kdp.tex — KDP publishing metadata
\bookisbn{}                       % paperback ISBN-13; empty = use free KDP ISBN
\bookeisbn{}                      % Kindle ISBN (optional; KDP assigns an ASIN anyway)
\booklanguage{English}
\bookpubdate{}                    % YYYY-MM-DD; empty = publish when approved
\bookseriesnumber{1}              % volume within \bookseries
\bookimprint{BCP Education}       % required when using your own ISBN
\bookkeywords{kubernetes, container orchestration, devops, cloud native, kubectl, docker containers, microservices}
\bookcategories{Computers / Operating Systems / Linux & UNIX, Computers / Software Development & Engineering / Tools}
\booklistprice{34.99}
\bookcurrency{USD}
\bookpapertype{white}             % white | cream
\bookink{black}                   % black | premium-color
\bookcoverfinish{matte}           % matte | glossy
\bookbleed{no}                    % interior bleed
\bookaicontent{none}              % AI disclosure: none | some | extensive
\bookadultcontent{no}
\booklongdescription{}            % <= 4000 chars; empty = reuse the cover blurb
```

When `\bookisbn` is set it is also printed on the copyright page
(`\bcpcopyrightpage`) automatically.

### Notes

- **Trim/margins** are already KDP-compatible (7"×10", large trim class).
- **Margin verification:** `task check-margins` renders every page of
  `out/main-print.pdf` and fails if any ink lies outside the KDP reviewer's
  safe zone (0.25" from top/bottom/outer trim; page-count-dependent gutter,
  max 0.875" for 701-828 pages). Run it before every KDP (re)submission;
  pass extra flags after `--`, e.g. `task check-margins -- --pages 720-740`.
- **Spine width:** `task cover-print` uses the exact KDP formula per paper type
  (white 0.002252"/page, cream 0.0025", color 0.002347") via `kdp-metadata.py
  --spine-only`, falling back to the old 0.0025" approximation if the script
  or page count is unavailable.
- **Printing cost / minimum list price** in the generated sheet use KDP's
  published large-trim rates (2025) for Amazon.com/.de/.uk — always confirm
  with KDP's Printing Cost & Royalty Calculator before publishing.
- **Barcode:** leave the marked 2"×1.2" area on the back cover blank; KDP
  prints the ISBN barcode there.
- The `kdp` class option (`\documentclass[print,kdp]{bcpedu}`) is reserved for
  future PDF/X-1a output and currently has no effect.

---

## Troubleshooting

**`Font "IBM Plex Serif" not found`**
→ Install the IBM Plex fonts as system fonts (see above). Run `fc-cache -f -v` on Linux.

**`minted requires --shell-escape`**
→ Ensure you're using `make digital` or `make print` (not running `xelatex` directly). The Makefile passes `--shell-escape` automatically.

**`! LaTeX Error: File 'bcpedu.cls' not found`**
→ Check that `TEXINPUTS` includes the path to `common/latex/`. Use `make` from the book directory, not from the workspace root.

**`Package svg Error: Inkscape is required`**
→ Install Inkscape and ensure `inkscape` is on your PATH (`which inkscape`).

**`biber: command not found`**
→ Install biber. On macOS: `brew install biber`. On Ubuntu: `sudo apt-get install biber`.

**Glossary not printing**
→ Run `make clean` then `make digital`. glossaries-extra requires `--automake` (enabled) which calls `makeglossaries` automatically via `latexmk`.

**Mermaid SVG shows as blank**
→ Ensure the SVG was generated by `node common/build-mermaid.js` first. Then verify Inkscape can open it: `inkscape --export-pdf=test.pdf test.svg`.
