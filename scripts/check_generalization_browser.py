"""Real-browser checks for frozen count results and the guarded learned artifact.

Requires Playwright/Chromium and a running local presentation server. Executes
only the bundled trusted programs; never trains or writes research results.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8000/')
parser.add_argument('--browser',default='/usr/bin/chromium')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
output=root/'.presentation/browser'
output.mkdir(parents=True,exist_ok=True)
report=json.loads((root/'presentation/generalization_results.json').read_text())
expected={r['id']:r for r in report['results']}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=args.browser,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1050});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(args.url,wait_until='networkidle')
 expect(page.locator('#connection')).to_contain_text('ready')
 page.locator('#policy-mode').select_option('hybrid')
 page.locator('[data-tab="scope"]').click()
 expect(page.locator('#generalization-results')).to_contain_text('12 authored synthetic programs / 6 families')
 expect(page.locator('#generalization-results')).to_contain_text('Fixed + O3 guard (derived)')
 page.locator('#generalization-results').screenshot(path=str(output/'unseen-count-evaluation.png'))
 for family in ['crc32','edit_distance','heapsort','floyd_warshall','integer_sqrt','rational_bezier']:
  page.locator('#example').select_option('evaluated_'+family)
  page.locator('#analyze').click()
  expect(page.locator('#decision-content')).to_be_visible(timeout=60000)
  with page.expect_download() as dl:page.locator('#download-json').click()
  result=json.loads(Path(dl.value.path()).read_text());seq=result['decision']['sequential']
  frozen=expected[family+'_0']
  assert result['source_sha256']==frozen['source_sha256']
  assert seq['model_sha256']==report['frozen']['model_sha256']
  assert seq['policy_final_instructions']==frozen['counts']['hybrid_raw']
  assert seq['final_instructions']==frozen['counts']['hybrid_guarded']
  assert seq['final_instructions']==result['decision']['metrics']['LearnedPolicy']['instructions']
  expect(page.locator('#standard-runtime')).to_have_text('Not measured')
  if family in ['integer_sqrt','rational_bezier']:
   expect(page.locator('.selected-sequence')).to_contain_text('O3 (static instruction-count fallback)')
   assert result['artifact_aliases']['LearnedPolicy']=='O3'
  print(family,'UI matches frozen raw/guarded counts and model SHA',flush=True)
 # All modes still compile. The raw sequence and emitted prefix are distinguished.
 for mode in ['sl','rl','hybrid']:
  page.locator('#policy-mode').select_option(mode)
  page.locator('#example').select_option('evaluated_crc32')
  page.locator('#arguments').evaluate('e=>e.closest("details").open=true')
  page.locator('#arguments').fill('5000')
  page.locator('#analyze').click()
  expect(page.locator('#decision-content')).to_be_visible(timeout=60000)
  expect(page.locator('#runtime-overview')).to_contain_text('static guard')
 page.locator('#overview-run').click();page.locator('#trusted').check();page.locator('#compare').click()
 expect(page.locator('#timing-table')).to_be_visible(timeout=120000)
 expect(page.locator('.correctness-card')).to_contain_text('Output checks passed')
 for clock in ['cpu','wall']:
  page.locator('#overview-clock').select_option(clock)
  with page.expect_download() as dl:page.locator('#download-json').click()
  result=json.loads(Path(dl.value.path()).read_text())
  for label,id in [('O3','standard-runtime'),('NeuroCompiler','learned-runtime')]:
   ms=result['measurement']['four_way']['clocks'][clock]['options'][label]['runtime_ms']
   expect(page.locator('#'+id)).to_have_text(f'{ms:.2f} ms')
 with page.expect_download() as dl:page.locator('#download-md').click()
 assert 'Static instruction-count guard' in Path(dl.value.path()).read_text()
 page.locator('[data-tab="decision"]').click()
 page.locator('.selection-details > summary').click()
 expect(page.locator('.selection-details')).to_contain_text('Raw learned terminal count:')
 page.locator('.selection-details > summary').click()
 page.reload(wait_until='networkidle');expect(page.locator('#learned-runtime')).to_contain_text('ms')
 page.set_viewport_size({'width':390,'height':844})
 for tab in ['decision','benchmark','ir','scope']:
  page.locator(f'[data-tab="{tab}"]').click()
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),tab
 assert not errors,errors
 print('All modes, native CRC output, two timing clocks, guard Markdown, reload and mobile passed',flush=True)
 b.close()
