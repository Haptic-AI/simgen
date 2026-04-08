# Brand Restyle + New Simulation Templates

**Date:** 2026-04-08

## What changed

### Brand Theme Framework

Replaced the dark mode UI with Haptic Labs brand kit. All styling now uses CSS custom properties in `globals.css` — change one file to retheme the entire app.

**Colors:**
- Primary Blue: `#00579C`
- Ink Blue: `#002F6C`
- Vintage Paper background: `#F5EBD4`
- Grid Beige: `#F9F5E7`

**Typography:**
- DM Sans (headings + body)
- IBM Plex Mono (code/technical text)
- Bolder weight (450 base), larger text per boss feedback

**Visual:**
- Grid paper background (subtle engineering notebook lines)
- Light mode (was dark)
- All 10 components + layout + page restyled using `var()` references

### New Simulation Templates (4 added)

| Template | Description | Key Params |
|----------|-------------|------------|
| `double_pendulum` | Two linked arms, chaotic motion | length1, length2, damping, initial_angle1, initial_angle2, gravity |
| `falling_stack` | 6 blocks collapsing under gravity | block_size, block_mass, offset, friction, gravity |
| `ragdoll` | Articulated figure falling/tumbling | drop_height, push_force, damping, gravity |
| `spinning_top` | Gyroscopic top with precession | disc_radius, mass, spin_speed, tilt_angle, tip_height, gravity |

Total templates: 9 (was 5, with only 3 actively used)

### Homepage Updates

- 9 showcase prompts on homepage (one per template, 3x3 grid)
- "Built by Haptic Labs" footer with blog + GitHub links
- All external links have `?ref=https://simgen.hapticlabs.ai`
- Blog: https://www.hapticlabs.ai/blog/2026/04/06/from-cloud-gpus-to-creative-canvas
- GitHub: https://github.com/Haptic-AI/simgen

## Files modified

**Frontend:**
- `frontend/app/globals.css` — theme framework (CSS custom properties)
- `frontend/app/layout.tsx` — fonts, light mode
- `frontend/app/page.tsx` — header links, showcase grid, footer
- `frontend/components/*.tsx` — all 10 components restyled

**Backend:**
- `backend/templates.py` — 4 new template schemas
- `backend/renderer.py` — initial conditions for double_pendulum, ragdoll, spinning_top
- `backend/templates/double_pendulum.xml`
- `backend/templates/falling_stack.xml`
- `backend/templates/ragdoll.xml`
- `backend/templates/spinning_top.xml`

## Theme framework usage

To change the entire look, edit only `frontend/app/globals.css`:

```css
:root {
  --brand-primary: #00579C;    /* change this */
  --brand-ink: #002F6C;        /* change this */
  --brand-paper: #F5EBD4;      /* change this */
  --brand-grid: #F9F5E7;       /* change this */
  /* everything else derives from these */
}
```

Components reference variables like:
- `bg-[var(--color-surface)]`
- `text-[var(--color-text)]`
- `border-[var(--color-border)]`
- `bg-[var(--color-primary)]`

## Deployed

- Production: https://simgen.hapticlabs.ai
- GitHub: pushed to `main` branch
