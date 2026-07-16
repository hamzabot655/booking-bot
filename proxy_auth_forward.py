"""Local forwarding proxy that adds Basic auth to an upstream HTTP proxy.

Chrome's --proxy-server ignores embedded user:pass, and on Chrome 127+ the
MV2 auth-extension trick is dead. This forwarder listens on localhost and, for
every connection, opens a connection to the upstream proxy (e.g. DataImpulse)
with a `Proxy-Authorization: Basic ...` header, then pumps bytes. HTTPS goes
through CONNECT untouched (no cert interception).

Threading: two daemon threads per connection (one relay per direction — the
proven design that works with Chrome's headless TLS on Railway). An IDLE
recv-timeout on every relay socket means a stuck/half-open connection closes on
its own, so threads always exit and can't pile up to the "can't start new
thread" limit. (An earlier BoundedSemaphore attempt drained on idle keep-alive
connections and blocked accept(), causing net::ERR_CONNECTION_CLOSED on Railway
— hence the timeout approach instead.)

Usage:
    port = start_auth_forwarder("gw.dataimpulse.com", 823, "user", "pass")
    # then Chrome:  --proxy-server=http://127.0.0.1:{port}
"""
from __future__ import annotations

import base64
import socket
import threading
from typing import Dict, Tuple

_RUNNING: Dict[Tuple[str, int, str, str], int] = {}
_LOCK = threading.Lock()

# Idle timeout (seconds): a relay socket with no traffic for this long is closed,
# so its two threads exit. Bounds thread growth without blocking new connections.
_IDLE_TIMEOUT = 180


def _pipe(a: socket.socket, b: socket.socket) -> None:
    """One-direction relay: read from a, write to b, until either side closes or idles out."""
    try:
        a.settimeout(_IDLE_TIMEOUT)
    except OSError:
        pass
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _handle(client: socket.socket, up_host: str, up_port: int, auth: str) -> None:
    up = None
    try:
        client.settimeout(30)
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = client.recv(4096)
            if not chunk:
                return
            head += chunk
            if len(head) > 65536:
                break
        line = head.split(b"\r\n", 1)[0].decode("latin1", "ignore")
        parts = line.split(" ")
        method = parts[0] if parts else ""

        up = socket.create_connection((up_host, up_port), timeout=30)

        if method.upper() == "CONNECT":
            target = parts[1]
            req = (
                "CONNECT %s HTTP/1.1\r\nHost: %s\r\n"
                "Proxy-Authorization: Basic %s\r\n"
                "Proxy-Connection: Keep-Alive\r\n\r\n" % (target, target, auth)
            )
            up.sendall(req.encode("latin1"))
            resp = b""
            while b"\r\n\r\n" not in resp:
                c = up.recv(4096)
                if not c:
                    break
                resp += c
            client.sendall(resp)
        else:
            inject = b"Proxy-Authorization: Basic " + auth.encode() + b"\r\n"
            head = head.replace(b"\r\n", b"\r\n" + inject, 1)
            up.sendall(head)

        t = threading.Thread(target=_pipe, args=(client, up), daemon=True)
        t.start()
        _pipe(up, client)
    except OSError:
        pass
    finally:
        for s in (client, up):
            try:
                if s:
                    s.close()
            except OSError:
                pass


def start_auth_forwarder(up_host: str, up_port: int, user: str, pw: str) -> int:
    """Start (or reuse) a localhost forwarder to the authenticated upstream proxy.
    Returns the local port to point Chrome at."""
    key = (up_host, up_port, user, pw)
    with _LOCK:
        if key in _RUNNING:
            return _RUNNING[key]
        auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(256)
        port = srv.getsockname()[1]

        def _accept() -> None:
            while True:
                try:
                    cli, _ = srv.accept()
                except OSError:
                    break
                try:
                    threading.Thread(
                        target=_handle, args=(cli, up_host, up_port, auth), daemon=True
                    ).start()
                except RuntimeError:
                    # Extremely unlikely with the idle timeout; drop rather than crash.
                    try:
                        cli.close()
                    except OSError:
                        pass

        threading.Thread(target=_accept, daemon=True).start()
        _RUNNING[key] = port
        return port
