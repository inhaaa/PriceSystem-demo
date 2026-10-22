"""실무 화면의 테마 전달·접근성·반응형 디자인 계약."""
from pathlib import Path
import re
import unittest

from demo.workspace_theme import SHEET_THEME_BRIDGE_JS, WORKSPACE_THEME_CSS, workspace_theme_marker_html


ROOT = Path(__file__).resolve().parents[1]


def contrast_ratio(first: str, second: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
                  for value in channels]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


class WorkspaceDesignTests(unittest.TestCase):
    def test_theme_bridge_copies_native_sheet_palette_without_decorative_mount(self):
        for source in ("--st-background-color", "--st-secondary-background-color", "--st-text-color",
                       "--st-border-color", "--st-dataframe-border-color", "--st-dataframe-header-background-color"):
            self.assertIn(source, SHEET_THEME_BRIDGE_JS)
        self.assertIn("new MutationObserver(sync)", SHEET_THEME_BRIDGE_JS)
        self.assertIn("observer.disconnect()", SHEET_THEME_BRIDGE_JS)
        self.assertIn("target.dataset.psTheme", SHEET_THEME_BRIDGE_JS)
        self.assertNotIn("mountWorkspaceGlimmer", SHEET_THEME_BRIDGE_JS)
        self.assertNotIn("requestAnimationFrame", SHEET_THEME_BRIDGE_JS)
        self.assertIn('data-initial-theme="dark"', workspace_theme_marker_html("dark"))
        self.assertIn('data-initial-theme="light"', workspace_theme_marker_html(None))

    def test_workspace_uses_opaque_surfaces_and_no_crystal_or_particle_background(self):
        for decoration in ("workspace-crystal", "diamond-chamber", "prism-bling", "radial-gradient", "--ps-glass"):
            self.assertNotIn(decoration, WORKSPACE_THEME_CSS)
        self.assertIn("background: var(--ps-surface);", WORKSPACE_THEME_CSS)
        self.assertIn(".st-key-workspace_surface", WORKSPACE_THEME_CSS)
        self.assertNotIn("__SCOPE__", WORKSPACE_THEME_CSS)

    def test_both_palettes_keep_button_and_body_text_readable(self):
        source = (ROOT / "demo/workspace_theme.py").read_text(encoding="utf-8")
        palettes = re.findall(r'__(?:SCOPE|LIGHT)__\s*\{([^}]+)\}', source)
        self.assertEqual(len(palettes), 2)
        for block in palettes:
            palette = dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', block))
            for foreground, background in (("--ps-text", "--ps-surface"),
                                           ("--ps-muted", "--ps-surface-muted"),
                                           ("--ps-action-ink", "--ps-action"),
                                           ("--ps-action-ink", "--ps-action-hover")):
                with self.subTest(foreground=foreground, background=background):
                    self.assertIn(foreground, palette)
                    self.assertIn(background, palette)
                    self.assertGreaterEqual(contrast_ratio(palette[foreground], palette[background]), 4.5)
        self.assertIn("--ps-accent: #d4ed76;", source)
        self.assertIn("--ps-canvas: #f5f6f5;", source)
        self.assertIn("--ps-text: #242a28;", source)

    def test_schedule_and_calculation_panels_share_workbench_design_contract(self):
        css = (ROOT / "assets/demo.css").read_text(encoding="utf-8")
        for component in ("workspace-utility", "workbench-heading", "schedule-day-heading",
                          "schedule-notice", "schedule-notice__amount", "schedule-status",
                          "workbench-facts", "recommendation-panel", "recommendation-panel__amount"):
            with self.subTest(component=component):
                self.assertIn("." + component, css)
        self.assertIn("font-variant-numeric: tabular-nums;", css)
        self.assertIn("text-align: right;", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("cursor: not-allowed;", css)

    def test_horizontal_tabs_and_mobile_sidebar_remain_available(self):
        css = (ROOT / "assets/demo.css").read_text(encoding="utf-8")
        for contract in (".st-key-internal_tab_bar", "st-key-tab_close_", "flex-wrap: nowrap;",
                         "overflow-x: auto;", '[data-testid="stSidebar"][aria-expanded="false"]'):
            self.assertIn(contract, css)
        self.assertIn("@media (max-width: 768px)", WORKSPACE_THEME_CSS)
        self.assertIn('[data-testid="stSidebarCollapsedControl"]', WORKSPACE_THEME_CSS)


if __name__ == "__main__":
    unittest.main()
