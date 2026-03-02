# 2025-02-26
from flask import request


def register_socket_handlers(socketio):
    @socketio.on("connect")
    def handle_connect():
        print(f"Socket connected: {request.sid}")

    @socketio.on("disconnect")
    def handle_disconnect():
        print(f"Socket disconnected: {request.sid}")
