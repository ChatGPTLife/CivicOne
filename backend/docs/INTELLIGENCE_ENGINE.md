<!-- 2025-02-26 -->
# Incident Intelligence Engine

**File:** `services/intelligence_engine.py`

## Purpose

Processes new incidents to:
1. Update hex cell incident counts
2. Generate patrol alerts
3. Suggest ambulance pre-stationing

## Thresholds

| Config | Default | Description |
|--------|---------|--------------|
| INCIDENT_DENSITY_THRESHOLD | 5 | Alerts when hex incident count ≥ 5 |
| ACCIDENT_ALERT_THRESHOLD | 3 | Ambulance suggestion when accident count ≥ 3 |

## Alert Types

- **high_incident_density** – "Increase patrol frequency"
- **ambulance_prestation_suggestion** – "Consider ambulance pre-stationing nearby"

## Patrol Priority Score

When incident density exceeds threshold, `patrol_priority_score` is incremented by 1.0 for that hex.
