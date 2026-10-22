"""색상과 글꼴을 브라우저에 보관하는 공개 데모 디자인 설정."""
from pathlib import Path
import streamlit as st


DEFAULT_THEME = '초록색'
THEME_ALIASES = {'하늘색': '파란색'}
STORAGE_KEY = 'pricesystem.color-theme.v1'
FONT_STORAGE_KEY = 'pricesystem.font.v1'
DEFAULT_FONT = 'pretendard'
FONTS = {
    'default': dict(label='시스템 폰트'),
    'pretendard': dict(label='Pretendard (기본)', family='PriceSystem Pretendard', filename='PretendardVariable.woff2'),
    'suit': dict(label='SUIT', family='PriceSystem SUIT', filename='SUIT-Variable.woff2'),
}
ROOT = Path(__file__).resolve().parents[1] / 'static'
SCOPE = 'body:has(.workspace-theme-marker):not(:has(#login-card-root))'
LIGHT = 'body:is([data-ps-theme="light"], :not([data-ps-theme]):has(.workspace-theme-marker[data-initial-theme="light"])):has(.workspace-theme-marker):not(:has(#login-card-root))'
FONT_SCOPE = 'body:is(:has(.workspace-theme-marker):not(:has(#login-card-root)), :has(#login-card-root))'

PALETTES = {
    '초록색': dict(action='#204e3e', hover='#173e30', ink='#ffffff', primary='#204e3e', primary_hover='#173e30', soft='#edf4ef',
                 sidebar='#153d32', active='#2a5141', border='#436354', muted='#c1d1c5', accent='#d4ed76', sidebar_ink='#f5f4ed', sidebar_accent='#d4ed76', brand_filter='none',
                 dark_primary='#ccdfca', dark_soft='#253d33', dark_action='#2f624c', dark_hover='#386d54', dark_ink='#ffffff'),
    '파란색': dict(action='#315780', hover='#29496f', ink='#ffffff', primary='#315780', primary_hover='#29496f', soft='#edf2f9',
                 sidebar='#203650', active='#304d6b', border='#56718e', muted='#c9d8eb', accent='#adc7e8', sidebar_ink='#f5f7fb', sidebar_accent='#bfd3ed', brand_filter='none',
                 dark_primary='#bfd3ed', dark_soft='#293c54', dark_action='#3e628d', dark_hover='#486b96', dark_ink='#ffffff'),
    '핑크색': dict(action='#944761', hover='#7c394f', ink='#ffffff', primary='#944761', primary_hover='#7c394f', soft='#fbf0f4',
                 sidebar='#4f2839', active='#6c384e', border='#a36c80', muted='#ead0da', accent='#e3b0c3', sidebar_ink='#fff7fa', sidebar_accent='#edc3d2', brand_filter='none',
                 dark_primary='#edc3d2', dark_soft='#452d39', dark_action='#984b67', dark_hover='#a25a75', dark_ink='#ffffff'),
    '검정색': dict(action='#25282c', hover='#151719', ink='#ffffff', primary='#25282c', primary_hover='#151719', soft='#f0f1f3',
                 sidebar='#191c20', active='#30353c', border='#535b66', muted='#cbd0d6', accent='#d1d5db', sidebar_ink='#f5f4ed', sidebar_accent='#d1d5db', brand_filter='none',
                 dark_primary='#e1e4e8', dark_soft='#30353c', dark_action='#d1d5db', dark_hover='#e5e7eb', dark_ink='#17191c'),
}


def theme_css(name):
    name = THEME_ALIASES.get(name, name)
    palette = PALETTES.get(name, PALETTES[DEFAULT_THEME])
    return f'''
{SCOPE} {{
  --ps-primary: {palette['dark_primary']}; --ps-primary-hover: {palette['accent']};
  --ps-primary-soft: {palette['dark_soft']};
  --ps-action: {palette['dark_action']}; --ps-action-hover: {palette['dark_hover']};
  --ps-action-ink: {palette['dark_ink']}; --ps-accent: {palette['accent']};
  --ps-selection: {palette['dark_action']}; --ps-selection-ink: {palette['dark_ink']};
  --ps-focus-outline: {palette['accent']}; --ps-focus-color: {palette['accent']}33;
  --ps-border-accent: {palette['accent']}80;
  --ps-info: {palette['dark_primary']}; --ps-info-bg: {palette['dark_soft']};
}}
{LIGHT} {{
  --ps-primary: {palette['primary']}; --ps-primary-hover: {palette['primary_hover']};
  --ps-primary-soft: {palette['soft']};
  --ps-action: {palette['action']}; --ps-action-hover: {palette['hover']}; --ps-action-ink: {palette['ink']};
  --ps-selection: {palette['primary']}; --ps-selection-ink: #ffffff;
  --ps-focus-outline: {palette['primary']}; --ps-focus-color: {palette['primary']}33;
  --ps-border-accent: {palette['primary']}66;
  --ps-info: {palette['primary']}; --ps-info-bg: {palette['soft']};
}}
{SCOPE} [data-testid="stSidebar"] {{
  --ps-text: {palette['sidebar_ink']}; --ps-muted: {palette['muted']}; --ps-text-muted: {palette['muted']};
  --ps-surface: {palette['sidebar']}; --ps-surface-muted: {palette['active']};
  --ps-border: {palette['border']}; --ps-border-strong: {palette['muted']};
  --ps-primary: {palette['sidebar_accent']}; --ps-primary-hover: {palette['sidebar_accent']};
  --ps-focus-outline: {palette['sidebar_accent']}; --ps-focus-color: {palette['sidebar_accent']}33;
  color: {palette['sidebar_ink']}; background: {palette['sidebar']}; border-right-color: {palette['border']};
}}
{SCOPE} [data-testid="stSidebar"] .sidebar-brand {{ border-bottom-color: {palette['border']}; }}
{SCOPE} [data-testid="stSidebar"] .sidebar-brand__mark {{ filter: {palette['brand_filter']}; }}
{SCOPE} [data-testid="stSidebar"] .sidebar-brand__name {{ color: {palette['sidebar_ink']}; }}
{SCOPE} [data-testid="stSidebar"] :is(.sidebar-brand__tagline, .sidebar-nav-title, .sidebar-account-label) {{ color: {palette['muted']}; }}
{SCOPE} [data-testid="stSidebar"] .demo-badge {{ color: {palette['sidebar_accent']}; border-color: {palette['border']}; }}
{SCOPE} [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button {{ color: {palette['sidebar_ink']}; }}
{SCOPE} [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button[kind="primary"]:not(:disabled) {{
  color: {palette['sidebar_ink']}; background: {palette['active']}; border-color: {palette['border']};
  box-shadow: inset 3px 0 {palette['sidebar_accent']};
}}
{SCOPE} [data-testid="stSidebar"] :is(.st-key-sidebar_home, div[class*="st-key-menu_open_"]) [data-testid="stButton"] button:hover {{
  color: {palette['sidebar_ink']}; background: {palette['active']};
}}
{SCOPE} [data-testid="stSidebar"] .st-key-sidebar_logout button {{ color: {palette['muted']}; }}
{SCOPE} [data-testid="stSidebar"] button:focus-visible {{ outline-color: {palette['sidebar_accent']}; }}
{SCOPE} [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {{ color: {palette['sidebar_ink']}; }}
'''


