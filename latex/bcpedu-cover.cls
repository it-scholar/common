%% =============================================================================
%% bcpedu-cover.cls — BCP Education Book Cover Class
%% =============================================================================
%% Generates a book's dark, minimalist "night" cover from the same kind of
%% metadata each book already sets in config/metadata.tex. Two modes:
%%
%%   \documentclass{bcpedu-cover}         % front cover only, no bleed (digital/thumbnail)
%%   \documentclass[wrap]{bcpedu-cover}   % back + spine + front, with bleed (print)
%%
%% A book's cover/cover.tex only needs to set metadata commands and call
%% \bcpRenderCover — see courses/kubernetes/books/kubernetes-for-developers/
%% cover/cover.tex for the reference example.
%%
%% Required engine: XeLaTeX or LuaLaTeX (same as bcpedu.cls)
%% =============================================================================

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{bcpedu-cover}[2026/09/20 v1.0 BCP Education Cover Class]

\RequirePackage{ifxetex,ifluatex}
\newif\if@bcpcoverxeluatex
\ifxetex\@bcpcoverxeluatextrue\fi
\ifluatex\@bcpcoverxeluatextrue\fi
\if@bcpcoverxeluatex\else
  \ClassError{bcpedu-cover}{%
    This class requires XeLaTeX or LuaLaTeX.\MessageBreak
    Compile with: xelatex --shell-escape cover.tex
  }{Switch your compiler.}
\fi

