import subprocess
import tempfile
import unittest
from pathlib import Path

from py_project_init.core.generator import TemplateManager
from py_project_init.core.gitlab import GitLabClient, GitLabError


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def _make_fake_client(server_root: Path, existing: dict | None = None):
    """Builds a fake GitLab client whose 'repositories' are local bare repos."""
    calls: dict[str, list] = {"create_project": [], "merge_requests": []}

    class FakeClient:
        def __init__(self, base_url, token):
            self.base_url, self.token = base_url, token

        def current_user(self):
            return {"username": "droesch"}

        def get_namespace_id(self, namespace):
            return 42

        def get_project(self, full_path):
            return existing

        def create_project(self, name, namespace_id, default_branch, visibility="private", description=""):
            calls["create_project"].append((name, namespace_id, default_branch, visibility))
            bare = server_root / f"{name}.git"
            subprocess.run(["git", "init", "--bare", "-b", default_branch, str(bare)], check=True, capture_output=True)
            # Simulate GitLab's initialize_with_readme commit
            seed = server_root / "seed"
            subprocess.run(["git", "clone", str(bare), str(seed)], check=True, capture_output=True)
            (seed / "README.md").write_text("# placeholder\n", encoding="utf-8")
            _git(seed, "add", ".")
            _git(seed, "-c", "user.name=GitLab", "-c", "user.email=gl@example.com", "commit", "-m", "Initial commit")
            _git(seed, "push", "origin", f"HEAD:{default_branch}")
            return {"id": 7, "http_url_to_repo": str(bare), "ssh_url_to_repo": str(bare),
                    "web_url": "https://gitlab.example/x", "default_branch": default_branch, "empty_repo": False}

        def create_merge_request(self, project_id, source, target, title):
            calls["merge_requests"].append((project_id, source, target))
            return {"web_url": "https://gitlab.example/x/-/merge_requests/1"}

    return FakeClient, calls


class TestGitLabIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.server = self.root / "server"
        self.server.mkdir()
        templates = Path(__file__).resolve().parent.parent / "templates"
        self.manager = TemplateManager(templates)
        # Minimal template without uv/npm hooks to keep the test fast and offline
        tpl = self.root / "tpls" / "mini"
        tpl.mkdir(parents=True)
        (tpl / "template.yaml").write_text("name: Mini\nlanguage: Universal\n", encoding="utf-8")
        (tpl / "README.md.j2").write_text("# {{ project_name }}\n", encoding="utf-8")
        self.manager.add_custom_dir(self.root / "tpls")

    def tearDown(self):
        self.tmp.cleanup()

    def _context(self, **gitlab):
        cfg = {"enabled": True, "url": "https://gitlab.example", "token": "t", "namespace": "development",
               "work_branch": "develop", "create_mr": True, **gitlab}
        return {"project_name": "cloud-net", "project_slug": "cloud_net", "description": "",
                "default_branch": "main", "gitlab": cfg}

    def _generate(self, fake, context):
        self.manager.gitlab_client_factory = fake
        target = self.root / "work" / "cloud-net"
        # Ensure commits work in CI environments without global git identity
        env_cfg = self.root / "gitconfig"
        env_cfg.write_text("[user]\n\tname = Test\n\temail = t@example.com\n", encoding="utf-8")
        import os
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
        self.assertEqual(calls["create_project"], [("cloud-net", 42, "main", "private")])
        self.assertEqual(_git(target, "branch", "--show-current"), "develop")
        # The project commit sits on top of the server's README commit -> MR is mergeable
        self.assertEqual(_git(target, "rev-parse", "develop~1"), _git(target, "rev-parse", "origin/main"))
        self.assertEqual(_git(target, "rev-parse", "develop"), _git(target, "rev-parse", "origin/develop"))
        self.assertEqual(_git(target, "rev-parse", "--abbrev-ref", "main@{upstream}"), "origin/main")
        self.assertEqual((target / "README.md").read_text(encoding="utf-8"), "# cloud-net")
        self.assertEqual(calls["merge_requests"], [(7, "develop", "main")])

    def test_existing_project_with_commits_is_left_untouched(self):
        existing = {"id": 1, "empty_repo": False, "default_branch": "main", "http_url_to_repo": "x"}
        fake, calls = _make_fake_client(self.server, existing=existing)
        target, problems = self._generate(fake, self._context())

        self.assertEqual(len(problems), 1)
        self.assertIn("existiert bereits", problems[0])
        self.assertEqual(calls["create_project"], [])
        self.assertEqual(_git(target, "remote"), "")
        self.assertEqual(_git(target, "branch", "--show-current"), "main")

    def test_existing_empty_project_pushes_default_and_work_branch(self):
        bare = self.server / "empty.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        existing = {"id": 3, "empty_repo": True, "default_branch": None,
                    "http_url_to_repo": str(bare), "web_url": "https://gitlab.example/empty"}
        fake, calls = _make_fake_client(self.server, existing=existing)
        target, problems = self._generate(fake, self._context())

        self.assertEqual(problems, [])
        self.assertEqual(calls["create_project"], [])
        heads = _git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        self.assertEqual(sorted(heads.split()), ["develop", "main"])
        self.assertEqual(_git(target, "branch", "--show-current"), "develop")
        # Same commit on both branches -> no MR needed
        self.assertEqual(calls["merge_requests"], [])

    def test_gitlab_api_error_keeps_local_project(self):
        class Failing:
            def __init__(self, *_):
                pass

            def current_user(self):
                raise GitLabError("HTTP 401: Unauthorized", 401)

        target, problems = self._generate(Failing, self._context(namespace=""))
        self.assertEqual(len(problems), 1)
        self.assertIn("401", problems[0])
        self.assertTrue(_git(target, "log", "--oneline"))

    def test_without_gitlab_uses_configured_default_branch(self):
        ctx = self._context()
        ctx["gitlab"] = {"enabled": False}
        target, problems = self._generate(None, ctx)
        self.assertEqual(problems, [])
        self.assertEqual(_git(target, "branch", "--show-current"), "main")


class TestGitLabClient(unittest.TestCase):
    def test_http_roundtrip_and_error_message(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append((self.path, self.headers["PRIVATE-TOKEN"], body))
                if body["name"] == "taken":
                    self._send(400, {"message": {"name": ["has already been taken"]}})
                else:
                    self._send(201, {"id": 5, "default_branch": "main"})

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
            client = GitLabClient(f"http://127.0.0.1:{server.server_port}", "secret")
            project = client.create_project("demo", 42, "main", "internal")
            self.assertEqual(project["id"], 5)
            path, token, body = seen[0]
            self.assertEqual((path, token), ("/api/v4/projects", "secret"))
            self.assertTrue(body["initialize_with_readme"])
            self.assertEqual((body["namespace_id"], body["default_branch"], body["visibility"]), (42, "main", "internal"))
            with self.assertRaises(GitLabError) as ctx:
                client.create_project("taken", None, "main")
            self.assertEqual(ctx.exception.status, 400)
            self.assertIn("already been taken", str(ctx.exception))
        finally:
            server.shutdown()

    def test_api_url_and_path_encoding(self):
        client = GitLabClient("https://gitlab.data-al.de/", " abc ")
        self.assertEqual(client.api_url, "https://gitlab.data-al.de/api/v4")
        self.assertEqual(client.token, "abc")
        self.assertEqual(client._enc("/development/cloud-net/"), "development%2Fcloud-net")


if __name__ == "__main__":
    unittest.main()
