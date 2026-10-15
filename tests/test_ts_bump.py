import tempfile
import subprocess
import shutil
import os
from pathlib import Path

hooks_dir = Path("hooks").resolve()
with tempfile.TemporaryDirectory() as td:
    proj = Path(td)
    subprocess.run(["git", "init"], cwd=proj, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=proj, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=proj, check=True)

    h_dir = proj / ".git" / "hooks"
    for h in ["pre-commit", "commit-msg", "post-commit"]:
        shutil.copy2(hooks_dir / h, h_dir / h)

    pkg = proj / "package.json"
    pkg.write_text('{\n  "name": "test-ts",\n  "version": "0.1.0"\n}\n', encoding="utf-8")
    (proj / "index.ts").write_text('console.log("hi");\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=proj, check=True)

    print("--- Test 1: git commit without force-interactive ---")
    res1 = subprocess.run(["git", "commit", "-m", "feat: initial test"], cwd=proj, capture_output=True, text=True)
    print("Return code:", res1.returncode)
    print("Stdout:", res1.stdout)
    print("Stderr:", res1.stderr)
    print("package.json:", pkg.read_text(encoding="utf-8"))

    print("\n--- Test 3: Check tty in bash hook when stdin/stdout are inherited/not piped ---")
    res3 = subprocess.run(
        ["C:\\Program Files\\Git\\bin\\bash.exe", "-c", "echo t0=$([ -t 0 ] && echo 1 || echo 0) t1=$([ -t 1 ] && echo 1 || echo 0) tty=$([ -e /dev/tty ] && echo 1 || echo 0)"],
        capture_output=True,
        text=True
    )
    print("res3:", res3.stdout.strip())