def login_theme_css(name):
    name = THEME_ALIASES.get(name, name)
    palette = PALETTES.get(name, PALETTES[DEFAULT_THEME])
    return f'''
body:has(#login-card-root) {{
  --ps-login-action: {palette['action']}; --ps-login-hover: {palette['hover']};
  --ps-login-deep: {palette['sidebar']}; --ps-login-accent: {palette['accent']};
  --ps-primary: {palette['primary']}; --ps-primary-soft: {palette['soft']};
  --ps-action: {palette['action']}; --ps-action-hover: {palette['hover']}; --ps-action-ink: {palette['ink']};
  --ps-focus-outline: {palette['primary']}; --ps-border-accent: {palette['primary']}66;
  --ps-text: #242a28; --ps-muted: #68716d; --ps-surface: #ffffff;
  --ps-surface-muted: #f1f4f2; --ps-surface-subtle: #f7f9f8;
  --ps-border: #dfe5e1; --ps-border-strong: #b9c4be;
}}
body:has(#login-card-root) [data-testid="stAppViewContainer"] {{
  --ps-login-forest: {palette['action']};
}}
body:has(#login-card-root) [data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover:not(:disabled) {{
  color: {palette['ink']}; background: {palette['hover']}; border-color: {palette['hover']};
}}
'''


def font_css(name):
    font = FONTS.get(name)
    if not font or name == 'default':
        return ''
    scope = FONT_SCOPE.replace('body:', f'body[data-ps-font="{name}"]:')
    return f'''
@font-face {{
  font-family: "{font['family']}";
  src: url("/app/static/fonts/{font['filename']}") format("woff2");
  font-weight: 100 900; font-style: normal; font-display: swap;
}}
{scope} {{ --ps-font-sans: "{font['family']}", sans-serif; }}
{scope} :is([data-testid="stApp"], [data-testid="stApp"] *, .ps-theme-tools, .ps-theme-tools *, .ps-login-art, .ps-login-art *, [data-baseweb="popover"], [data-baseweb="popover"] *, [role="listbox"], [role="listbox"] *)
:not([data-testid="stIconMaterial"], [data-testid^="stExpanderIcon"], [class*="material-symbols"], .material-icons, pre, pre *, code, code *, kbd, svg, svg *) {{
  font-family: var(--ps-font-sans) !important;
}}
'''.replace('\n:not(', ':not(')


def render_color_styles():
    # The browser attribute has higher specificity than the first-frame fallback.
    css = theme_css(DEFAULT_THEME) + login_theme_css(DEFAULT_THEME)
    for name in PALETTES:
        css += (theme_css(name) + login_theme_css(name)).replace('body:', f'body[data-ps-color="{name}"]:')
    css += ''.join(font_css(name) for name in FONTS)
    st.markdown(f'<style id="workbench-color-theme">{css}</style>', unsafe_allow_html=True)


def render_theme_picker():
    menu = st.components.v2.component(
        'workbench_color_menu',
        html=(ROOT / 'theme-menu.html').read_text(encoding='utf-8'),
        css=(ROOT / 'theme-menu.css').read_text(encoding='utf-8'),
        js=(ROOT / 'theme-menu.js').read_text(encoding='utf-8'),
        isolate_styles=False,
    )
    menu(key='workbench_color_menu', height=0, data={
        'themes': [{'name': name, 'color': palette['action'], 'ink': palette['ink']} for name, palette in PALETTES.items()],
        'defaultTheme': DEFAULT_THEME,
        'themeAliases': THEME_ALIASES,
        'storageKey': STORAGE_KEY,
        'fonts': [{'id': name, 'label': font['label']} for name, font in FONTS.items()],
        'defaultFont': DEFAULT_FONT,
        'fontStorageKey': FONT_STORAGE_KEY,
        'fontFaces': {name: f"/app/static/fonts/{font['filename']}"
                      for name, font in FONTS.items() if 'filename' in font},
    })


def render_preferences():
    """로그인과 업무 화면에 팔레트·글꼴 CSS와 설정 메뉴를 한 번씩 표시한다."""
    render_color_styles()
    render_theme_picker()