%% ─── Class options ───────────────────────────────────────────────────────────
%% front (default): single front-cover panel, trim size only, no bleed.
%% wrap: back + spine + front in one canvas, with bleed, for print.
\newif\if@bcpcoverwrap \@bcpcoverwrapfalse
\DeclareOption{front}{\@bcpcoverwrapfalse}
\DeclareOption{wrap}{\@bcpcoverwraptrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

\LoadClass{article}

%% ─── Core utilities ──────────────────────────────────────────────────────────
\RequirePackage{etoolbox}
\RequirePackage{xparse}
\RequirePackage{graphicx}
\RequirePackage{enumitem}
\RequirePackage{tikz}
\usetikzlibrary{calc}

%% Covers are always full color, regardless of the interior digital/print mode.
\PassOptionsToPackage{digital}{bcpedu-colors}
\RequirePackage{bcpedu-colors}
\RequirePackage{bcpedu-fonts}

%% ─── Book identity metadata ───────────────────────────────────────────────────
%% Mirrors the commands in bcpedu.cls (kept in sync by convention, not by
%% \input-ing config/metadata.tex directly - that file also pulls in
%% \addbibresource/\input{back/glossary}, which the cover has no use for).
%% Set these again in cover.tex, matching the book's own config/metadata.tex.
\newcommand{\@booktitle}{Untitled Book}
\newcommand{\@booksubtitle}{}
\newcommand{\@bookauthor}{BCP Education}
\newcommand{\@bookversion}{1.0}
\newcommand{\@bookedition}{First Edition}
\newcommand{\@bookseries}{BCP Education}

\NewDocumentCommand{\booktitle}     {m}{\renewcommand{\@booktitle}{#1}}
\NewDocumentCommand{\booksubtitle}  {m}{\renewcommand{\@booksubtitle}{#1}}
\NewDocumentCommand{\bookauthor}    {m}{\renewcommand{\@bookauthor}{#1}}
\NewDocumentCommand{\bookversion}   {m}{\renewcommand{\@bookversion}{#1}}
\NewDocumentCommand{\bookedition}   {m}{\renewcommand{\@bookedition}{#1}}
\NewDocumentCommand{\bookseries}    {m}{\renewcommand{\@bookseries}{#1}}
%% Per-book accent color override, e.g. \bookaccentcolor{8B0000} (hex, no #).
\NewDocumentCommand{\bookaccentcolor}{m}{\definecolor{bcpAccent}{HTML}{#1}}

%% ─── Cover-only content metadata ──────────────────────────────────────────────
\newcommand{\@bookblurb}{}
\NewDocumentCommand{\bookblurb}{m}{\renewcommand{\@bookblurb}{#1}}

%% \booktakeaways{\item One thing\item Another thing} - back-cover bullet list.
%% Left empty by default: the "What You'll Learn" block is skipped entirely.
\newcommand{\@booktakeaways}{}
\NewDocumentCommand{\booktakeaways}{m}{\renewcommand{\@booktakeaways}{#1}}

%% Optional per-book hooks - both OFF by default (pure typographic/geometric cover).
\newcommand{\@coverimagepath}{}
\NewDocumentCommand{\coverimage}{m}{\renewcommand{\@coverimagepath}{#1}}

\newcommand{\@coverbadgepath}{}
\NewDocumentCommand{\coverbadge}{m}{\renewcommand{\@coverbadgepath}{#1}}

%% ─── Physical dimensions ──────────────────────────────────────────────────────
%% Trim matches the interior book (bcpedu-layout.sty): 7in x 10in.
\newlength{\bcptrimw}   \setlength{\bcptrimw}{7in}
\newlength{\bcptrimh}   \setlength{\bcptrimh}{10in}
\newlength{\bcpbleed}   \setlength{\bcpbleed}{0.125in}   % standard KDP-style bleed

%% Spine width - normally injected by the Taskfile build (from the real
%% interior page count) as a plain macro \bcpinjectedspinewidth defined via
%% -pretex, BEFORE \documentclass runs (so it's available here, at class-load
%% time, early enough to still influence the physical page size below - a
%% runtime \spinewidth{...} call from inside cover.tex is too late for that,
%% since geometry's page size can only be set while the package loads, not
%% via a later \geometry/\newgeometry call).  Default fallback (0.4in) keeps
%% a standalone wrap-mode build working without any injected value.
\newlength{\bcpspinewidth}
\setlength{\bcpspinewidth}{0.4in}
\newcommand{\spinewidth}[1]{\setlength{\bcpspinewidth}{#1}}
\@ifundefined{bcpinjectedspinewidth}{}{\spinewidth{\bcpinjectedspinewidth}}
%% Below this, rotated spine text would be unreadably cramped - accent bar only.
\newlength{\bcpspinemin}
\setlength{\bcpspinemin}{0.32in}

%% Radius of the default/coverimage circular emblem on the front panel.
\newlength{\bcpemblemr}
\setlength{\bcpemblemr}{1.45in}

\newlength{\bcpwrapwidth}
\newlength{\bcpwrapheight}
%% Distance from the physical page's top/bottom edge down to the trim edge -
%% 0 in front mode (page = trim, no bleed), \bcpbleed in wrap mode. All fixed-
%% inch content positions below are measured from the TRIM edge, so every
%% absolute yshift adds/subtracts this to stay aligned once bleed is trimmed.
\newlength{\bcptopbleed}

%% geometry's physical paper size can only be set while the package loads
%% (a later \geometry/\newgeometry call only affects margins), so compute the
%% final canvas size here and pass it straight in as package options.
\if@bcpcoverwrap
  \setlength{\bcpwrapwidth}{\bcptrimw}
  \addtolength{\bcpwrapwidth}{\bcptrimw}
  \addtolength{\bcpwrapwidth}{\bcpspinewidth}
  \addtolength{\bcpwrapwidth}{\bcpbleed}
  \addtolength{\bcpwrapwidth}{\bcpbleed}
  \setlength{\bcpwrapheight}{\bcptrimh}
  \addtolength{\bcpwrapheight}{\bcpbleed}
  \addtolength{\bcpwrapheight}{\bcpbleed}
  \setlength{\bcptopbleed}{\bcpbleed}
  \RequirePackage[paperwidth=\the\bcpwrapwidth, paperheight=\the\bcpwrapheight, margin=0pt]{geometry}
\else
  \setlength{\bcpwrapwidth}{\bcptrimw}
  \setlength{\bcpwrapheight}{\bcptrimh}
  \setlength{\bcptopbleed}{0pt}
  \RequirePackage[paperwidth=\the\bcptrimw, paperheight=\the\bcptrimh, margin=0pt]{geometry}
\fi

\AtBeginDocument{\pagestyle{empty}}

%% ─── Grain texture ────────────────────────────────────────────────────────────
%% Sparse, low-opacity random dots across the full canvas - a cheap, asset-free
%% stand-in for a paper/film grain overlay. Fixed seed so builds are reproducible.
\newcommand{\bcpDrawGrain}{%
  \pgfmathsetseed{20260714}%
  \foreach \bcpi in {1,...,450} {%
    \pgfmathsetmacro{\bcprx}{rnd}%
    \pgfmathsetmacro{\bcpry}{rnd}%
    \pgfmathsetmacro{\bcpro}{0.02+0.05*rnd}%
    \pgfmathsetmacro{\bcprr}{0.3+0.5*rnd}%
    \fill[bcpCoverText, opacity=\bcpro]
      ([xshift=\bcprx*\paperwidth, yshift=-\bcpry*\paperheight]current page.north west)
      circle (\bcprr pt);
  }%
}

%% ─── Emblem + mark helpers (shared by front/spine) ────────────────────────────
%% Circular emblem centered at (#1,#2): default is a spare line-art mark (ring,
%% a small "moon" dot, a few star dots); if \coverimage is set, that graphic is
%% clipped into the same circle instead - so book-specific art always reads as
%% part of the same family device rather than a full-bleed photo.
\newcommand{\bcpDrawEmblem}[2]{%
  \ifdefempty{\@coverimagepath}{%
    \draw[bcpCoverTextMuted, line width=0.9pt]
      ([xshift=#1, yshift=#2]current page.north west) circle (\bcpemblemr);
    \fill[bcpAccent]
      ([xshift=#1+0.55*\bcpemblemr, yshift=#2+0.6*\bcpemblemr]current page.north west) circle (0.14in);
    \foreach \bcpsx/\bcpsy in {-0.5/0.68, -0.12/0.88, 0.35/0.55} {%
      \fill[bcpCoverTextMuted, opacity=0.75]
        ([xshift=#1+\bcpsx*\bcpemblemr, yshift=#2+\bcpsy*\bcpemblemr]current page.north west) circle (0.8pt);
    }%
  }{%
    \begin{scope}
      \clip ([xshift=#1, yshift=#2]current page.north west) circle (\bcpemblemr);
      \node[anchor=center, inner sep=0pt] at ([xshift=#1, yshift=#2]current page.north west)
        {\includegraphics[width=2\bcpemblemr, height=2\bcpemblemr]{\@coverimagepath}};
    \end{scope}
    \draw[bcpCoverTextMuted, line width=0.9pt]
      ([xshift=#1, yshift=#2]current page.north west) circle (\bcpemblemr);
  }%
}

%% Small centered plus-mark accent at (#1,#2) - the one recurring ornament tying
%% every panel together instead of solid color blocks.
\newcommand{\bcpDrawMark}[2]{%
  \draw[bcpAccent, line width=0.9pt]
    ([xshift=#1-0.08in, yshift=#2]current page.north west) --
    ([xshift=#1+0.08in, yshift=#2]current page.north west);
  \draw[bcpAccent, line width=0.9pt]
    ([xshift=#1, yshift=#2-0.08in]current page.north west) --
    ([xshift=#1, yshift=#2+0.08in]current page.north west);
}

%% ─── Front cover panel ────────────────────────────────────────────────────────
%% #1 = left-edge x-offset of this panel, #2 = panel width.
%% Minimal, center-composed layout: series imprint, a circular emblem (default
%% line-art mark, or a book-specific \coverimage clipped into the same circle),
%% tracked-out title, then a small mark, subtitle, and author/edition footer -
%% everything centered, all fixed y-offsets measured from the trim edge.
\newcommand{\bcpDrawFrontContent}[2]{%
  \node[anchor=north, xshift=#1+0.5*#2, yshift=-\bcptopbleed-0.85in, inner sep=0pt] at (current page.north west)
    {\fontsize{7.5pt}{9pt}\selectfont\sffamily\addfontfeature{LetterSpace=8}\color{bcpCoverTextMuted}\MakeUppercase{\@bookseries}};
  \draw[bcpCoverTextMuted, line width=0.5pt]
    ([xshift=#1+0.5*#2-0.45in, yshift=-\bcptopbleed-1.08in]current page.north west) --
    ([xshift=#1+0.5*#2+0.45in, yshift=-\bcptopbleed-1.08in]current page.north west);
  \bcpDrawEmblem{#1+0.5*#2}{-\bcptopbleed-3.15in}
  \ifdefempty{\@coverbadgepath}{}{%
    \node[anchor=north east, xshift=#1+#2-0.55in, yshift=-\bcptopbleed-0.55in, inner sep=0pt] at (current page.north west)
      {\includegraphics[width=0.75in]{\@coverbadgepath}};
  }%
  \hyphenpenalty=10000\relax\exhyphenpenalty=10000\relax
  \node[anchor=north, xshift=#1+0.5*#2, yshift=-\bcptopbleed-5.05in, text width=#2-1.3in, align=center, inner sep=0pt] at (current page.north west)
    {\fontsize{27pt}{33pt}\selectfont\sffamily\bfseries\addfontfeature{LetterSpace=2}\color{bcpCoverText}\MakeUppercase{\@booktitle}};
  \hyphenpenalty=50\relax\exhyphenpenalty=50\relax
  \bcpDrawMark{#1+0.5*#2}{-\bcptopbleed-6.65in}
  \ifdefempty{\@booksubtitle}{}{%
    \node[anchor=north, xshift=#1+0.5*#2, yshift=-\bcptopbleed-6.95in, text width=#2-1.8in, align=center, inner sep=0pt] at (current page.north west)
      {\fontsize{11.5pt}{16pt}\selectfont\sffamily\addfontfeature{LetterSpace=1}\color{bcpCoverTextMuted}\@booksubtitle};
  }%
  \draw[bcpCoverTextMuted, line width=0.5pt]
    ([xshift=#1+0.5*#2-0.7in, yshift=\bcptopbleed+1.32in]current page.south west) --
    ([xshift=#1+0.5*#2+0.7in, yshift=\bcptopbleed+1.32in]current page.south west);
  \node[anchor=south, xshift=#1+0.5*#2, yshift=\bcptopbleed+1.0in, inner sep=0pt] at (current page.south west)
    {\fontsize{9.5pt}{12pt}\selectfont\sffamily\addfontfeature{LetterSpace=4}\color{bcpCoverText}\MakeUppercase{\@bookauthor}};
  \node[anchor=south, xshift=#1+0.5*#2, yshift=\bcptopbleed+0.72in, inner sep=0pt] at (current page.south west)
    {\fontsize{8.5pt}{11pt}\selectfont\sffamily\color{bcpCoverTextMuted}\@bookedition\enspace\textperiodcentered\enspace Version~\@bookversion};
}

%% ─── Back cover panel (wrap mode only) ────────────────────────────────────────
\newcommand{\bcpDrawBackContent}[2]{%
  \node[anchor=north, xshift=#1+0.5*#2, yshift=-\bcptopbleed-0.85in, inner sep=0pt] at (current page.north west)
    {\fontsize{7.5pt}{9pt}\selectfont\sffamily\addfontfeature{LetterSpace=8}\color{bcpCoverTextMuted}\MakeUppercase{\@bookseries}};
  \draw[bcpCoverTextMuted, line width=0.5pt]
    ([xshift=#1+0.5*#2-0.45in, yshift=-\bcptopbleed-1.08in]current page.north west) --
    ([xshift=#1+0.5*#2+0.45in, yshift=-\bcptopbleed-1.08in]current page.north west);
  \node[anchor=north west, xshift=#1+0.55in, yshift=-\bcptopbleed-1.85in, text width=#2-1.1in, align=left, inner sep=0pt] at (current page.north west)
    {\fontsize{11pt}{15.5pt}\selectfont\sffamily\color{bcpCoverText}\@bookblurb};
  \ifdefempty{\@booktakeaways}{}{%
    \node[anchor=north west, xshift=#1+0.55in, yshift=-\bcptopbleed-5.6in, text width=#2-1.1in, align=left, inner sep=0pt] at (current page.north west)
      {%
        {\fontsize{9.5pt}{12pt}\selectfont\sffamily\addfontfeature{LetterSpace=5}\color{bcpAccent}\MakeUppercase{What You'll Learn}}\\[7pt]
        \begin{itemize}[nosep, leftmargin=1.2em, itemsep=3pt,
            label=\textcolor{bcpCoverTextMuted}{\rule{0.28em}{0.5pt}}]
          \fontsize{9.5pt}{13pt}\selectfont\sffamily\color{bcpCoverText}
          \@booktakeaways
        \end{itemize}%
      };
  }%
  \draw[bcpCoverTextMuted, line width=0.6pt]
    ([xshift=#1+#2-2.3in, yshift=-\paperheight+\bcptopbleed+1.35in]current page.north west)
    rectangle
    ([xshift=#1+#2-0.35in, yshift=-\paperheight+\bcptopbleed+0.35in]current page.north west);
  \node[anchor=center, xshift=#1+#2-1.325in, yshift=-\paperheight+\bcptopbleed+0.85in, inner sep=0pt] at (current page.north west)
    {\fontsize{7.5pt}{9pt}\selectfont\sffamily\color{bcpDarkGray}ISBN barcode placeholder};
  \draw[bcpCoverTextMuted, line width=0.5pt]
    ([xshift=#1+0.55in, yshift=\bcptopbleed+0.95in]current page.south west) --
    ([xshift=#1+#2-0.55in, yshift=\bcptopbleed+0.95in]current page.south west);
  \node[anchor=south west, xshift=#1+0.55in, yshift=\bcptopbleed+0.6in, inner sep=0pt] at (current page.south west)
    {\fontsize{9pt}{11pt}\selectfont\sffamily\color{bcpCoverTextMuted}\@bookseries\ \textperiodcentered\ \@bookedition};
}

%% ─── Spine panel (wrap mode only) ─────────────────────────────────────────────
\newcommand{\bcpDrawSpineContent}[2]{%
  \draw[bcpCoverTextMuted, line width=0.6pt]
    ([xshift=#1+0.2*#2, yshift=-\bcptopbleed-0.62in]current page.north west) --
    ([xshift=#1+0.8*#2, yshift=-\bcptopbleed-0.62in]current page.north west);
  \ifdim\bcpspinewidth<\bcpspinemin\relax
    %% Too narrow for readable rotated text - the thin rule above is enough.
  \else
    \node[anchor=center, xshift=#1+0.5*#2, yshift=-0.5\paperheight, rotate=90, inner sep=0pt] at (current page.north west)
      {%
        \begin{minipage}{5in}\centering
          {\fontsize{7.5pt}{9pt}\selectfont\sffamily\addfontfeature{LetterSpace=6}\color{bcpCoverTextMuted}\MakeUppercase{\@bookseries}}\\[7pt]
          {\fontsize{14pt}{17pt}\selectfont\sffamily\bfseries\addfontfeature{LetterSpace=1}\color{bcpCoverText}\MakeUppercase{\@booktitle}}%
          \quad{\textcolor{bcpAccent}{\rule{0.4em}{0.4em}}}\quad
          {\fontsize{9.5pt}{12pt}\selectfont\sffamily\addfontfeature{LetterSpace=2}\color{bcpCoverTextMuted}\MakeUppercase{\@bookauthor}}%
        \end{minipage}%
      };
  \fi
}

%% ─── Top-level render command ─────────────────────────────────────────────────
%% Call this (and only this) inside cover.tex's \begin{document}...\end{document}.
\newcommand{\bcpRenderCover}{%
  \thispagestyle{empty}%
  \noindent
  \begin{tikzpicture}[remember picture, overlay]
    \fill[bcpCoverBg] (current page.north west) rectangle (current page.south east);
    \bcpDrawGrain
    \if@bcpcoverwrap
      \bcpDrawBackContent{\bcpbleed}{\bcptrimw}
      \bcpDrawSpineContent{\dimexpr\bcpbleed+\bcptrimw\relax}{\bcpspinewidth}
      \bcpDrawFrontContent{\dimexpr\bcpbleed+\bcptrimw+\bcpspinewidth\relax}{\bcptrimw}
    \else
      \bcpDrawFrontContent{0pt}{\paperwidth}
    \fi
  \end{tikzpicture}%
}

\endinput
