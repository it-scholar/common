%% =============================================================================
%% bcpedu.cls — BCP Education Book Class
%% =============================================================================
%% Main document class for all BCP Education technical books.
%% Extends the standard `book` class with custom styling, layout, and features.
%%
%% Usage:
%%   \documentclass[digital]{bcpedu}   % full-color PDF (default)
%%   \documentclass[print]{bcpedu}     % grayscale print-ready PDF
%%   \documentclass[print,kdp]{bcpedu} % print + KDP PDF/X compliance (future)
%%
%% Required engine: XeLaTeX or LuaLaTeX (pdfLaTeX is NOT supported)
%% =============================================================================

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{bcpedu}[2026/07/08 v1.0 BCP Education Book Class]

%% ─── Engine check ────────────────────────────────────────────────────────────
\RequirePackage{ifxetex,ifluatex}
\newif\if@xeluatex
\ifxetex\@xeluatextrue\fi
\ifluatex\@xeluatextrue\fi
\if@xeluatex\else
  \ClassError{bcpedu}{%
    This class requires XeLaTeX or LuaLaTeX.\MessageBreak
    Compile with: xelatex --shell-escape main.tex\MessageBreak
    or:           lualatex --shell-escape main.tex
  }{Switch your compiler.}
\fi

%% ─── Class options ───────────────────────────────────────────────────────────
\newif\if@bcpprint   \@bcpprintfalse   % default: digital
\newif\if@bcpkdp     \@bcpkdpfalse

\DeclareOption{digital}{\@bcpprintfalse}
\DeclareOption{print}{\@bcpprinttrue}
\DeclareOption{kdp}{\@bcpkdptrue}

%% Pass all unknown options to the book class
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{book}}
\ProcessOptions\relax

%% ─── Base class ──────────────────────────────────────────────────────────────
%% 11pt, A4/letter-neutral (geometry handles actual size), two-sided, chapters
%% open on right-hand (odd) pages.
\LoadClass[11pt,twoside,openright]{book}

%% ─── Core utilities (needed before everything else) ──────────────────────────
\RequirePackage{etoolbox}   % \AtBeginDocument, \apptocmd, \patchcmd
\RequirePackage{xparse}     % \NewDocumentCommand
\RequirePackage{ifthen}

%% ─── Book metadata commands ──────────────────────────────────────────────────
%% Set these in your document preamble BEFORE \begin{document}.
%%
%%   \booktitle{Linux for Application Developers}
%%   \booksubtitle{A Comprehensive Guide}
%%   \bookauthor{Your Name}
%%   \bookversion{1.0}
%%   \bookedition{First Edition}
%%   \bookaccentcolor{1A4980}   % hex, no leading #
%%   \bookseries{BCP Education}
%%   \booksubject{Linux}
%%   \bookdescription{Short description for PDF metadata}
%%
\newcommand{\@booktitle}{Untitled Book}
\newcommand{\@booksubtitle}{}
\newcommand{\@bookauthor}{BCP Education}
\newcommand{\@bookversion}{1.0}
\newcommand{\@bookedition}{First Edition}
\newcommand{\@bookaccentcolor}{1A4980}
\newcommand{\@bookseries}{BCP Education}
\newcommand{\@booksubject}{}
\newcommand{\@bookdescription}{}

