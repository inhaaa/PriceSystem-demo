"""Safety and accessibility contracts for the PriceSystem brand surfaces."""

from pathlib import Path
import unittest
from xml.etree import ElementTree

from demo.visual_components import (
    home_action_card_html,
    login_panel_html,
    page_header_html,
    sidebar_brand_html,
)


ROOT = Path(__file__).resolve().parents[1]


class BrandDesignTests(unittest.TestCase):
    def test_login_identifies_the_product_without_a_promotional_hero(self):
        markup = login_panel_html("PriceSystem", "입찰가격 분석 · DEMO", "")
        self.assertIn('id="login-product-title">PriceSystem</h1>', markup)
        self.assertIn("입찰가격 분석 · DEMO", markup)
        self.assertIn("공고와 투찰 내역을 한곳에서 관리합니다.", markup)
        self.assertIn('aria-labelledby="login-product-title"', markup)
        self.assertIn('./app/static/brand-mark.svg', markup)
        self.assertNotIn("입찰의 기준을", markup)
        self.assertNotIn('login-panel__art', markup)
        self.assertNotIn('price-bands.svg', markup)
        self.assertNotIn('login-gem', markup)
        self.assertNotIn('드래그', markup)

    def test_shared_identity_is_local_vector_and_explicit_about_demo(self):
        sidebar = sidebar_brand_html()
        self.assertIn('./app/static/brand-mark.svg', sidebar)
        self.assertIn('PriceSystem', sidebar)
        self.assertIn('DEMO', sidebar)
        for name in ('assets/logo.svg', 'static/brand-mark.svg', 'static/price-bands.svg'):
            with self.subTest(asset=name):
                tree = ElementTree.fromstring((ROOT / name).read_text(encoding='utf-8'))
                self.assertTrue(tree.tag.endswith('svg'))
                self.assertFalse(any(node.tag.endswith('image') for node in tree.iter()))
                self.assertNotIn('http', ''.join(tree.itertext()))

    def test_every_dynamic_brand_text_stays_escaped(self):
        payload = '<script>alert("x")</script>'
        surfaces = (
            page_header_html(payload, payload, payload),
            login_panel_html(payload, payload, payload),
            home_action_card_html(payload, payload, payload),
        )
        for markup in surfaces:
            with self.subTest(markup=markup[:80]):
                self.assertNotIn('<script>', markup)
                self.assertIn('&lt;script&gt;', markup)
        self.assertIn('arrow_forward', surfaces[-1])

    def test_card_has_clear_direction_without_inventing_a_sequence(self):
        featured = home_action_card_html('가격 분석', '공고를 선택합니다.', ':material/analytics:', True)
        normal = home_action_card_html('공고 관리', '공고를 검토합니다.', ':material/list_alt:')
        self.assertIn('분석 시작', featured)
        self.assertIn('업무 바로가기', normal)
        self.assertIn('home-action-card__arrow', featured)
        self.assertNotIn('home-action-card__index', normal)

    def test_login_supports_keyboard_and_reduced_motion_without_external_fonts(self):
        css = (ROOT / 'assets/login.css').read_text(encoding='utf-8')
        self.assertIn(':focus-visible', css)
        self.assertIn('prefers-reduced-motion: reduce', css)
        self.assertIn('@media (max-width: 768px)', css)
        self.assertIn('> [data-testid="stLayoutWrapper"]:has([data-testid="stForm"])', css)
        self.assertIn('#173b31', css)
        self.assertIn('#f4f5f6', css)
        self.assertIn('#ffffff', css)
        self.assertNotIn('#d4ed76', css)
        self.assertNotIn('@import', css)


if __name__ == '__main__':
    unittest.main()
