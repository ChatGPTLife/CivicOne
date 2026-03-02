// 2025-02-26
import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export function getSocketClient() {
  if (socket) {
    return socket;
  }

  const socketUrl = process.env.NEXT_PUBLIC_SOCKET_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  socket = io(socketUrl, {
    transports: ["polling"],
    upgrade: false,
  });

  return socket;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}
