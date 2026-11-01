"""Minimal GitHub REST client (stdlib only) plus secure token storage helpers."""
import json
import os
import re
import shutil
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request

KEYRING_SERVICE = "py-project-init-github"
DEFAULT_GITHUB_WEB = "https://github.com"
DEFAULT_GITHUB_API = "https://api.github.com"


class GitHubError(RuntimeError):
    """Raised for any failed GitHub API call. `status` holds the HTTP code if known."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _ssl_context() -> ssl.SSLContext:
    """Default verification, without Python 3.13+'s X509 strict mode for Enterprise CAs."""
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


class GitHubClient:
    def __init__(self, base_url: str = DEFAULT_GITHUB_WEB, token: str = "", timeout: float = 20.0):
        raw_url = (base_url or DEFAULT_GITHUB_WEB).strip().rstrip("/")
        if not raw_url:
            raw_url = DEFAULT_GITHUB_WEB
        parsed = urllib.parse.urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
        host = (parsed.hostname or "").lower()

        # Any URL targeting github.com (e.g. https://github.com or https://github.com/profile) uses api.github.com
        if host in ("github.com", "www.github.com", "api.github.com") or not host:
            self.web_url = DEFAULT_GITHUB_WEB
            self.api_url = DEFAULT_GITHUB_API
        else:
            if raw_url.endswith("/api/v3"):
                self.api_url = raw_url
                self.web_url = raw_url[:-7]
            else:
                self.web_url = raw_url
                self.api_url = f"{raw_url}/api/v3"

        self.token = token.strip()
        self.timeout = timeout
        self.ssl_context = _ssl_context()

    @staticmethod
    def _enc(path: str) -> str:
        return urllib.parse.quote(path.strip("/"), safe="")

    def _request(self, method: str, path: str, data: dict | None = None):
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "py-project-init",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            self.api_url + path,
            data=body,
            method=method,
            headers=headers,
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
                errors = payload.get("errors")
                if errors and isinstance(errors, list):
                    err_msgs = [err.get("message") or str(err) for err in errors if isinstance(err, dict)]
                    if err_msgs:
                        detail = f"{detail} ({', '.join(err_msgs)})"
            except (ValueError, AttributeError):
                pass
            raise GitHubError(f"HTTP {e.code}: {detail or e.reason}", status=e.code) from e
        except urllib.error.URLError as e:
            raise GitHubError(f"GitHub nicht erreichbar ({self.api_url}): {e.reason}") from e

    def current_user(self) -> dict:
        return self._request("GET", "/user")

    def get_repo(self, owner: str, name: str) -> dict | None:
        try:
            return self._request("GET", f"/repos/{self._enc(owner)}/{self._enc(name)}")
        except GitHubError as e:
            if e.status == 404:
                return None
            raise

    def create_repo(
        self,
        name: str,
        owner: str | None = None,
        default_branch: str = "main",
        visibility: str = "private",
        description: str = "",
    ) -> dict:
        """Creates the repository with an initial README so default branch exists server-side."""
        is_private = visibility in ("private", "internal")
        data = {
            "name": name,
            "description": description,
            "private": is_private,
            "auto_init": True,
        }
        # In GitHub API, visibility can also be explicitly passed if supported
        if visibility in ("private", "public", "internal"):
            data["visibility"] = visibility

        # If owner is specified, check if it's the current user or an organization
        if owner:
            curr_login = ""
            curr_name = ""
            try:
                u = self.current_user() or {}
                curr_login = u.get("login", "")
                curr_name = u.get("name", "")
            except Exception:
                pass

            is_self = (curr_login and owner.lower() == curr_login.lower()) or \
                      (curr_name and owner.lower() == curr_name.lower()) or \
                      (not re.match(r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$', owner))

            if not is_self and curr_login:
                path = f"/orgs/{self._enc(owner)}/repos"
                return self._request("POST", path, data)

        return self._request("POST", "/user/repos", data)

    def create_pull_request(
        self, owner: str, repo: str, source: str, target: str, title: str, body: str = ""
    ) -> dict:
        data = {
            "title": title,
            "head": source,
            "base": target,
            "body": body,
        }
        return self._request("POST", f"/repos/{self._enc(owner)}/{self._enc(repo)}/pulls", data)


# ── Token storage (Windows Credential Manager via keyring, env var, gh CLI fallback) ──

def load_token(base_url: str = DEFAULT_GITHUB_WEB) -> str:
    raw_url = (base_url or DEFAULT_GITHUB_WEB).strip().rstrip("/")
    candidates = [raw_url]

    parsed = urllib.parse.urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    host = (parsed.hostname or "").lower()
    if host in ("github.com", "www.github.com", "api.github.com"):
        if DEFAULT_GITHUB_WEB not in candidates:
            candidates.append(DEFAULT_GITHUB_WEB)

    try:
        import keyring
        for key in candidates:
            token = keyring.get_password(KEYRING_SERVICE, key)
            if token:
                return token
    except Exception:
        pass

    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env_token:
        return env_token.strip()

    # Fallback to local GitHub CLI if present and logged in
    try:
        if shutil.which("gh"):
            res = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
    except Exception:
        pass

    return ""


def save_token(base_url: str, token: str) -> bool:
    """Stores the token in the OS credential store. Returns False if unavailable."""
    raw_url = (base_url or DEFAULT_GITHUB_WEB).strip().rstrip("/")
    keys_to_save = [raw_url]
    parsed = urllib.parse.urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    host = (parsed.hostname or "").lower()
    if host in ("github.com", "www.github.com", "api.github.com"):
        if DEFAULT_GITHUB_WEB not in keys_to_save:
            keys_to_save.append(DEFAULT_GITHUB_WEB)

    try:
        import keyring
        success = False
        for k in keys_to_save:
            keyring.set_password(KEYRING_SERVICE, k, token)
            success = True
        return success
    except Exception:
        return False


def delete_token(base_url: str = DEFAULT_GITHUB_WEB) -> None:
    raw_url = (base_url or DEFAULT_GITHUB_WEB).strip().rstrip("/")
    keys_to_delete = [raw_url]
    parsed = urllib.parse.urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    host = (parsed.hostname or "").lower()
    if host in ("github.com", "www.github.com", "api.github.com"):
        if DEFAULT_GITHUB_WEB not in keys_to_delete:
            keys_to_delete.append(DEFAULT_GITHUB_WEB)

    try:
        import keyring
        for k in keys_to_delete:
            try:
                keyring.delete_password(KEYRING_SERVICE, k)
            except Exception:
                pass
    except Exception:
        pass
