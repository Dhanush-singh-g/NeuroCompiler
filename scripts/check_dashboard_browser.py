"""Optional Chromium UI verification; requires Playwright, not used by the app."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import Error, sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000/')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    args = parser.parse_args()
    errors, requests, checks, skipped = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1440, 'height':1100})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: requests.append(request.url))
        page.goto(args.url, wait_until='networkidle')
        expect(page.locator('#study-status')).to_contain_text('inconclusive')
        expect(page.locator('#overview-metrics')).to_contain_text('168')
        expect(page.locator('#headroom-content')).to_contain_text('12.1%')
        expect(page.locator('#headroom-content')).to_contain_text('does not establish learned generalization')
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.screenshot(path=str(ROOT/'results/dashboard_desktop.png'), full_page=True)
        checks.append('Desktop overview and scoped headroom')
        page.locator('[data-view="benchmarks"]').click()
        expect(page.locator('.program-row')).to_have_count(23)
        page.locator('#search').fill('blake')
        expect(page.locator('.program-row')).to_have_count(1)
        expect(page.locator('#program-detail h2')).to_have_text('BLAKE2')
        page.locator('#setting-select').select_option('O3_no_vector')
        expect(page.locator('#program-detail')).to_contain_text('Passed')
        expect(page.locator('#program-detail')).to_contain_text('no new fitted policy')
        page.locator('#setting-select').select_option('O3_large_inline')
        expect(page.locator('#program-detail')).to_contain_text('excluded from recommendations')
        page.locator('#search').fill('no-matching-program-123')
        expect(page.locator('#program-list')).to_contain_text('No matching programs')
        expect(page.locator('#program-detail')).to_contain_text('No program selected')
        page.locator('#search').fill('')
        page.locator('#split-filter').select_option('development')
        expect(page.locator('.program-row')).to_have_count(2)
        expect(page.locator('#program-detail')).to_contain_text('Not executed')
        expect(page.locator('#program-detail')).to_contain_text('Prediction unavailable')
        checks.append('Search, setting changes, empty state, and closed development')
        page.locator('[data-view="measurement"]').click()
        expect(page.locator('.control-button')).to_have_count(30)
        expect(page.locator('#quality-metrics')).to_contain_text('2,160')
        page.locator('[data-control-cpu="2"][data-control-case="expat_nested"]').click()
        expect(page.locator('#control-detail')).to_contain_text('0.901×')
        expect(page.locator('#control-detail')).to_contain_text('Starting-order bias')
        page.locator('#measurement-view [data-clock="wall"]').click()
        expect(page.locator('#control-detail')).to_contain_text('WALL CLOCK')
        page.locator('[data-control-cpu="3"][data-control-case="zlib_random"]').click()
        expect(page.locator('#control-detail')).to_contain_text('CPU 3')
        checks.append('Both clocks and recorded control failure details')
        page.locator('#topbar-evidence').click()
        expect(page.locator('#evidence-dialog')).to_be_visible()
        expect(page.locator('.source-item')).to_have_count(8)
        page.keyboard.press('Escape')
        expect(page.locator('#evidence-dialog')).not_to_be_visible()
        with page.expect_download() as downloaded:
            page.locator('#export-button').click()
        download = downloaded.value
        exported = json.loads(Path(download.path()).read_text())
        assert exported['measurement']['status'] == 'failed'
        assert exported['model']['status'] == 'not_qualified'
        checks.append('Provenance dialog keyboard close and actual JSON download')
        page.set_viewport_size({'width':390,'height':844})
        page.locator('[data-view="overview"]').click()
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.screenshot(path=str(ROOT/'results/dashboard_mobile.png'), full_page=True)
        page.locator('#topbar-evidence').click()
        expect(page.locator('#evidence-dialog')).to_be_visible()
        page.keyboard.press('Escape')
        page.locator('[data-view="measurement"]').click()
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        checks.append('Mobile layout and accessible evidence entry')
        offline = browser.new_page(viewport={'width':1200,'height':900})
        offline.on('pageerror', lambda error: errors.append(str(error)))
        try:
            offline.goto((ROOT/'dashboard/index.html').as_uri(), wait_until='load')
        except Error as error:
            if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):
                raise
            skipped.append('Direct file opening blocked by managed Chromium policy; HTTP workflow verified')
        else:
            expect(offline.locator('#overview-metrics')).to_contain_text('168')
            checks.append('Bundled offline file opening')
        missing = browser.new_page()
        missing.on('pageerror', lambda error: errors.append(str(error)))
        missing.route('**/results.js', lambda route: route.fulfill(body='/* unavailable */', content_type='text/javascript'))
        missing.goto(args.url)
        expect(missing.locator('#data-warning')).to_contain_text('evidence is unavailable')
        expect(missing.locator('#study-status')).to_contain_text('Performance results are unavailable')
        checks.append('Missing snapshot never displays performance success')
        assert not errors, errors
        assert all(url.startswith(args.url) for url in requests), requests
        browser.close()
    result = {'checks': checks, 'skipped': skipped, 'browser_errors': errors, 'external_requests': 0,
              'native_benchmarks_run': 0, 'status': 'passed'}
    (ROOT/'results/dashboard_browser_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
