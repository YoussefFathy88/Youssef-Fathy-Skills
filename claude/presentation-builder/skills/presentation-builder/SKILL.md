---
name: "presentation-builder"
description: "Guided deck creation: set up or reuse a design system, gather goal and audience context, confirm an outline, build the slides, then guide edits. Use for any presentation request."
---

# Presentation Builder

Flow: Detect tools -> Design system -> Context -> Content intake -> Outline -> Build -> Hand-off.
Never skip a phase. Never build slides before the content is received and the outline is approved.

## Ground rules
- Ask questions in batches, never one at a time across many turns. Use AskUserQuestion when available (max 4 questions per call); otherwise one numbered message.
- Give a sensible default with every question so the user can just confirm. Content is the exception: there is no default for content.
- Skip anything already answered in the conversation or in attached files.
- Content comes from the user. Never build a deck from general knowledge alone.
- Use only facts from the user's sources. Mark gaps as [TODO], never invent numbers, quotes, or citations.
- Keep messages short and plain.

## Phase 0: Detect tools
1. List the available Artifact types.
   - If Slides and Design System types exist: use the artifact path.
   - If not: fallback path. Build a .pptx with the pptx skill, and save the design system as a design-system.md file the user can reuse.
2. List existing Design System artifacts.
   - If one is the default or the user names one: read it, confirm "Use <name>?", then go to Phase 2.
   - If none: go to Phase 1.

## Phase 1: Build the design system (only if none exists)
First ask: "Do you have brand assets (logo, colors, fonts, an old deck, screenshots)?"
- Yes: extract colors, fonts, and style from them. Show what you found and ask only about gaps.
- No: run the batches below.

Batch 1, Identity
- Brand or person name
- 3 personality words (e.g. bold, calm, technical)
- Main audience
- Light, dark, or both

Batch 2, Color
- Primary color (hex or "suggest")
- Accent color
- Colors to avoid

Batch 3, Typography
- Heading font and body font (or "suggest")
- Languages and scripts needed. If Arabic or another RTL script: require fonts that support it and RTL layout

Batch 4, Visual language
- Shapes: rounded or sharp
- Imagery: photos, illustrations, icons, or minimal
- Chart and diagram style
- Logo placement
- Text density: minimal, balanced, or dense

If starting from scratch, propose 2 or 3 short directions and let the user pick.

Then build the Design System artifact with:
- Colors with roles (background, text, primary, accent, muted) and readable contrast
- Type scale (title, heading, body, caption, code)
- Spacing and radius
- Slide components: title, section divider, content, two-column, chart, quote, code, closing
- Short do and don't list

Show it, iterate until approved, save it, and offer to make it the default.
When the user later gives a lasting style rule (e.g. "never use a green background"), fix the slide AND add the rule to the design system.

## Phase 2: Presentation context
Batch A, Goal
- Type: academic, conference talk, workshop or training, pitch, business update, sales, other
- The one idea the audience must remember
- The action you want from them

Batch B, Audience and setting
- Who they are and their expertise level
- Presented live or read alone (changes text density)
- Duration or slide count
- Language

Batch C, Scope
- Must-include sections
- Anything to avoid
- Speaker notes needed?

Batch D, Style for this deck (within the design system)
- Density: minimal, balanced, dense
- Visuals: diagrams, charts, code, images
- Tone: formal, friendly, playful
- Do not promise animations unless the output format supports them

Default structure by goal:
- Academic: problem, background, method, results, limitations, references
- Conference talk: hook, story, one idea per slide, minimal text, strong close
- Workshop or training: objectives, concept, example, exercise, recap
- Pitch: problem, solution, market, traction, model, team, ask
- Business update: summary first, metrics, risks, next steps
- Sales: pain, solution, proof, pricing, call to action

## Phase 2.5: Content intake (mandatory)
1. Ask for ALL content in one message:
   "Share everything you have for this deck: docs, notes, outlines, data, links, old decks, transcripts, screenshots. Attach files or paste text. Rough notes are fine."
2. Wait for the content. Do not offer a default and do not move on without it.
3. Read every source fully. Then reply with:
   - What you found: 3 to 6 short bullets of the key points
   - Gaps: what the goal or outline needs but the sources don't cover
   - Conflicts: anything that disagrees between sources
   Ask the user to fill the gaps or confirm they stay as [TODO].
4. If the user has no content, offer these choices and let them pick:
   - Give short bullet notes now (recommended)
   - Claude researches the topic on the web, with every fact cited and labeled
   - Claude writes a draft marked [DRAFT] on every slide, for the user to correct
   Never pick one for the user.

## Phase 3: Readiness check and outline
Before building, confirm all are known: design system, goal, audience, length, language, and content received and read. Ask for anything missing.
Then show a slide-by-slide outline: title, key message, planned visual, and the source each slide comes from.
Any slide with no source is listed as a gap. Wait for approval.

## Phase 4: Build
- Artifact path: create the deck from the Slides type with the chosen design system and follow the type's own instructions.
- Fallback path: load the pptx skill and build a .pptx that follows design-system.md.
- Checks: one message per slide, no text overflow, readable contrast, correct RTL for Arabic, every fact traceable to the user's sources.
- Example or mock data (names, numbers in UI mockups) must be labeled "Example" on the slide and listed in the hand-off.

## Phase 5: Hand-off
Give a 2-line summary of what was built, then guide the user:
- Small fixes, do it yourself in the editor: typos, a word or number, swapping an image, reordering a slide.
- Bigger changes, ask Claude: restructuring, new sections, a new visual style, new or rebuilt charts, adapting to a different audience or length.
- Export: download as .pptx or PDF when needed.
- List any [TODO] gaps and example data still on the slides.
- Suggest one concrete next step (e.g. add speaker notes, rehearse timing).