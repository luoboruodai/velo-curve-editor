#!/usr/bin/env python3
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / 'VeloAE'
checks = 0


def check(condition, message):
    global checks
    assert condition, message
    checks += 1
    print(f'ok {checks} - {message}')


class PanelHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.parents = {}
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get('id')
        if element_id:
            parent = self.stack[-1] if self.stack else None
            self.parents[element_id] = parent
        if tag == 'script' and attributes.get('src'):
            self.scripts.append(attributes['src'])
        if tag not in {'meta', 'link', 'input', 'br', 'hr', 'img', 'source', 'path', 'circle'}:
            self.stack.append((tag, element_id))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


html = (PANEL / 'index.html').read_text(encoding='utf-8')
css = (PANEL / 'css' / 'style.css').read_text(encoding='utf-8')
main = (PANEL / 'js' / 'main.js').read_text(encoding='utf-8')
theme = (PANEL / 'js' / 'theme.js').read_text(encoding='utf-8')
parsed = PanelHTML()
parsed.feed(html)

check(parsed.parents['appContainer'] == parsed.parents['settingsModal'], 'app and settings modal share the same parent')
check(parsed.parents['settingsModal'] == ('body', None), 'settings modal is a direct body child')
check(parsed.scripts.index('js/theme.js') < parsed.scripts.index('js/main.js'), 'theme module loads before main.js')
check((PANEL / 'js' / 'theme.js').is_file(), 'theme module exists as a local resource')
check('document.documentElement' in theme, 'theme tokens target the common document root')
check('window.VeloTheme = { apply };' in theme, 'the public theme API is exposed')
check('MutationObserver' not in theme and 'setInterval' not in theme and 'setTimeout' not in theme, 'theme updates use no observer or polling')
check("root.style.getPropertyValue(name) !== value" in theme, 'unchanged token values are not written')
check('--preset-box-size' not in theme, 'layout sizing stays out of the shared theme module')
controls = main.split('function updateControls()', 1)[1].split('function updatePresetSelection()', 1)[0]
check(controls.count('window.VeloTheme.apply(settings);') == 1, 'main delegates shared theme updates once per control update')
check("setStyle(ui.app, '--preset-box-size'" in controls, 'main keeps preset sizing on the app container')
for token in ('--btn-active-bg', '--accent-soft', '--btn-active-hover-bg', '--curve-color', '--panel-bg'):
    check(f"setStyle(ui.app, '{token}'" not in controls, f'app-scoped write removed for {token}')
    check(f"'{token}'" in theme, f'root theme token: {token}')
root_rule = re.search(r':root\s*\{([^}]*)\}', css, re.S).group(1)
app_rule = re.search(r'^\.app-container\s*\{([^}]*)\}', css, re.M | re.S).group(1)
check('--preset-box-size' not in root_rule, 'root has no layout sizing token')
check('--preset-box-size: 80px' in app_rule, 'app container owns the default preset size')


def declarations(selector):
    match = re.search(r'^' + re.escape(selector) + r'\s*\{([^}]*)\}', css, re.M | re.S)
    assert match, f'missing rule: {selector}'
    return match.group(1)


for selector in ('.settings-tab.active', '.switch input:checked + .switch-track', '.primary-btn'):
    check('background: var(--btn-active-bg)' in declarations(selector), f'active accent: {selector}')
for selector in ('.settings-tab.active:hover', '.switch input:checked:hover + .switch-track', '.settings-panel .primary-btn:hover'):
    check('background: var(--btn-active-hover-bg)' in declarations(selector), f'themed hover: {selector}')
focus = declarations('button:focus-visible, .preset-item:focus-visible, select:focus-visible, input:focus-visible')
check('border-color: var(--btn-active-bg)' in focus and 'box-shadow: 0 0 0 1px var(--btn-active-bg)' in focus, 'control focus follows the active accent')
check('box-shadow: 0 0 0 1px var(--btn-active-bg)' in declarations('.switch input:focus-visible + .switch-track'), 'switch focus follows the active accent')
check('#303030' in declarations('.settings-tabs'), 'tab surface remains neutral')
check('#353535' in declarations('fieldset'), 'settings groups remain neutral')
check('#383838' in declarations('.settings-footer'), 'settings footer remains neutral')
check('border-radius: 8px' in declarations('.settings-panel'), 'settings panel radius is preserved')
check('border-radius: 4px' in declarations('.settings-tab'), 'tab radius is preserved')

row = declarations('.setting-row')
check('min-width: 0' in row and 'flex-wrap: wrap' in row, 'long setting rows can shrink and wrap')
check('overflow-wrap: anywhere' in row and 'line-height: 1.4' in row, 'long setting labels wrap without fixed-height clipping')
buttons = declarations('.settings-panel button')
check('min-width: 0' in buttons and 'white-space: normal' in buttons and 'overflow-wrap: anywhere' in buttons, 'settings buttons support translated text wrapping')
check('height: auto' in declarations('.settings-panel .secondary-btn'), 'settings buttons can grow for wrapped labels')
check('flex-wrap: wrap' in declarations('.settings-button-row'), 'settings action rows wrap at narrow widths')
check('flex-wrap: wrap' in declarations('.settings-footer'), 'settings footer actions wrap at narrow widths')
tab = declarations('.settings-tab')
check('min-width: 0' in tab and 'height: auto' in tab and 'white-space: nowrap' in tab, 'compact tab labels stay on one line')
check('min-width: 0' in declarations('fieldset'), 'fieldsets do not enforce a min-content overflow width')
select = declarations('.settings-page select')
check('min-width: 0' in select and 'max-width: 100%' in select, 'selects shrink inside narrow setting rows')
slider = declarations('.setting-slider')
check('min-width: 0' in slider and 'max-width: 100%' in slider and 'flex: 0 1 170px' in slider, 'setting sliders shrink within their container')
preset_list = declarations('.preset-list')
check('grid-template-columns: repeat(2, var(--preset-box-size))' in preset_list, 'preset sidebar keeps two fixed-size columns')
check('padding: 8px' in preset_list and 'gap: 8px' in preset_list, 'preset cards have consistent outer and inner spacing')
check('grid-auto-rows: var(--preset-box-size)' in preset_list, 'preset row heights preserve the intended gap')
check('white-space: nowrap' in declarations('.setting-slider output'), 'numeric and percentage outputs remain on one line')
check('overflow-x: auto' in preset_list and 'scrollbar-gutter: stable' in preset_list, 'narrow sidebars scroll instead of compressing cards')
check('Math.max(112, settings.presetSize * 2 + 30)' in controls, 'preset panel width includes cards, spacing and scrollbar gutter')
horizontal_cards = declarations('.preset-bottom .preset-item, .preset-top .preset-item')
check('flex: 0 0 var(--preset-box-size)' in horizontal_cards and 'height: var(--preset-box-size)' in horizontal_cards, 'top and bottom preset cards keep their fixed sizing')
check('overflow-x: auto' in declarations('.preset-bottom .preset-list, .preset-top .preset-list'), 'horizontal preset overflow remains scrollable')

print(f'1..{checks}')
