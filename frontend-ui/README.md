# Pathline Frontend UI

Shareable React UI for privacy-preserving IVR script editing and status runs.

No backend required for local UI development — point `VITE_API_URL` at your API when testing end-to-end.

## What's included

```
frontend-ui/
├── src/
│   ├── components/     Script editor, call flow, run panel
│   ├── script/         Script model, compile, storage
│   ├── context/        Script store
│   ├── styles.css      Full theme
│   └── App.tsx         Call + Scripts tabs
├── public/scripts/     Optional script JSON (blank template)
├── package.json
└── vite.config.ts
```

## Quick start

```bash
cd frontend-ui
npm install
npm run dev
```

Open http://localhost:3000

## Script editor (Scripts tab)

Four layers per script:

| Section | Purpose |
|---------|---------|
| **Basics** | Name, description, target number, timeout, tags |
| **Secrets** | Values the script needs at run time |
| **Conversation** | When I hear → Then (Send Keys, Save Value, …) |
| **Results** | Fields captured during a run |

Scripts are stored in browser `localStorage`. Use **Export** to back up as JSON.

## API (optional)

Set in `.env`:

```
VITE_API_URL=http://localhost:8000
```

Endpoints used by the Call tab: `/v1/token`, `/v1/status`, `/v1/revoke`.

## Share this folder

Zip or copy `frontend-ui/` as-is. Recipients run `npm install && npm run dev`.

To refresh from the main Pathline repo:

```bash
./scripts/sync-frontend-ui.sh
```
