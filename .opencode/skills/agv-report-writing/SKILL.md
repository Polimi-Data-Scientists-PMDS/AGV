---
name: agv-report-writing
description: AGV report, main.tex, controllers.tex, old_controller.tex, logger.tex, or webapp.tex writing. Use when drafting or revising the AGV LaTeX report in the established technical project-report style.
---

# AGV Report Writing

Use this skill only when writing or revising the LaTeX report in `AGV_Report/`. 

## Scope

- `AGV_Report/main.tex` owns document configuration and imports the four report sections.
- `AGV_Report/controllers.tex` describes the current controller.
- `AGV_Report/old_controller.tex` records predecessor implementations and the decisions they informed.
- `AGV_Report/logger.tex` documents the logging service, persistence and telemetry.
- `AGV_Report/webapp.tex` documents the monitoring web application.
- Read the relevant implementation and project documentation before making factual claims. In particular, consult `README.md`, `docs/`, the relevant controller modules, `logging/` and `web-app/`.

## Writing Style

Write in formal but readable technical English. The desired voice is explanatory and implementation-aware, not promotional or excessively academic.

- Open a section or subsection by stating its role in the overall system and why it matters.
- Use paragraphs of roughly 3--6 sentences. Each paragraph should develop one idea: motivation, mechanism, consequence or limitation.
- Explain concepts before describing implementation details. Then connect the design to concrete modules, classes, functions, data flows or configuration files when this improves traceability.
- Prefer precise active statements such as "The controller queries the lidar interface before selecting a local route." Use passive voice only when it makes the subject genuinely unimportant.
- Use a measured technical vocabulary: "robust", "consistent", "computational cost", "failure mode", "trade-off", "limitation", "pipeline", "state estimate" and "dynamic obstacle" are appropriate when supported by evidence.
- Qualify conclusions. State assumptions, observed behaviour and limitations explicitly; do not claim reliability, performance or correctness without evidence from the repository, tests or simulation results.
- Use short lead-in sentences before lists, figures, tables and code listings. Every figure and table must be introduced in the prose and have a descriptive caption.
- Use `\texttt{...}` for code identifiers and `\textbf{...}` sparingly for a key technical term on first introduction.
- Use `Section~\ref{...}` for internal references and `\cref{...}` when referring to labelled figures, tables or listings.

## Mathematical Formalism

Keep mathematical formalism lighter than a numerical-methods report.

- Prefer prose, diagrams, pseudocode, tables and concrete examples for software architecture and algorithmic behaviour.
- Include an equation only when it defines a quantity used in the evaluation, a control rule or an algorithmic invariant that cannot be explained more clearly in words.
- When an equation is necessary, define every symbol immediately and explain its engineering meaning in the following sentence.
- Do not derive standard algorithms or include formal proofs unless the report task explicitly requires them.

## LaTeX Practice

- Preserve the four-file structure and do not move content into `main.tex`.
- Use `\section`, `\subsection` and `\subsubsection` consistently; add a `\label` immediately after every heading that will be cross-referenced.
- Do not use manual line breaks (`\\`) to separate ordinary paragraphs. Leave a blank line in the source instead.
- Escape LaTeX-sensitive characters in prose, including `_`, `%`, `&`, `#` and `{}`.
- Do not invent citations, measurements, completed features or test results. Add a `TODO` comment if essential evidence is unavailable.

## Revision Checklist

Before finishing, confirm that the prose is factual, each paragraph has a clear purpose, code references match the repository, cross-references resolve, and no claim is stronger than the available evidence.
