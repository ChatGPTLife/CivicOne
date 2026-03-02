# 2025-02-26
import logging
import os

from flask import Flask
from flask_cors import CORS

from config import Config
from extensions import socketio
from routes import register_blueprints
from services.dispatch_engine import DispatchEngine
from services.hex_service import HexService
from services.intelligence_engine import IncidentIntelligenceEngine
from services.route_service import RouteService
from services.simulation_engine import SimulationEngine
from sockets.events import register_socket_handlers


logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], supports_credentials=False)

    socketio.init_app(app)

    route_service = RouteService(app.config["OSRM_BASE_URL"])
    hex_service = HexService(
        app.config["CHENNAI_BBOX"],
        app.config["H3_RESOLUTION"],
    )
    intelligence_engine = IncidentIntelligenceEngine(
        incident_density_threshold=app.config["INCIDENT_DENSITY_THRESHOLD"],
        accident_alert_threshold=app.config["ACCIDENT_ALERT_THRESHOLD"],
    )
    dispatch_engine = DispatchEngine(route_service=route_service, hex_service=hex_service)
    simulation_engine = SimulationEngine(
        hex_service=hex_service,
        dispatch_engine=dispatch_engine,
        intelligence_engine=intelligence_engine,
    )

    app.extensions["hex_service"] = hex_service
    app.extensions["dispatch_engine"] = dispatch_engine
    app.extensions["intelligence_engine"] = intelligence_engine
    app.extensions["simulation_engine"] = simulation_engine

    register_blueprints(app)
    register_socket_handlers(socketio)

    with app.app_context():
        try:
            from utils.db import ensure_vehicles_table, ensure_incidents_table
            ensure_vehicles_table()
            ensure_incidents_table()
        except RuntimeError as error:
            logger.warning("DB init skipped: %s", error)
        try:
            hex_service.ensure_hex_cells_in_db()
        except RuntimeError as error:
            logger.warning("Hex bootstrap skipped at startup: %s", error)

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}, 200

    @app.errorhandler(RuntimeError)
    def handle_runtime_error(error: RuntimeError):
        message = str(error)
        logger.exception("RuntimeError: %s", message)
        if message.startswith("Database"):
            # In debug mode, expose actual DB error for easier troubleshooting
            if app.debug:
                return {"error": "Database operation failed", "detail": message}, 500
            return {"error": "Database operation failed"}, 500
        return {"error": "Internal server error"}, 500

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        debug=True,
        allow_unsafe_werkzeug=True,
    )
