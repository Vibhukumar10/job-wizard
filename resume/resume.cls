%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% RESUME CLASS FILE - ATS-OPTIMIZED BUILD
% Original: Medium Length Professional CV (v0.9)
% Changes are marked with "% ATS:" so you can see exactly what was modified.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\ProvidesClass{resume}[2026/01/01 v2.0 ATS-friendly resume class]

% ATS: 11pt base keeps body text at a readable ~10.3pt after Helvetica scaling.
% Use "a4paper" instead of "letterpaper" if you apply mostly in India/EU.
\LoadClass[11pt,letterpaper]{article}

%----------------------------------------------------------------------------------------
% ATS: TEXT-LAYER / UNICODE SETUP  (the single most important block in this file)
%----------------------------------------------------------------------------------------
\usepackage[utf8]{inputenc}   % ATS: UTF-8 source
\usepackage[T1]{fontenc}      % ATS: 8-bit font encoding -> correct glyph->char mapping
\usepackage{cmap}             % ATS: emits CMap tables so PDF text is copy/paste-able
\usepackage{textcomp}         % ATS: proper text symbols (bullet, dash) instead of math glyphs

% ATS: Forces pdfTeX to write a ToUnicode map for EVERY glyph. Without this,
% bullets and symbols are extracted as blanks or garbage by resume parsers.
\input{glyphtounicode}
\pdfgentounicode=1

% ATS: Helvetica/Arial clone (Nimbus Sans). Arial & Helvetica are the safest,
% most universally supported resume fonts for both ATS parsing and human review.
% Alternatives (uncomment ONE if you prefer a serif look; both are ATS-safe):
%   \usepackage{charter}                                  % Bitstream Charter
%   \usepackage{mathptmx}                                 % Times New Roman clone
\usepackage[scaled=0.92]{helvet}
\renewcommand{\familydefault}{\sfdefault}

% ATS: Kill ligatures. "fi", "fl", "ffi" ligatures are single glyphs and many
% parsers drop or mangle them -> "configuration" becomes "con guration".
\usepackage{microtype}
\DisableLigatures{encoding = *, family = *}

% ATS: Kill hyphenation. Line-break hyphens split keywords across lines
% ("connection pool-ing", "authenti-cation") and destroy keyword matches.
\usepackage[none]{hyphenat}
\hyphenpenalty=10000
\exhyphenpenalty=10000
\tolerance=9999
\emergencystretch=3em
\raggedright                  % ATS: no forced justification -> no weird word spacing

\usepackage[parfill]{parskip} % Remove paragraph indentation
\setlength{\parskip}{2pt}     % ATS: consistent, tight block spacing
\usepackage{array}
\usepackage{ifthen}

\usepackage{hyperref}
% ATS: hidelinks-style config. Coloured/boxed links add no parsing value and the
% visible link TEXT is what gets extracted, so links are kept but rendered dark.
\hypersetup{
    colorlinks=true,
    linkcolor=black,
    filecolor=black,
    citecolor=black,
    urlcolor=black,
    pdfborder={0 0 0},
    pdftitle={Vibhu Kumar Singh - Resume},   % ATS: PDF metadata (some parsers read it)
    pdfauthor={Vibhu Kumar Singh},
    pdfsubject={Software Engineer Resume},
    pdfkeywords={Java, Spring Boot, Helidon, Microservices, REST API, Kubernetes,
                 Terraform, Ansible, FluxCD, OCI, AWS, Docker, Backend Engineer},
    pdflang={en-US},
    bookmarks=false
}

\pagestyle{empty} % ATS: no headers/footers (most parsers discard header/footer zones)

%----------------------------------------------------------------------------------------
%	HEADINGS COMMANDS: Commands for printing name and address
%----------------------------------------------------------------------------------------

\def \name#1{\def\@name{#1}}
\def \@name {}