\NewDocumentCommand{\booktitle}     {m}{\renewcommand{\@booktitle}{#1}}
\NewDocumentCommand{\booksubtitle}  {m}{\renewcommand{\@booksubtitle}{#1}}
\NewDocumentCommand{\bookauthor}    {m}{\renewcommand{\@bookauthor}{#1}}
\NewDocumentCommand{\bookversion}   {m}{\renewcommand{\@bookversion}{#1}}
\NewDocumentCommand{\bookedition}   {m}{\renewcommand{\@bookedition}{#1}}
\NewDocumentCommand{\bookaccentcolor}{m}{\renewcommand{\@bookaccentcolor}{#1}}
\NewDocumentCommand{\bookseries}    {m}{\renewcommand{\@bookseries}{#1}}
\NewDocumentCommand{\booksubject}   {m}{\renewcommand{\@booksubject}{#1}}
\NewDocumentCommand{\bookdescription}{m}{\renewcommand{\@bookdescription}{#1}}

%% ─── Load sub-packages in dependency order ────────────────────────────────
%%
%% 1. Colors first (everything else depends on color names)
%% 2. Fonts (needed before tcolorbox/minted which render text)
%% 3. Layout (page geometry and headers)
%% 4. Headings (titlesec chapter/section styles)
%% 5. Code environments
%% 6. Callout boxes
%% 7. Cross-reference utilities
%% 8. Front matter (title page, ToC)
%% 9. Back matter (glossary, index, bibliography)
%%
\if@bcpprint
  \PassOptionsToPackage{print}{bcpedu-colors}
\else
  \PassOptionsToPackage{digital}{bcpedu-colors}
\fi

\RequirePackage{bcpedu-colors}
\RequirePackage{bcpedu-fonts}
\RequirePackage{bcpedu-layout}
\RequirePackage{bcpedu-headings}
\RequirePackage{bcpedu-code}
\RequirePackage{bcpedu-callouts}
\RequirePackage{bcpedu-crossref}
\RequirePackage{bcpedu-front}
\RequirePackage{bcpedu-back}

%% ─── KDP PDF/X option (placeholder for future use) ───────────────────────────
\if@bcpkdp
  %% TODO: \RequirePackage{pdfx} with PDF/X-1a profile when publishing decision is made
  \ClassWarning{bcpedu}{KDP/PDF-X mode is reserved for future use. No special processing applied yet.}
\fi

%% ─── PDF metadata (set after \begin{document} once metadata commands are set) ─
\AtBeginDocument{%
  \hypersetup{%
    pdftitle    = {\@booktitle\ifx\@booksubtitle\empty\else: \@booksubtitle\fi},
    pdfauthor   = {\@bookauthor},
    pdfsubject  = {\@booksubject},
    pdfkeywords = {\@bookseries, \@booksubject},
    pdfproducer = {BCP Education / XeLaTeX},
    pdfcreator  = {bcpedu.cls v1.0},
  }%
}

%% ─── Useful general-purpose packages ─────────────────────────────────────────
\RequirePackage{graphicx}          % \includegraphics
\RequirePackage{svg}               % \includesvg (requires --shell-escape + Inkscape)
\RequirePackage{float}             % [H] figure placement
\RequirePackage{wrapfig}           % text-wrapping figures
\RequirePackage{subcaption}        % subfigures
\RequirePackage{tikz}              % ghost numbers, title page decorations
\usetikzlibrary{calc}             % coordinate arithmetic for TikZ nodes
\RequirePackage{booktabs}          % \toprule, \midrule, \bottomrule
\RequirePackage{longtable}         % tables spanning multiple pages
\RequirePackage{multirow}          % multirow table cells
\RequirePackage{array}             % extended column specs
\RequirePackage{tabularx}          % auto-width table columns
\RequirePackage{enumitem}          % list spacing control
\RequirePackage{xspace}            % smart trailing space in macros
\RequirePackage{calc}              % length arithmetic
\RequirePackage{ragged2e}          % \RaggedRight in boxes
\RequirePackage{parskip}           % paragraph spacing instead of indent
\RequirePackage{needspace}         % prevent widow section headings
\RequirePackage{emptypage}         % suppress headers/footers on blank pages

%% ─── Adjust list spacing for compactness ─────────────────────────────────────
\setlist{nosep, leftmargin=*, topsep=4pt}
%% Gold filled square bullets — matches business plan editorial style
\setlist[itemize]{label=\raisebox{0.18em}{\textcolor{bcpAccent}{\rule{0.36em}{0.36em}}}}
\setlist[enumerate]{label=\textcolor{bcpAccent}{\arabic*.}}

%% ─── Figure and table caption styling ────────────────────────────────────────
\RequirePackage[
  font={small,sf},
  labelfont={bf,color=bcpAccent},
  labelsep=period,
  format=hang,
  width=0.92\textwidth,
]{caption}

%% ─── Default SVG search path (books place SVGs in assets/) ───────────────────
\svgpath{{assets/}{../assets/}{../../assets/}}

%% ─── Convenience: \bcpversion, \bcpauthor for use in document body ───────────
\newcommand{\bcptitle}{\@booktitle\xspace}
\newcommand{\bcpauthor}{\@bookauthor\xspace}
\newcommand{\bcpedition}{\@bookedition\xspace}

\endinput
