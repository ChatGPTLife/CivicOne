#!/usr/bin/env python3
# 2025-02-26
"""
Test script for radio comms. Run from backend dir: python scripts/test_radio.py
Requires: backend running, DB with hex_cells and vehicles.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_hex_labels():
    """Test hex_labels module."""
    print("1. Testing hex_labels...")
    try:
        from utils.hex_labels import get_hex_label
        label = get_hex_label("87618c446ffffff")
        print(f"   get_hex_label('87618c446ffffff') = {label!r}")
        print("   OK")
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        return False


def test_radio_comms_import():
    """Test radio_comms can be imported and trigger_radio_comms exists."""
    print("2. Testing radio_comms import...")
    try:
        from services.radio_comms import trigger_radio_comms
        print("   OK")
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        return False


def test_radio_comms_with_app_context():
    """Test trigger_radio_comms with Flask app context (emits to socket)."""
    print("3. Testing trigger_radio_comms with app context...")
    try:
        from app import app
        from services.radio_comms import trigger_radio_comms

        with app.app_context():
            trigger_radio_comms(
                vehicle_id=12345,
                vehicle_prev_status="patrolling",
                incident_type="accident",
                hex_id="87618c446ffffff",
            )
        print("   OK (no exception)")
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_post_incident_telegram():
    """Test POST /api/incidents/telegram - full flow including radio."""
    print("4. Testing POST /api/incidents/telegram...")
    try:
        import requests
        base = os.getenv("API_BASE_URL", "http://localhost:8000")
        res = requests.post(
            f"{base}/api/incidents/telegram",
            json={
                "type": "accident",
                "latitude": 13.08,
                "longitude": 80.27,
                "report_id": "TEST-RADIO",
            },
            timeout=10,
        )
        print(f"   Status: {res.status_code}")
        if res.status_code >= 400:
            print(f"   Body: {res.text[:200]}")
        if res.status_code in (200, 201):
            data = res.json()
            print(f"   Incident: {data.get('incident', {}).get('id')}")
            print(f"   Vehicle: {data.get('dispatch', {}).get('vehicle', {}).get('id')}")
            print("   OK")
            return True
        print("   FAILED (check if backend running, DB has vehicles)")
        return False
    except requests.exceptions.ConnectionError:
        print("   FAILED: Cannot connect to backend. Is it running on port 8000?")
        return False
    except Exception as e:
        print(f"   FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=== Radio comms test ===\n")
    r1 = test_hex_labels()
    r2 = test_radio_comms_import()
    r3 = test_radio_comms_with_app_context()
    r4 = test_post_incident_telegram()
    print("\n=== Summary ===")
    print(f"hex_labels: {'PASS' if r1 else 'FAIL'}")
    print(f"radio_comms import: {'PASS' if r2 else 'FAIL'}")
    print(f"trigger_radio_comms: {'PASS' if r3 else 'FAIL'}")
    print(f"POST incident: {'PASS' if r4 else 'FAIL'}")
    sys.exit(0 if (r1 and r2 and r3) else 1)
