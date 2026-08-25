import { useCallback, useEffect, useRef, useState } from "react";

export function useSocket(onMessage: (message: any) => void, disabled = false) {
  const socket = useRef<WebSocket | null>(null);
  const handler = useRef(onMessage); handler.current = onMessage;
  const [connected, setConnected] = useState(disabled);
  useEffect(() => {
    if (disabled) return;
    let retry = 0; let timer: number;
    const connect = () => {
      const base = location.pathname.replace(/\/?$/, "/");
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${location.host}${base}ws`); socket.current = ws;
      ws.onopen = () => { retry = 0; setConnected(true); };
      ws.onmessage = (event) => handler.current(JSON.parse(event.data));
      ws.onclose = () => { setConnected(false); timer = window.setTimeout(connect, Math.min(5000, 500 * 2 ** retry++)); };
    };
    connect(); return () => { clearTimeout(timer); socket.current?.close(); };
  }, [disabled]);
  const send = useCallback((message: any) => socket.current?.readyState === WebSocket.OPEN && socket.current.send(JSON.stringify(message)), []);
  return { connected, send };
}
