# Courier Control UI quality pipeline

## Goal
UI changes must be designed, reviewed and tested before they reach the stable deployment.

## Flow
1. Define the screen and states before coding.
2. Reuse design tokens and shared components; do not add page-local CSS unless unavoidable.
3. Develop on a feature branch.
4. Run Django checks/tests and UI contract tests.
5. Render the UI at 320, 375, 390, 393, 430, 768 and 1440 px widths.
6. Review screenshots before merging.
7. Deploy to staging and verify on a real iPhone.
8. Merge/deploy stable only after approval.
9. Create a new immutable checkpoint branch after the stable version is verified.

## UI rules
- Mobile-first. No horizontal page overflow.
- Inputs and buttons use shared sizes/radii/spacing.
- Native controls must be tested in WebKit/iOS-like rendering.
- Scrollable card rows may scroll horizontally but must hide intrusive scrollbars and use snap points.
- Fixed/sticky action bars require reserved content space; prefer normal document flow for forms.
- No CSS inside templates for reusable components.
- Never move an existing checkpoint branch. Create a new checkpoint.

## Visual acceptance
A screen is not complete merely because Django tests pass. It must pass responsive layout checks and screenshot review. A visual baseline is updated only after human approval.
