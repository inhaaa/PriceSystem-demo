"""자동배포가 전용 서비스로만 실행되고 부팅 후 재개되는지 확인한다."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AutoDeployUnitTests(unittest.TestCase):
    def test_timer_runs_after_boot_and_waits_between_finished_runs(self):
        path = ROOT / "deploy/pricesys-demo-auto.timer"
        self.assertTrue(path.is_file(), "자동배포 timer가 필요합니다")
        unit = path.read_text(encoding="utf-8")
        self.assertIn("OnBootSec=2min", unit)
        self.assertIn("OnUnitInactiveSec=60s", unit)
        self.assertIn("WantedBy=timers.target", unit)

    def test_service_uses_installed_updater_and_never_restarts_shared_services(self):
        path = ROOT / "deploy/pricesys-demo-auto.service"
        self.assertTrue(path.is_file(), "데모 전용 자동배포 service가 필요합니다")
        unit = path.read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", unit)
        self.assertIn("ExecStart=/usr/bin/python3 /usr/local/lib/pricesys-demo/auto_deploy.py", unit)
        self.assertNotIn("/srv/pricesys-demo/deploy/auto_deploy.py", unit)
        self.assertNotIn("ExecStartPre=", unit)
        self.assertNotIn("ExecStop=", unit)
        self.assertNotIn("caddy", unit.lower())
        self.assertNotIn("restart docker", unit.lower())


if __name__ == "__main__":
    unittest.main()
