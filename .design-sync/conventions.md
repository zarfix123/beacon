# Beacon — building with these components

Beacon's parts are plain React components that style themselves with **CSS custom
properties (design tokens)** and ship their own **CSS Modules**. There is **no theme
provider and no class-name utility system** — you do not wrap anything in a context,
and there are no `bg-*`/`p-*` utility classes. You style your *own* layout glue with
the `var(--*)` tokens below; the components style themselves.

## Setup

1. **Load the stylesheet.** Import the bound `styles.css` once at the app root. It pulls
   in the tokens and fonts (the `var(--*)` values and the brand families). Without it
   every token resolves to nothing and components render unstyled.
2. **Panels need a positioned stage.** `AnswerPanel`, `AgentsReached`,
   `NetworkConstellation`, and `PromptPill` are app-overlay panels that position
   themselves `absolute` (AnswerPanel top-left, AgentsReached top-right,
   NetworkConstellation fills, PromptPill is a bottom dock). Render them inside a
   `position: relative` container with real dimensions — otherwise they anchor to the
   viewport. The icons and any leaf usage are inline and need no stage.
3. **No live data required.** Every component is prop-driven; pass plain objects/strings
   (see each component's `.d.ts` + `.prompt.md`). They do not fetch.

## The styling idiom — tokens

Style your own elements with these `var(--*)` families (names are verbatim from
`tokens/*.css`):

| Family | Real tokens |
|---|---|
| Surfaces | `--surface-page` `--surface-card` `--surface-raised` `--surface-sunken` `--surface-inverse` |
| Text | `--text-primary` `--text-secondary` `--text-muted` `--text-link` `--text-inverse` |
| Signal / status | `--signal-500` `--signal-600` (beacon accent, electric blue) · `--active-500` (verified green) · `--warn-500` `--warn-600` (restricted amber) · `--danger-500` · `--info-500` |
| Borders | `--border-subtle` `--border-default` `--border-strong` `--border-focus` |
| Spacing | `--space-xs` `--space-sm` `--space-md` `--space-base` `--space-lg` `--space-xl` `--space-2xl` … `--space-4xl` |
| Radius | `--radius-sm` `--radius-md` `--radius-lg` `--radius-pill` |
| Shadow / glass | `--shadow-sm` `--shadow-md` `--shadow-lg` · `--blur-glass` |
| Type families | `--font-sans` (Hanken Grotesk) · `--font-serif` (Newsreader) · `--font-mono` (JetBrains Mono) |
| Type scale | `--display-hero-size` `--display-large-size` `--body-size` `--body-small-size` `--label-size` `--overline-size` (+ matching `*-lh`, `*-ls`) |
| Weights | `--weight-regular` `--weight-medium` `--weight-semibold` `--weight-bold` |
| Motion | `--dur-fast` `--dur-base` `--dur-slow` · `--ease-out` `--ease-spring` |
| Layering | `--z-panel` `--z-popover` `--z-overlay` `--z-chrome` |

## Where the truth lives

Read the bound `tokens/*.css` (`colors.css`, `typography.css`, `spacing.css`,
`base.css`, `fonts.css`) for the full token set, and each component's `.prompt.md` +
`.d.ts` for its exact props.

## One idiomatic build

```jsx
// A results stage: the answer panel + agent list over the constellation, with a
// prompt dock — your layout glue uses tokens; the components style themselves.
<div style={{ position: 'relative', height: '100dvh', background: 'var(--surface-page)' }}>
  <NetworkConstellation isResults nodes={nodes} subtitle="3 in range" onClearFocus={clear} />
  <AnswerPanel answer={answer} provenance={provenance} cards={cards} onHandoff={handoff} />
  <AgentsReached cards={cards} reachLine="1 full · 1 scoped · 1 denied"
                 expanded={expanded} onToggle={toggle} onRequest={request} />
  <PromptPill question={q} scopeLabel="team" onQ={onQ} onKey={onKey} onSubmit={submit} />
</div>
```

Status color convention: **green `--active-500` = full/verified, amber `--warn-500` =
redacted/restricted, grey `--warm-mid` = denied, electric `--signal-500` = the live
beacon accent while searching.**
