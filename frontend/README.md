# Financial Coach frontend

React + TypeScript + Vite. Mockup with demo data; not connected to the backend yet.

```bash
npm install
npm run dev      # http://localhost:5173, /api is forwarded to FastAPI on :8000
npm run build    # typecheck + production build
npm run lint
```

## What to edit

| Change | File |
|---|---|
| Colours, fonts, spacing, corners | `src/styles/tokens.css` (S-Pankki's published colours; change values, not names) |
| Show or hide optional sections | `src/config/ui.config.ts` |
| Layout and component styling | `src/styles/components.css` (uses tokens only, no raw colours) |
| Demo numbers | `src/fixtures/demo.ts` (illustrative, not from the dataset) |

Basket keys and labels match `coach/spending_baskets.py`. The backend does all money arithmetic; the frontend only formats it (`src/lib/money.ts`).

Brand rules: no S-Pankki logo or S Bonus fonts until the sponsor approves them in writing. Keep the "prototype · synthetic data" badge.
