"""Minimal GitLab REST client (stdlib only) plus secure token storage helpers."""
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

KEYRING_SERVICE = "py-project-init-gitlab"


class GitLabError(RuntimeError):
    """Raised for any failed GitLab API call. `status` holds the HTTP code if known."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _ssl_context() -> ssl.SSLContext:
    """Default verification (system trust store), but without Python 3.13+'s X509 strict mode.

    Self-hosted GitLab instances often use internal CA certificates without an Authority Key
    Identifier, which strict mode rejects ("Missing Authority Key Identifier") although git and
    browsers accept them. Chain, hostname and expiry are still fully verified.
    """
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


class GitLabClient:
    def __init__(self, base_url: str, token: str, timeout: float = 20.0):
        self.web_url = base_url.strip().rstrip("/")
        self.api_url = self.web_url + "/api/v4"
        self.token = token.strip()
        self.timeout = timeout
        self.ssl_context = _ssl_context()

    @staticmethod
    def _enc(path: str) -> str:
        return urllib.parse.quote(path.strip("/"), safe="")

    def _request(self, method: str, path: str, data: dict | None = None):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            self.api_url + path,
            data=body,
            method=method,
            headers={"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as res:
                raw = res.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                payload = json.loads(e.read() or b"{}")
                detail = payload.get("message") or payload.get("error") or ""
            except (ValueError, AttributeError):
                pass
            raise GitLabError(f"HTTP {e.code}: {detail or e.reason}", status=e.code) from e
        except urllib.error.URLError as e:
            raise GitLabError(f"GitLab nicht erreichbar ({self.web_url}): {e.reason}") from e

    def current_user(self) -> dict:
        return self._request("GET", "/user")

    def get_namespace_id(self, namespace: str) -> int:
        try:
            return self._request("GET", f"/namespaces/{self._enc(namespace)}")["id"]
        except GitLabError as e:
            if e.status == 404:
                raise GitLabError(f"Gruppe/Namespace '{namespace}' nicht gefunden oder kein Zugriff.", 404) from e
            raise

    def get_project(self, full_path: str) -> dict | None:
        try:
            return self._request("GET", f"/projects/{self._enc(full_path)}")
        except GitLabError as e:
            if e.status == 404:
                return None
            raise

    def create_project(
        self,
        name: str,
        namespace_id: int | None,
        default_branch: str,
        visibility: str = "private",
        description: str = "",
    ) -> dict:
        """Creates the project WITH an initial README so the default branch exists server-side.

        GitLab rejects pushes from Developers into a project without a default branch,
        so letting GitLab create it during project creation avoids the need for a Maintainer.
        """
        data = {
            "name": name,
            "path": name,
            "default_branch": default_branch,
            "initialize_with_readme": True,
            "visibility": visibility,
            "description": description,
        }
        if namespace_id is not None:
            data["namespace_id"] = namespace_id
        return self._request("POST", "/projects", data)

    def create_merge_request(self, project_id: int, source: str, target: str, title: str) -> dict:
        return self._request(
            "POST",
            f"/projects/{project_id}/merge_requests",
            {"source_branch": source, "target_branch": target, "title": title, "remove_source_branch": False},
        )


# ── Token storage (Windows Credential Manager via keyring, env var as fallback) ──

def load_token(base_url: str) -> str:
    try:
        import keyring
        token = keyring.get_password(KEYRING_SERVICE, base_url.strip().rstrip("/"))
        if token:
            return token
    except Exception:
        pass
    return os.environ.get("GITLAB_TOKEN", "")


def save_token(base_url: str, token: str) -> bool:
    """Stores the token in the OS credential store. Returns False if unavailable."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, base_url.strip().rstrip("/"), token)
        return True
    except Exception:
        return False


def delete_token(base_url: str) -> None:
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, base_url.strip().rstrip("/"))
    except Exception:
        pass
