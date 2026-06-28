"""HTTP client for AIWriteX server API."""

from typing import Any, Optional
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
