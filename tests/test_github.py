import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from py_project_init.core.generator import TemplateManager
from py_project_init.core.github import GitHubClient, GitHubError, load_token, save_token, delete_token


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def _make_fake_client(server_root: Path, existing: dict | None = None):
    """Builds a fake GitHub client whose 'repositories' are local bare repos."""
    calls: dict[str, list] = {"create_repo": [], "pull_requests": []}

    class FakeClient:
        def __init__(self, base_url="", token=""):
            self.base_url, self.token = base_url, token

        def current_user(self):
            return {"login": "octocat"}

        def get_repo(self, owner, name):
            return existing

        def create_repo(self, name, owner=None, default_branch="main", visibility="private", description=""):
            calls["create_repo"].append((name, owner, default_branch, visibility))
            bare = server_root / f"{name}.git"
            subprocess.run(["git", "init", "--bare", "-b", default_branch, str(bare)], check=True, capture_output=True)
            # Simulate GitHub's auto_init commit with initial README
            seed = server_root / "seed"
            subprocess.run(["git", "clone", str(bare), str(seed)], check=True, capture_output=True)
            (seed / "README.md").write_text("# placeholder\n", encoding="utf-8")
            _git(seed, "add", ".")
            _git(seed, "-c", "user.name=GitHub", "-c", "user.email=gh@example.com", "commit", "-m", "Initial commit")
            _git(seed, "push", "origin", f"HEAD:{default_branch}")
            return {
                "id": 101,
                "clone_url": str(bare),
                "ssh_url": str(bare),
                "html_url": f"https://github.com/{owner or 'octocat'}/{name}",
                "default_branch": default_branch,
                "empty_repo": False,
                "size": 42,
            }

        def create_pull_request(self, owner, repo, source, target, title, body=""):
            calls["pull_requests"].append((owner, repo, source, target))
            return {"html_url": f"https://github.com/{owner}/{repo}/pull/1", "number": 1}

    return FakeClient, calls


class TestGitHubIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.server = self.root / "server"
        self.server.mkdir()
        templates = Path(__file__).resolve().parent.parent / "templates"
        self.manager = TemplateManager(templates)
        # Minimal template to keep test fast and offline
        tpl = self.root / "tpls" / "mini"
        tpl.mkdir(parents=True)
        (tpl / "template.yaml").write_text("name: Mini\nlanguage: Universal\n", encoding="utf-8")
        (tpl / "README.md.j2").write_text("# {{ project_name }}\n", encoding="utf-8")
        self.manager.add_custom_dir(self.root / "tpls")

    def tearDown(self):
        self.tmp.cleanup()

    def _context(self, **github):
        cfg = {
            "enabled": True,
            "url": "https://github.com",
            "token": "ghp_secret",
            "owner": "my-org",
            "work_branch": "develop",
            "create_pr": True,
            **github,
        }
        return {
            "project_name": "hub-net",
            "project_slug": "hub_net",
            "description": "Test description",
            "default_branch": "main",
            "github": cfg,
        }

    def _generate(self, fake, context):
        self.manager.github_client_factory = fake
        target = self.root / "work" / "hub-net"
        # Ensure commits work in environments without global git identity
        env_cfg = self.root / "gitconfig"
        env_cfg.write_text("[user]\n\tname = Test\n\temail = t@example.com\n", encoding="utf-8")
        old = os.environ.get("GIT_CONFIG_GLOBAL")
        os.environ["GIT_CONFIG_GLOBAL"] = str(env_cfg)
        try:
            problems = self.manager.generate(target, "mini", context, log_callback=lambda _m: None)
        finally:
            if old is None:
                os.environ.pop("GIT_CONFIG_GLOBAL", None)
            else:
                os.environ["GIT_CONFIG_GLOBAL"] = old
        return target, problems

    def test_new_project_is_based_on_server_default_branch(self):
        fake, calls = _make_fake_client(self.server)
        target, problems = self._generate(fake, self._context())

        self.assertEqual(problems, [])
        self.assertEqual(calls["create_repo"], [("hub-net", "my-org", "main", "private")])
        self.assertEqual(_git(target, "branch", "--show-current"), "develop")
        # The project commit sits on top of the server's README commit -> PR is cleanly mergeable
        self.assertEqual(_git(target, "rev-parse", "develop~1"), _git(target, "rev-parse", "origin/main"))
        self.assertEqual(_git(target, "rev-parse", "develop"), _git(target, "rev-parse", "origin/develop"))
        self.assertEqual(_git(target, "rev-parse", "--abbrev-ref", "main@{upstream}"), "origin/main")
        self.assertEqual((target / "README.md").read_text(encoding="utf-8"), "# hub-net")
        self.assertEqual(calls["pull_requests"], [("my-org", "hub-net", "develop", "main")])

    def test_existing_repo_with_commits_is_left_untouched(self):
        existing = {"id": 1, "empty_repo": False, "size": 150, "default_branch": "main", "clone_url": "x"}
        fake, calls = _make_fake_client(self.server, existing=existing)
        target, problems = self._generate(fake, self._context())

        self.assertEqual(len(problems), 1)
        self.assertIn("existiert bereits und enthält Commits", problems[0])
        self.assertEqual(calls["create_repo"], [])
        self.assertEqual(_git(target, "remote"), "")
        self.assertEqual(_git(target, "branch", "--show-current"), "main")

    def test_existing_empty_repo_pushes_default_and_work_branch(self):
        bare = self.server / "empty.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        existing = {
            "id": 2,
            "empty_repo": True,
            "size": 0,
            "default_branch": None,
            "clone_url": str(bare),
            "html_url": "https://github.com/my-org/empty",
        }
        fake, calls = _make_fake_client(self.server, existing=existing)
        target, problems = self._generate(fake, self._context())

        self.assertEqual(problems, [])
        self.assertEqual(calls["create_repo"], [])
        heads = _git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        self.assertEqual(sorted(heads.split()), ["develop", "main"])
        self.assertEqual(_git(target, "branch", "--show-current"), "develop")
        # Same commit on both branches -> no PR needed
        self.assertEqual(calls["pull_requests"], [])

    def test_github_api_error_keeps_local_project(self):
        class Failing:
            def __init__(self, *_):
                pass

            def current_user(self):
                raise GitHubError("HTTP 401: Bad credentials", 401)

        target, problems = self._generate(Failing, self._context(owner=""))
        self.assertEqual(len(problems), 1)
        self.assertIn("401", problems[0])
        self.assertTrue(_git(target, "log", "--oneline"))

    def test_without_github_uses_configured_default_branch(self):
        ctx = self._context()
        ctx["github"] = {"enabled": False}
        target, problems = self._generate(None, ctx)
        self.assertEqual(problems, [])
        self.assertEqual(_git(target, "branch", "--show-current"), "main")


