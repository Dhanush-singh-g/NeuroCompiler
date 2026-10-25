"""Optional real-browser acceptance check for the running live app.

Requires Playwright and Chromium. Executes only the bundled trusted examples.
Writes new records under ignored .presentation/, never research results/.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000/')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    args = parser.parse_args()
    output = ROOT/'.presentation/browser'
    output.mkdir(parents=True, exist_ok=True)
    errors, checks, requests = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1440,'height':1050}, device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'favicon' not in m.text else None)
        page.on('request',lambda r:requests.append(r.url))
        page.goto(args.url,wait_until='networkidle')
        expect(page.locator('#connection')).to_contain_text('ready')
        page.locator('#policy-mode').select_option('legacy')
        page.locator('#example').select_option('sieve')
        expect(page.locator('#example')).to_have_value('sieve')
        expect(page.locator('#compare')).to_be_disabled()
        expect(page.locator('#session-scorecard')).to_contain_text('Input/model pairs assessed')
        page.locator('.pass-guide summary').click()
        expect(page.locator('.pass-guide')).to_contain_text('Removes calculations')
        page.locator('.pass-guide summary').click()
        page.screenshot(path=str(output/'initial-desktop.png'),full_page=True)
        page.locator('#analyze').click()
        expect(page.locator('#decision-content')).to_be_visible(timeout=60000)
        expect(page.locator('#decision-content')).to_contain_text('O3 → GVN → DCE')
        expect(page.locator('#decision-content')).to_contain_text('no program execution')
        expect(page.locator('#decision-content')).to_contain_text('APPROVED',ignore_case=True)
        expect(page.locator('.contribution')).to_have_count(6)
        with page.expect_download() as downloaded:
            page.locator('#download-json').click()
        analysis = json.loads(Path(downloaded.value.path()).read_text())
        assert analysis['native_execution'] is False
        assert analysis['measurement'] is None
        page.screenshot(path=str(output/'decision-desktop.png'),full_page=True)
        checks.append('Real C compilation, portable-model decision, attribution, and analysis JSON export')
        page.locator('[data-tab="ir"]').click()
        expect(page.locator('#ir-base')).to_contain_text('define',timeout=10000)
        expect(page.locator('#ir-candidate')).to_contain_text('define')
        page.locator('#ir-choice').select_option('mem2reg_loop_rotate_licm_O3')
        expect(page.locator('#ir-title')).to_contain_text('Loop preparation')
        page.locator('#ir-choice').select_option('O1')
        expect(page.locator('#ir-title')).to_contain_text('O1')
        expect(page.locator('#ir-candidate')).to_contain_text('define')
        page.locator('[data-tab="benchmark"]').click()
        expect(page.locator('#compare')).to_be_disabled()
        page.locator('#trusted').check()
        expect(page.locator('#compare')).to_be_enabled()
        page.locator('#compare').click()
        expect(page.locator('#timing-table')).to_be_visible(timeout=120000)
        expect(page.locator('#nc-summary')).to_contain_text('O1 vs O2 vs O3 vs NeuroCompiler')
        expect(page.locator('#o3-runtime')).to_contain_text('ms')
        expect(page.locator('#nc-runtime')).to_contain_text('ms')
        expect(page.locator('#o1-runtime')).to_contain_text('ms')
        expect(page.locator('#o2-runtime')).to_contain_text('ms')
        assert page.locator('#o3-runtime').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')>=40
        expect(page.locator('#preferred-option')).to_be_visible()
        expect(page.locator('#timing-table tr')).to_have_count(4)
        expect(page.locator('#benchmark-content')).to_contain_text('Output checks passed')
        page.locator('[data-clock="wall"]').click()
        expect(page.locator('[data-clock="wall"]')).to_have_attribute('aria-pressed','true')
        with page.expect_download() as downloaded:
            page.locator('#download-json').click()
        result = json.loads(Path(downloaded.value.path()).read_text())
        assert result['decision']==analysis['decision']
        assert result['prediction_frozen_at'] < result['measurement_started_at']
        assert result['correctness']['passed']
        assert result['measurement']['protocol']=='live-four-way-v3'
        assert set(result['measurement']['four_way']['clocks']['cpu']['options'])=={'O1','O2','O3','NeuroCompiler'}
        assert len(result['measurement']['cells']['O3']['samples'])==12
        with page.expect_download() as downloaded:
            page.locator('#download-md').click()
        assert 'The model decision was frozen' in Path(downloaded.value.path()).read_text()
        assert 'Direct head-to-head comparisons' in Path(downloaded.value.path()).read_text()
        page.screenshot(path=str(output/'comparison-desktop.png'),full_page=True)
        checks.append('Trusted native execution, unchanged pre-timing decision, output checks, both clocks, raw pairs, and Markdown export')
        page.reload(wait_until='networkidle')
        expect(page.locator('#decision-content')).to_be_visible()
        expect(page.locator('#source')).to_have_value(analysis['input']['source'])
        checks.append('Browser refresh restores the input and matching analysis')
        page.set_viewport_size({'width':390,'height':844})
        for tab in ('decision','benchmark','ir','scope'):
            page.locator(f'[data-tab="{tab}"]').click()
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'),tab
        page.locator('[data-tab="decision"]').click()
        page.screenshot(path=str(output/'decision-mobile.png'),full_page=True)
        page.locator('[data-tab="decision"]').focus()
        page.keyboard.press('ArrowRight')
        expect(page.locator('[data-tab="benchmark"]')).to_have_attribute('aria-selected','true')
        checks.append('All mobile panels fit the viewport and tabs support keyboard arrows')
        page.set_viewport_size({'width':1440,'height':1050})
        page.locator('#source').fill('int main( { syntax error')
        expect(page.locator('#decision-content')).not_to_be_visible()
        expect(page.locator('#compare')).to_be_disabled()
        page.locator('#analyze').click()
        expect(page.locator('#error')).to_contain_text('error:',timeout=30000)
        page.locator('#example').select_option('stdin')
        page.locator('#analyze').click()
        expect(page.locator('#decision-content')).to_be_visible(timeout=30000)
        page.locator('[data-tab="benchmark"]').click()
        page.locator('#trusted').check()
        page.locator('#compare').click()
        expect(page.locator('#timing-table')).to_be_visible(timeout=30000)
        expect(page.locator('.correctness-card pre')).to_have_text('55\n')
        expect(page.locator('#nc-summary')).to_contain_text('Same executable as')
        expect(page.locator('#nc-summary')).to_contain_text('How the four-way result is checked')
        assert page.locator('#preferred-option').inner_text() in ['All four entries are the same executable','No reliable preference yet']
        expect(page.locator('#session-scorecard')).to_contain_text('Unchanged code / inconclusive differences')
        with page.expect_download() as downloaded:
            page.get_by_role('link',name='Session summary').click()
        card=json.loads(Path(downloaded.value.path()).read_text())
        assert card['groups']['training_example']['inputs']>=1
        assert card['groups']['bundled_demo']['unchanged']>=1
        assert card['totals']['tested']>=2
        checks.append('Edits invalidate stale results, compiler errors recover, stdin is real, and short programs stay inconclusive')
        upload = b'#include <stdio.h>\nint main(void){puts("uploaded C program");return 0;}\n'
        page.locator('#upload').set_input_files({'name':'audience.c','mimeType':'text/x-c','buffer':upload})
        expect(page.locator('#filename')).to_have_text('audience.c')
        expect(page.locator('#source')).to_have_value(upload.decode())
        expect(page.locator('#compare')).to_be_disabled()
        page.locator('#analyze').click()
        page.reload(wait_until='networkidle')
        expect(page.locator('#decision-content')).to_be_visible(timeout=30000)
        expect(page.locator('#source')).to_have_value(upload.decode())
        expect(page.locator('#example')).to_have_value('custom')
        checks.append('Real file upload and refresh during analysis keep the displayed source attached to its prediction')
        with page.expect_popup() as popup:
            page.get_by_role('link',name='Research evidence').click()
        expect(popup.value.locator('#study-status')).to_contain_text('inconclusive')
        checks.append('Preserved research dashboard remains accessible')
        browser.close()
    # All app assets and API requests stay local; downloads use the same origin.
    assert all(url.startswith(args.url) for url in requests), requests
    assert not errors, errors
    report = {'status':'passed','checks':checks,'browser_errors':errors,'external_requests':0,
              'sieve_verdicts':{k:v['verdict'] for k,v in result['measurement']['cells'].items()},
              'scope':'Presentation acceptance check, not a formal research experiment.'}
    (output/'check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
