# Frontend Reference

## Overview

The frontend is a React single-page application built by Vite and styled with plain CSS. It
uses browser path inspection instead of a routing library: `/signup` renders member signup,
paths beginning with `/dash` render officer access, and other paths render the landing page.
The production build is served by FastAPI; during development Vite proxies backend requests.

## Entry points and shared utilities

- `src/main.jsx` mounts `<App />` into `#root`.
- `src/App.jsx` selects the public, officer, or landing experience. `OfficerApp` checks the
  session once and owns the `loading`/`yes`/`no` authentication state.
- `src/api.js` exports `api(path, options)`, the common JSON request wrapper. It sends same-origin
  cookies, adds `Content-Type: application/json`, returns `null` for `204`, and throws an
  `Error` containing the API `detail` and HTTP `status` for failures.
- `easternDateTime(value)` formats timestamps in `America/New_York` regardless of browser zone.
- `src/styles.css` supplies the responsive layout, calendar, forms, modal, status, and utility
  classes. There is no component or state-management library.

## Member signup

`SignupPage` reads the `dive` query parameter, fetches the public dive, and controls the form
and request lifecycle with local state. Its states are loading, unavailable, editable form,
submission error, confirmed success, and waitlist success.

The component conditionally renders pickup location when carpooling and suit/shoe sizes when
renting. Before submission it converts shoe size to a number and sends irrelevant conditional
fields as `null`. Browser validation improves feedback, while the backend remains authoritative.

## Officer components

All officer UI is under `src/features/dashboard/`.

| Component/function | Responsibility |
| --- | --- |
| `LoginPage` | Submits the shared password, displays API errors, and notifies `OfficerApp` after login. |
| `Dashboard` | Owns loaded dives/officers/inventory, selected month, tabs, selected dive, edit modal, and logout. `load()` refreshes the three protected collections concurrently. |
| `Calendar` | Builds a Sunday-first month grid, groups dives by Eastern calendar day, and marks events that have warnings. |
| `DiveForm` | Creates or edits a dive and toggles officer UUID assignments, retaining inactive historical assignees while editing. |
| `DiveDetail` | Shows metadata, signup link, warnings, totals, active officers, gear report, confirmed roster, waitlist, and destructive dive controls. |
| `ParticipantEditor` | Displays PII and carpool/gear tags; edits member fields, removes signups, and exposes valid first-in-line promotion. |
| `OfficersPanel` | Adds officers and switches active status without deleting assignment history. |
| `InventoryPanel` | Adds categorized inventory and adjusts quantities. Decrementing the last unit deletes the row; zero rows received from an older dataset are hidden. |
| `monthTitle` | Formats the dashboard month heading. |
| `easternDayKey` | Converts a timestamp into the Eastern date key used by the calendar. |
| `localInput` | Converts stored timestamps for an Eastern `datetime-local` input. |

Dashboard mutations call the API, then reload canonical server state. This intentionally avoids
maintaining a second client-side business model.

## Accessibility and responsive behavior

Inputs use associated labels; errors use visible alert styling; modal sections declare dialog
semantics; icon-only controls have accessible names; and calendar events are buttons. CSS
collapses multi-column layouts for narrow screens. New interactions should remain keyboard
operable and must not depend on color alone to communicate warnings.

## Testing and build

- Vitest and React Testing Library cover conditional signup fields and inventory depletion.
- `src/testSetup.js` installs DOM matchers and cleanup.
- Playwright covers critical browser smoke flows from `e2e/`.
- ESLint enforces JavaScript and React Hook rules.

Run `npm test`, `npm run lint`, and `npm run build` from `frontend/`. The build writes `dist/`,
which is generated and not committed.