class TestGitHubClient(unittest.TestCase):
    def test_url_resolution(self):
        client_pub = GitHubClient("https://github.com", "tok")
        self.assertEqual(client_pub.web_url, "https://github.com")
        self.assertEqual(client_pub.api_url, "https://api.github.com")

        client_ent = GitHubClient("https://github.mycompany.de", "tok")
        self.assertEqual(client_ent.web_url, "https://github.mycompany.de")
        self.assertEqual(client_ent.api_url, "https://github.mycompany.de/api/v3")

        client_ent_v3 = GitHubClient("https://github.mycompany.de/api/v3", "tok")
        self.assertEqual(client_ent_v3.web_url, "https://github.mycompany.de")
        self.assertEqual(client_ent_v3.api_url, "https://github.mycompany.de/api/v3")

    def test_http_roundtrip_and_headers(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        requests_received = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                requests_received.append((self.command, self.path, dict(self.headers), None))
                if self.path == "/user":
                    self._send(200, {"login": "octocat", "id": 1})
                elif self.path == "/repos/octocat/notfound":
                    self._send(404, {"message": "Not Found"})
                else:
                    self._send(404, {})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests_received.append((self.command, self.path, dict(self.headers), body))
                if body.get("name") == "already-taken":
                    self._send(422, {"message": "Validation Failed", "errors": [{"message": "name already exists"}]})
                else:
                    self._send(201, {"id": 10, "default_branch": "main", "clone_url": "x"})

            def _send(self, code, payload):
                raw = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            client = GitHubClient(f"http://127.0.0.1:{server.server_port}", "secret_token")
            # Override api_url directly for the test server
            client.api_url = f"http://127.0.0.1:{server.server_port}"

            user = client.current_user()
            self.assertEqual(user["login"], "octocat")
            cmd, path, headers, _ = requests_received[0]
            self.assertEqual(cmd, "GET")
            self.assertEqual(headers["Authorization"], "Bearer secret_token")
            self.assertEqual(headers["User-Agent"], "py-project-init")
            self.assertEqual(headers["Accept"], "application/vnd.github+json")

            repo = client.create_repo("new-app", owner=None, visibility="private")
            self.assertEqual(repo["id"], 10)

            not_found = client.get_repo("octocat", "notfound")
            self.assertIsNone(not_found)

            with self.assertRaises(GitHubError) as ctx:
                client.create_repo("already-taken", owner=None)
            self.assertEqual(ctx.exception.status, 422)
            self.assertIn("name already exists", str(ctx.exception))
        finally:
            server.shutdown()

    def test_token_loading_fallbacks(self):
        old_gh = os.environ.get("GITHUB_TOKEN")
        old_ght = os.environ.get("GH_TOKEN")
        try:
            os.environ["GITHUB_TOKEN"] = "gh_from_env_var"
            token = load_token("https://unique-unconfigured-url.test")
            self.assertEqual(token, "gh_from_env_var")

            del os.environ["GITHUB_TOKEN"]
            os.environ["GH_TOKEN"] = "gh_from_gh_token"
            token = load_token("https://unique-unconfigured-url.test")
            self.assertEqual(token, "gh_from_gh_token")
        finally:
            if old_gh is not None:
                os.environ["GITHUB_TOKEN"] = old_gh
            else:
                os.environ.pop("GITHUB_TOKEN", None)
            if old_ght is not None:
                os.environ["GH_TOKEN"] = old_ght
            else:
                os.environ.pop("GH_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