% ATS: was $\diamond$ (a MATH glyph, extracted as U+22C4 or dropped entirely).
% A plain pipe is ASCII and is the most parser-friendly contact separator.
\def \addressSep {\textbar}

\let \@addressone \relax
\let \@addresstwo \relax
\let \@addressthree \relax

\def \address #1{
  \@ifundefined{@addresstwo}{
    \def \@addresstwo {#1}
  }{
  \@ifundefined{@addressthree}{
  \def \@addressthree {#1}
  }{
     \def \@addressone {#1}
  }}
}

% ATS: contact lines centred under the name. Each line still extracts as one
% contiguous string, which is what the parser reads - visual alignment does not
% affect extraction as long as there is no large horizontal gap inside the line.
\def \printaddress #1{
  \begingroup
    \def \\ {\ \addressSep\ }
    \centerline{#1}
  \endgroup
  \par
  \addressskip
}

% ATS: \MakeUppercase removed. Name parsers match "Firstname Lastname" far more
% reliably than "FIRSTNAME LASTNAME" (all-caps is often read as an acronym).
% ATS: name is CENTRED, Title Case, alone on the first line and is the first text
% object in the PDF reading order. \centerline is used deliberately (not
% \centering) so that \\ keeps working as a separator in the contact lines below.
\def \printname {
  \begingroup
    \centerline{{\namesize\bfseries \@name}}
    \nameskip
  \endgroup
  \par
}

%----------------------------------------------------------------------------------------
%	PRINT THE HEADING LINES
%----------------------------------------------------------------------------------------

\let\ori@document=\document
\renewcommand{\document}{
  \ori@document
  \printname
  \@ifundefined{@addressone}{}{\printaddress{\@addressone}}
  \@ifundefined{@addresstwo}{}{\printaddress{\@addresstwo}}
  \@ifundefined{@addressthree}{}{\printaddress{\@addressthree}}
}

%----------------------------------------------------------------------------------------
%	SECTION FORMATTING
%----------------------------------------------------------------------------------------

% ATS: Section titles stay left-aligned, bold, uppercase, on their own line,
% followed by a plain horizontal rule (a vector line, not a graphic - safe).
% Heading block: space ABOVE the title, a small gap between title and rule,
% then a real breathing gap BELOW the rule before the section content starts.
\newenvironment{rSection}[1]{
  \sectionskip
  {\bfseries\large\MakeUppercase{#1}}
  \sectionlineskip
  \hrule height 0.8pt
  \vspace{\sectionbodyskip}   % <-- padding after every section heading
  \begin{list}{}{
    \setlength{\leftmargin}{0em}
  }
  \item[]
}{
  \end{list}
  \vspace{-0.1em}
}

%----------------------------------------------------------------------------------------
%	WORK EXPERIENCE FORMATTING
%----------------------------------------------------------------------------------------

\newenvironment{rSubsection}[4]{
 {\bfseries #1} \hfill {#2}
 \ifthenelse{\equal{#3}{}}{}{
  \\
  {\em #3} \hfill {\em #4}
  }\smallskip
  % ATS: was $\cdot$ (math glyph, no Unicode mapping). \textbullet maps to U+2022.
  \begin{list}{\textbullet}{\leftmargin=1em}
   \itemsep -0.5em \vspace{-0.5em}
  }{
  \end{list}
  \vspace{-0.5em}
}

% Whitespace tuning
\def\namesize{\LARGE}          % ATS: ~20pt name
\def\addressskip{\vspace{2pt}}
\def\sectionlineskip{\vspace{3pt}}          % title -> rule gap
\def\nameskip{\vspace{3pt}}
\def\sectionskip{\vspace{8pt}}              % space ABOVE each section heading
\newlength{\sectionbodyskip}
\setlength{\sectionbodyskip}{7pt}            % PADDING AFTER each heading rule
                                             % (raise to 9pt-10pt for more air)
                               % heading is not glued to the previous block