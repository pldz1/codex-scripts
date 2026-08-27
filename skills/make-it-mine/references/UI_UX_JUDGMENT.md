# UI and UX Judgment Reference

Use this when the task involves page structure, interaction design, UI component choice, or visual hierarchy.

The learning target is not a component name. It is the decision rule the user can reuse.

## Interaction decision dimensions

For a UI choice, reason about:

- **task** — what is the user trying to accomplish?
- **frequency** — occasional or repeated/high-speed action?
- **precision** — exact value or approximate adjustment?
- **option count** — how many choices exist?
- **comparison** — must users see alternatives simultaneously?
- **reversibility** — can the action be undone?
- **error cost** — what happens if the user is wrong?
- **expertise** — novice, mixed, or expert users?
- **space** — desktop, mobile, constrained panel?
- **accessibility** — keyboard, screen reader, motor constraints?
- **feedback** — how is success/failure communicated?

## Common decision probes

### Slider vs numeric input
Slider favors bounded relative adjustment and low precision.
Numeric input favors exact known values, broad ranges, and keyboard efficiency.
Often the right answer is both: slider plus editable numeric value.

### Select vs radio group
Radio exposes alternatives and supports comparison when options are few.
Select saves space when options are numerous or secondary.

### Checkbox vs toggle
Checkbox often represents selection or form state committed later.
Toggle often communicates an immediate on/off setting.
Validate the product semantics; do not use appearance as the rule.

### Modal vs drawer vs page
Modal: focused, temporary, contextual task.
Drawer: preserves context while supporting somewhat richer secondary work.
Page: deep, shareable, navigable, long-running, multi-step, or high-complexity task.

### Table vs cards
Table: dense comparison across repeated fields.
Cards: heterogeneous content, visual browsing, or item-focused actions.

### Pagination vs infinite scroll
Pagination: location, control, revisiting, bounded result exploration.
Infinite scroll: continuous discovery where exact position matters less.

### Toast vs inline feedback
Toast: transient global confirmation with low recovery need.
Inline: errors or feedback tied to a specific field/content area, especially when action is required.

## Visual reasoning

Do not accept labels such as "clean" or "modern" as sufficient reasoning.
Ask:

- What should the eye notice first?
- Which information is primary, secondary, or optional?
- What should be grouped?
- What can be progressively disclosed?
- What density matches the task?
- Which action is truly primary?
- How does the layout change on narrow screens?

## Transfer test examples

If a slider works for image opacity, ask whether it works for annual salary.
If a modal works for renaming an item, ask whether it works for a 7-step onboarding flow.
If cards work for a marketplace browse page, ask whether they work for comparing 25 rows of financial metrics.
