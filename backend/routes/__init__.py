# 2025-02-26
from routes.hex_grid import hex_grid_bp
from routes.hex_lookup import hex_lookup_bp
from routes.traffic_signals import traffic_signals_bp
from routes.green_corridor import green_corridor_bp
from routes.incidents import incidents_bp
from routes.patrol_alerts import patrol_alerts_bp
from routes.radio import radio_bp
from routes.simulation import simulation_bp
from routes.vehicles import vehicles_bp
from routes.dispatches import dispatches_bp


def register_blueprints(app):
    app.register_blueprint(hex_grid_bp)
    app.register_blueprint(hex_lookup_bp)
    app.register_blueprint(traffic_signals_bp)
    app.register_blueprint(green_corridor_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(patrol_alerts_bp)
    app.register_blueprint(radio_bp)
    app.register_blueprint(simulation_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(dispatches_bp)
