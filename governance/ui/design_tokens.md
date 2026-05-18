# Design Tokens and UI Constraints

## U-001: Visual Language
Pathline uses a refined dark-mode instrumentation aesthetic.
- **Surface:** Warm charcoal.
- **Accent:** Antique gold.
- **Typography:** IBM Plex Sans (precision), Italic Serif (editorial flourishes).

## U-002: Frontend Technical Constraints
- **Frameworks:** Strictly forbidden (No React, Vue, Svelte, etc.).
- **State Management:** No libraries (No Redux, MobX, etc.).
- **Build Tools:** Forbidden (No Vite, webpack, Rollup).
- **Implementation:** Lightweight vanilla JavaScript only.
- **Abstractions:** Only the `frontend/static/js/common/` layer is approved.

## U-003: Operational Visibility
- No hidden reactivity or state machines.
- All frontend behavior must be explicit and debuggable.
- Server-rendered components (index.html served via Python) are preferred.
