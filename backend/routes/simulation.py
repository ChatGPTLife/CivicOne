# 2025-02-26
from flask import Blueprint, current_app, request


simulation_bp = Blueprint("simulation", __name__, url_prefix="/api/simulation")


@simulation_bp.post("/config")
def simulation_config():
    payload = request.get_json(silent=True) or {}
    simulation_engine = current_app.extensions["simulation_engine"]
    config = simulation_engine.update_config(payload)
    return {"config": config}, 200


@simulation_bp.post("/run")
def simulation_run():
    payload = request.get_json(silent=True) or {}
    simulation_engine = current_app.extensions["simulation_engine"]
    result = simulation_engine.run(payload)
    return result, 200


@simulation_bp.post("/reset")
def simulation_reset():
    simulation_engine = current_app.extensions["simulation_engine"]
    result = simulation_engine.reset()
    return result, 200
