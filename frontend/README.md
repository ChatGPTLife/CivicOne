<!-- 2025-02-26 -->
# One City One Number – Chennai (Frontend)

Next.js + TypeScript command dashboard for unified emergency and civic dispatch operations.

## Features Implemented

- Axios-based API integration with Flask backend
- Leaflet map with:
	- Hex-grid overlay toggle
	- Incident density color coding
	- Incident markers
	- Vehicle markers
	- Route polyline updates
	- Green corridor hex highlighting
- Real-time events via Socket.IO:
	- `new_incident`
	- `vehicle_dispatched`
	- `route_update`
	- `patrol_alert`
	- `simulation_update`
- Incident creation form (`POST /api/incidents`)
- Simulation controls:
	- `POST /api/simulation/config`
	- `POST /api/simulation/run`
	- `POST /api/simulation/reset`
- Patrol alert feed (`GET /api/patrol-alerts`)

## Environment

Copy `.env.example` to `.env.local` and adjust if needed:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SOCKET_URL=http://localhost:8000
```

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Notes

- Backend is expected at port `8000` by default.
- Telegram integration is intentionally not included.
