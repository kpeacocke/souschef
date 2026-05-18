# Accessibility Regression Checklist

Use this checklist in pull requests that change UI behaviour or styles.

## WCAG 2.1 AA Baseline Checks

- Keyboard focus order follows visual flow for primary workflows.
- Every interactive control has a visible text label.
- Focus indicators are clearly visible on controls and skip links.
- High-contrast mode keeps text and controls readable.
- Core pages provide semantic landmarks for navigation and main content.

## Core Workflow Pass

- Dashboard navigation (tabs/buttons) is operable by keyboard only.
- Command palette controls are labelled and keyboard accessible.
- Workspace management forms provide visible labels and helper context.
- Analytics dashboard filters and drill-down controls remain labelled.

## Suggested CI Review Notes

Include the following in PR notes when UI changes are present:

- Which pages were checked.
- Whether high-contrast mode was tested.
- Any known accessibility limitations and follow-up issues.
