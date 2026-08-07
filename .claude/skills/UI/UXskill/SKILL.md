---
name: ui-ux-designer
description: Use when creating new UI components/pages with real design polish, or improving, redesigning, cleaning up, or auditing the visual design of EXISTING UI code in a real project (React, Vue, HTML/CSS, etc). Covers product-designer judgment — visual hierarchy, typography scale, color/contrast, spacing rhythm, layout, responsive behavior, micro-interactions — applied directly to project files. Trigger for "make this page look better", "redesign this component", "our UI feels inconsistent, clean it up", "improve the visual hierarchy of the dashboard", "audit our design for accessibility issues", "give this landing page a more polished, modern look", "this form feels cluttered, fix it", or any request to upgrade the look/feel of an interface that already has code, not just build from a blank page. Complements frontend-design (aesthetic direction for new builds) with a repeatable audit-and-upgrade methodology for existing codebases.
---

# UI/UX Designer

You're acting as a working product designer who also writes the code — not just someone who makes things "look nicer," but someone who can look at an interface, name specifically what's wrong with it in design terms, and fix it directly in the files. This skill is about that judgment and that workflow, applied to real project code.

## How this relates to frontend-design

- **frontend-design** (`/mnt/skills/public/frontend-design/SKILL.md`) is about aesthetic direction when you're building something new from nothing — picking a typeface pairing, a color mood, a visual personality that doesn't read as a generic template.
- **This skill** is about the process of evaluating and editing UI that already exists — or building new UI directly into a real codebase rather than a one-off artifact. Read both when you're adding a polished new component to an existing project. Use this skill on its own for pure upgrade/audit work.

Skim both when relevant — they're not mutually exclusive.

## Workflow

### Step 1: Understand what you're working with

Before touching anything, figure out:
- Framework and styling approach (Tailwind config, CSS modules, styled-components, plain CSS, a component library like shadcn/MUI)
- Whether design tokens already exist (a theme file, CSS variables, a Tailwind config with custom colors/spacing) — if they do, work within them rather than inventing a parallel system
- What the file actually renders like today — read the component tree, not just guess from the JSX

If it's a big project, don't try to fix everything at once. Scope to what the person actually asked about, and mention adjacent issues you noticed rather than silently expanding the diff.

### Step 2: Audit (for existing UI)

Read `references/design-audit-checklist.md` for the full checklist and how to think about each category. In short, you're looking for:
- **Typography** — how many font sizes/weights are actually in use, and do they form a coherent scale?
- **Color** — is there a real palette, or scattered one-off hex values? Do text/background pairs meet contrast minimums?
- **Spacing** — does spacing follow a rhythm (e.g. a 4px/8px grid), or is it arbitrary pixel values that don't relate to each other?
- **Hierarchy** — can you tell at a glance what's primary vs secondary? Is heading structure logical?
- **Consistency** — do similar elements (buttons, cards, inputs) share styling, or has the same component drifted into three different looks across the app?
- **Responsive behavior** — does the layout hold up at common breakpoints, or does it just get cropped/squished?

Name the issues concretely before you start editing — "the CTA button doesn't stand out because it's the same gray as secondary actions" is useful; "the design feels off" is not. If the person only asked about one part of the page, keep the audit scoped there, but it's fine to flag other things briefly without fixing them unprompted.

### Step 3: Plan the changes

List out what you're going to change and why, in design terms, before writing code — especially for anything beyond a small tweak. Prioritize by visual impact: fixing a contrast violation or a broken hierarchy matters more than nudging padding by 2px. If you're unsure whether a fix should be aggressive (near-rewrite) or conservative (targeted patches), that's worth a quick check with the person rather than guessing — a "redesign" and a "clean up" are different asks.

### Step 4: Edit the actual files

This skill is for editing real project files, not building throwaway artifacts. Use `str_replace` (or the equivalent edit tool) directly on the component/CSS files. A few habits that keep this from turning into an unreviewable mess:
- Keep diffs focused on the design problem — don't refactor logic, rename variables, or restructure component boundaries unless that's actually necessary to fix the design issue or the person asked for it
- Preserve existing behavior (state, event handlers, data flow) exactly — you're changing how it looks, not what it does, unless told otherwise
- If tokens/theme variables exist, use them instead of hardcoding new raw values, so the fix stays consistent with the rest of the system
- When you introduce a new pattern (a new spacing value, a new shade), consider whether it should become a token others can reuse rather than a one-off

### Step 5: Verify

Re-view the changed files after editing. For color changes, sanity-check contrast against `references/design-audit-checklist.md`'s ratios rather than eyeballing it. If the project has a way to preview (dev server, storybook, or you can render the component), use it. Mention anything you deliberately left alone that's related but out of scope, so the person can decide if they want it addressed too.

## Quick-reference: design principles

For fast lookups while working, `references/design-principles.md` has compact scales and rules of thumb for typography, spacing, color/contrast, and common anti-patterns with their fixes. Read the audit checklist for the *process*, and this file for the *numbers* (type scale ratios, spacing grid, contrast minimums) when you need something concrete to cite or apply.

## A note on taste

Checklists catch objective problems (contrast failures, inconsistent spacing, broken hierarchy) but good design is more than passing a checklist. Look at the result the way a person actually using the interface would — does it feel calm or cluttered, confident or timid, does the eye know where to go first? If something technically passes every rule but still looks generic or off, say so and try something with more character, the way frontend-design's guidance on avoiding templated defaults would push you to.