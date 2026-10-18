---
name: tailwind-ui
description: "Create or refine responsive React and Next.js UI with Tailwind CSS. Use for components, app shells, navigation, accessibility, styling fixes, and safe layout refactors that must preserve existing design."
---

# Tailwind UI

## When to Use
- Building or changing Next.js/React pages, components, navigation, or responsive layouts.
- Fixing visual regressions or refactoring shared UI while preserving the current design.
- Applying Tailwind utilities, interaction states, or accessibility improvements.

## Procedure
1. Read the target component and its parent layout, global styles, Tailwind configuration, and nearby components before editing.
2. Identify the existing visual structure and behavior that must remain. Treat shared layouts, navigation, and user menus as protected surfaces.
3. Make the smallest component-level change that satisfies the request. Do not replace a whole layout or component to fix a localized issue.
4. Preserve existing Tailwind classes and design tokens unless the requirement explicitly calls for a design change. Do not replace the styled interface with bare HTML or remove responsive states.
5. Use semantic elements, keyboard-operable controls, visible focus states, accessible names, and appropriate contrast. Use links for navigation and buttons for actions.
6. Keep styling responsive and consistent with the current breakpoints; avoid one-off arbitrary values when an existing token or pattern fits.
7. Run the frontend linter, type check, and production build when available. Review the changed page at relevant viewport sizes for overflow, missing states, and unintended layout shifts.

## Constraints
- Do not use `any` in TypeScript; preserve strict component prop types.
- Avoid broad global CSS changes for a component-specific adjustment.
- Do not add dependencies for simple UI behavior without a clear need.
