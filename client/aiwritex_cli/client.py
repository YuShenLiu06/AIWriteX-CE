"""HTTP client for AIWriteX server API."""

from typing import Any, Callable, Optional
import base64
import json
import threading
from urllib.parse import urlencode

import requests

from .config_store import ConfigStore
from .errors import AuthError, ConnectionError, NotFoundError, ServerError


# Top-level CLI overrides (--base-url / --api-key / --username / --password / --timeout),
# populated by the main() callback. Priority: explicit arg > override > config file.
_CLI_OVERRIDES: dict[str, Any] = {}


def set_overrides(**overrides: Any) -> None:
    """Record top-level CLI options as in-process overrides (None values ignored)."""
    _CLI_OVERRIDES.update({k: v for k, v in overrides.items() if v is not None})


class AIWriteXClient:
    """HTTP client for AIWriteX server."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize client with optional overrides."""
        config = ConfigStore.load()
        self.base_url = base_url or _CLI_OVERRIDES.get("base_url") or config.get("base_url", "http://127.0.0.1:8888")
        self.api_key = api_key or _CLI_OVERRIDES.get("api_key") or config.get("api_key")
        self.username = username or _CLI_OVERRIDES.get("username") or config.get("username")
        self.password = password or _CLI_OVERRIDES.get("password") or config.get("password")
        self.timeout = timeout or _CLI_OVERRIDES.get("timeout") or config.get("timeout", 30)

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _auth(self) -> Optional[tuple[str, str]]:
        """Build HTTP basic auth."""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        data: Optional[Any] = None,
        files: Optional[dict] = None,
        stream: bool = False,
    ) -> requests.Response:
        """Make HTTP request with error handling."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                auth=self._auth(),
                params=params,
                json=json,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=stream,
            )
            self._check_error(response)
            return response
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"连接失败: {e}") from e
        except requests.exceptions.Timeout as e:
            raise ConnectionError(f"请求超时: {e}") from e
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"请求错误: {e}") from e

    def _check_error(self, response: requests.Response) -> None:
        """Check response for errors and raise appropriate exception."""
        if response.status_code == 401:
            raise AuthError("认证失败，请检查 API Key 或用户名密码")
        if response.status_code == 404:
            raise NotFoundError("资源不存在")
        if response.status_code >= 500:
            raise ServerError(f"服务器错误: {response.status_code}")
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise ServerError(f"请求错误 ({response.status_code}): {detail}")

    def get_json(self, path: str, params: Optional[dict] = None) -> dict:
        """GET request returning JSON."""
        response = self.request("GET", path, params=params)
        return response.json()

    def post_json(self, path: str, json: Optional[dict] = None) -> dict:
        """POST request returning JSON."""
        response = self.request("POST", path, json=json)
        return response.json()

    def put_json(self, path: str, json: Optional[dict] = None) -> dict:
        """PUT request returning JSON."""
        response = self.request("PUT", path, json=json)
        return response.json()

    def patch_json(self, path: str, json: Optional[dict] = None) -> dict:
        """PATCH request returning JSON."""
        response = self.request("PATCH", path, json=json)
        return response.json()

    def delete_json(self, path: str) -> dict:
        """DELETE request returning JSON."""
        response = self.request("DELETE", path)
        return response.json()

    def get_text(self, path: str, params: Optional[dict] = None) -> str:
        """GET request returning text."""
        response = self.request("GET", path, params=params)
        return response.text

    def post_file(self, path: str, files: dict, data: Optional[dict] = None) -> dict:
        """POST request with file upload."""
        response = self.request("POST", path, files=files, data=data)
        return response.json()

    # ----- WebSocket streaming (for /api/ws/generate/logs) -----

    def get_ws_url(self, path: str) -> str:
        """Convert base_url http(s):// to ws(s):// and append path."""
        base = self.base_url.rstrip("/")
        if base.startswith("https://"):
            ws_base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            ws_base = "ws://" + base[len("http://"):]
        else:
            ws_base = base
        return f"{ws_base}/{path.lstrip('/')}"

    def _apply_ws_auth(self, query: dict, headers: list) -> None:
        """Populate auth for WS handshake per server's _check_websocket_auth.

        Server (generate.py:38-74) accepts: Basic Auth header OR ?api_key= query.
        Username/password via query is NOT supported, so we prefer api_key in query
        and fall back to Basic header when only username/password is configured.
        """
        if self.api_key:
            query["api_key"] = self.api_key
            return
        if self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            headers.append(f"Authorization: Basic {token}")

    def stream_generate_logs(
        self,
        on_message: Callable[[dict], None],
        timeout: float,
    ) -> str:
        """Subscribe to WS /api/ws/generate/logs until task ends or timeout.

        Args:
            on_message: called for every received message dict {type, message, ...}.
            timeout: total seconds before raising TimeoutError.

        Returns:
            Final server status: "completed" or "failed".

        Raises:
            ConnectionError: WS handshake/transport failure (caller may downgrade to polling).
            TimeoutError: timeout reached before server sent a terminal message.
        """
        import websocket  # websocket-client (added to pyproject.toml)

        query: dict[str, str] = {}
        header_lines: list[str] = []
        self._apply_ws_auth(query, header_lines)

        url = self.get_ws_url("/api/ws/generate/logs")
        if query:
            url = f"{url}?{urlencode(query)}"

        state: dict[str, Any] = {"final": None, "error": None}
        # state 同时被 WS 回调线程与 timeout 定时器线程读写，用锁防止
        # check-then-act 竞态（例如 _kill_on_timeout 在 final 刚置位时误写 error）。
        state_lock = threading.Lock()

        def _on_message(_ws, raw: str) -> None:
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                data = {"type": "info", "message": str(raw)}
            on_message(data)
            msg_type = data.get("type", "")
            if msg_type in ("completed", "failed"):
                with state_lock:
                    state["final"] = msg_type
                try:
                    _ws.close()
                except Exception:
                    pass

        def _on_error(_ws, err: Exception) -> None:
            with state_lock:
                state["error"] = err

        app = websocket.WebSocketApp(
            url,
            header=header_lines,
            on_message=_on_message,
            on_error=_on_error,
        )

        def _kill_on_timeout() -> None:
            with state_lock:
                if state["final"] is not None or state["error"] is not None:
                    return
                state["error"] = TimeoutError(f"WebSocket 跟随超时（{timeout}s）")
            # close() 移到锁外，避免阻塞 WS 内部线程
            try:
                app.close()
            except Exception:
                pass

        timer = threading.Timer(timeout, _kill_on_timeout)
        timer.daemon = True
        timer.start()
        try:
            app.run_forever(ping_interval=30, ping_timeout=10)
        finally:
            timer.cancel()

        with state_lock:
            final = state["final"]
            error = state["error"]

        if final:
            return final
        if isinstance(error, TimeoutError):
            raise error
        if error is not None:
            raise ConnectionError(f"WebSocket 连接失败: {error}")
        # run_forever returned without terminal message or error (e.g. server closed cleanly)
        raise ConnectionError("WebSocket 连接意外关闭")
