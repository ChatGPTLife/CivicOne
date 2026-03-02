<!-- 2025-02-26 -->
# API Reference

## Incidents

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/incidents | Create incident (web) |
| POST | /api/incidents/telegram | Create incident (Telegram bot) |
| GET | /api/incidents | List incidents |
| PATCH | /api/incidents/:id/attended | Mark attended, set vehicle to patrolling |

## Vehicles

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/vehicles | List vehicles |
| POST | /api/vehicles/deploy | Deploy vehicles |
| DELETE | /api/vehicles/:id | Remove vehicle |
| POST | /api/vehicles/position | Update position (patrol simulator) |

## Hex Grid

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/hex-grid | Hex cells with polygons |

## Radio

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/radio/static/:name | Static audio (controller, dispatch) |
| GET | /api/radio/test | Emit test radio_comm |

## Socket Events

- `new_incident` – New incident created
- `vehicle_dispatched` – Vehicle assigned to incident
- `vehicle_position` – Vehicle moved
- `vehicle_removed` – Vehicle deleted
- `incident_attended` – Incident marked attended
- `radio_comm` – Radio comms (control/dispatch)
- `patrol_alert` – Intelligence alert
