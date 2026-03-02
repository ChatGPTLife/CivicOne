<!-- 2025-02-26 -->
# Dispatch Algorithm

## Vehicle Assignment

The dispatch engine uses a **Nearest Available Vehicle** strategy:

1. **Filter**: Select all vehicles with `status = 'available'`
2. **Distance**: Compute Haversine distance (great-circle distance in km) from each vehicle to the incident
3. **Assign**: Pick the vehicle with the **minimum distance**
4. **Update**: Set vehicle status to `busy`, assign to incident

### Implementation

- **File**: `services/dispatch_engine.py`
- **Method**: `_nearest_vehicle(incident)`
- **Distance function**: `utils/geo.py` → `haversine_km(lat1, lon1, lat2, lon2)`

```python
return min(
    available_vehicles,
    key=lambda vehicle: haversine_km(
        incident["latitude"], incident["longitude"],
        vehicle["latitude"], vehicle["longitude"],
    ),
)
```

## Route Computation

- **Service**: `services/route_service.py`
- **Source**: OSRM (Open Source Routing Machine) – road-based shortest path
- **Fallback**: Straight line if OSRM fails

## Green Corridor

Hex cells along the route are marked as "green corridor" for traffic signal priority.

## Auto-Mark Attended

When a vehicle's position is updated (e.g. via `/api/vehicles/position`):

- If the vehicle is assigned to an incident
- And the vehicle is within **50 meters** of the incident (Haversine distance)
- The incident is automatically marked as `attended`

**File**: `routes/vehicles.py` (in `update_vehicle_position`)
