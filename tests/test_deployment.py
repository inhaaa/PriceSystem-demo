"""Public image inputs and VPS isolation boundaries, without a Docker dependency."""
import fnmatch
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def in_build_context(relative, rules):
    included = True
    for rule in rules:
        if not rule or rule.startswith("#"):
            continue
        allow = rule.startswith("!")
        pattern = rule.removeprefix("!").rstrip("/")
        parts = relative.split("/")
        ancestors = ["/".join(parts[:index]) for index in range(1, len(parts) + 1)]
        if any(fnmatch.fnmatchcase(path, pattern) for path in ancestors):
            included = allow
    return included


class DeploymentTests(unittest.TestCase):
    def compose(self):
        path = ROOT / "compose.yaml"
        self.assertTrue(path.is_file(), "VPS Compose configuration is missing")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_demo_uses_its_own_project_and_only_a_loopback_port(self):
        config = self.compose()
        self.assertEqual(config["name"], "pricesys-demo")
        self.assertEqual(set(config["services"]), {"app"})
        app = config["services"]["app"]
        self.assertEqual(app["container_name"], "pricesys-demo")
        self.assertEqual(app["ports"], ["127.0.0.1:8502:8501"])
        self.assertEqual(app["restart"], "unless-stopped")
        self.assertNotIn("network_mode", app)
        self.assertNotIn("networks", config)

    def test_demo_mounts_no_host_data_and_inherits_no_production_environment(self):
        app = self.compose()["services"]["app"]
        for key in ("volumes", "volumes_from", "env_file", "secrets", "configs", "devices", "privileged"):
            self.assertNotIn(key, app, key)
        self.assertNotIn("environment", app)
        self.assertTrue(app["read_only"])
        self.assertEqual(app["cap_drop"], ["ALL"])
        self.assertIn("no-new-privileges:true", app["security_opt"])
        self.assertIn("mem_limit", app)
        self.assertIn("cpus", app)
        self.assertIn("max-size", app["logging"]["options"])
        self.assertIn("/_stcore/health", " ".join(app["healthcheck"]["test"]))

    def test_image_listens_inside_container_as_an_unprivileged_user(self):
        path = ROOT / "Dockerfile"
        self.assertTrue(path.is_file(), "VPS Dockerfile is missing")
        instructions = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        command = json.loads(next(line[4:] for line in instructions if line.startswith("CMD ")))
        self.assertEqual(command[:5], ["python", "-m", "streamlit", "run", "app.py"])
        self.assertIn("--server.address=0.0.0.0", command)
        self.assertIn("--server.port=8501", command)
        self.assertNotIn("--server.enableCORS=false", command)
        self.assertNotIn("--server.enableXsrfProtection=false", command)
        users = [line.split(maxsplit=1)[1] for line in instructions if line.startswith("USER ")]
        self.assertTrue(users)
        self.assertNotIn(users[-1], ("root", "0", "0:0"))
        self.assertFalse(any(line.startswith("COPY . ") or line.startswith("ADD ") for line in instructions))

    def test_build_context_includes_runtime_assets_but_excludes_secrets_and_databases(self):
        path = ROOT / ".dockerignore"
        self.assertTrue(path.is_file(), "Public-only Docker build boundary is missing")
        rules = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(next(rule for rule in rules if rule and not rule.startswith("#")), "*")
        public = (ROOT / "PUBLIC_FILES.txt").read_text(encoding="utf-8").splitlines()
        runtime = [p for p in public if p.startswith(("demo/", "assets/", "static/", ".streamlit/"))]
        for relative in ["app.py", "requirements.txt", *runtime]:
            self.assertTrue(in_build_context(relative, rules), relative)
        for relative in (".env", ".env.production", ".streamlit/secrets.toml", ".git/config",
                         ".local/backup.zip", ".venv/pyvenv.cfg", "data/production.db",
                         "demo/production.sqlite", "demo/secrets.py", "assets/private.key",
                         "static/credentials.json", "tests/test_app.py", "docs/images/login.png"):
            self.assertFalse(in_build_context(relative, rules), relative)


if __name__ == "__main__":
    unittest.main()
