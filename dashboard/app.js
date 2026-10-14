/* Static recorded evidence only. No compilation, benchmark execution, or model calls. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '—').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const ratio = value => Number.isFinite(value) ? `${value.toFixed(3)}×` : 'Unavailable';
  const labels = {O3:'-O3', O2:'-O2', O3_no_vector:'-O3 · no vectorization', O3_large_inline:'-O3 · large inline'};
  const names = {zlib_random:'zlib · random', expat_nested:'Expat · nested', lz4_random:'LZ4 · random', jsonparser_nested:'json-parser · nested', miniz_random:'miniz · random', mpack_nested:'MPack · nested'};
  const data = window.NEURO_RESULTS;
  if (!data || data.schema_version !== 1) {
    $('data-warning').hidden = false;
    $('data-warning').textContent = 'Dashboard evidence is unavailable. Run python scripts/build_dashboard.py from the project directory, then reload.';
    $('study-status').innerHTML = '<span class="notice-icon">!</span><div><strong>No evidence snapshot loaded</strong>Performance results are unavailable.</div>';
    return;
  }
  let clock = 'cpu';
  let selected = data.programs[0]?.id ?? null;
  let setting = 'O3';
  let selectedControl = {cpu:2, case:data.measurement.cases[1] ?? data.measurement.cases[0]};
  const tag = (text, cls='neutral') => `<span class="tag ${cls}">${esc(text)}</span>`;
  const metric = (label, value, note, icon, unit='') => `<article class="metric"><span class="metric-icon" aria-hidden="true">${icon}</span><p class="metric-label">${esc(label)}</p><div class="metric-value">${esc(value)}<span class="metric-unit">${esc(unit)}</span></div><p class="metric-note">${esc(note)}</p></article>`;
  if (data.warnings.length) {
    $('data-warning').hidden = false;
    $('data-warning').textContent = `${data.warnings.length} evidence source issue(s). Affected results are unavailable; see Evidence & sources.`;
  }
  $('nav-count').textContent = data.programs.length;
  $('overview-metrics').innerHTML = [
    metric('Training implementations',data.corpus.training_programs,'Input variants stay grouped','▤'),
    metric('Correctness inputs',data.corpus.training_inputs,'Four compiler settings each','◈'),
    metric('Correctness checks passed',data.corpus.correctness_cells,'Recorded O0 / candidate comparisons','✓'),
    metric('Fresh development programs',data.corpus.development_programs,'Reserved · no execution yet','◇')
  ].join('');
  const statusCopy = {
    failed:['Performance study is inconclusive','No available target passed measurement admission. Learned improvement over -O3 remains unproven.'],
    unavailable:['Measurement evidence is incomplete','Admission and performance results remain unavailable until the required records are present.'],
    confirmation_required:['Independent confirmation required','A passing screen alone does not establish reliable training labels or learned improvement.']
  }[data.measurement.status] ?? ['Measurement status unavailable','No performance conclusion can be drawn.'];
  $('study-status').innerHTML = `<span class="notice-icon">!</span><div><strong>${statusCopy[0]}</strong>${statusCopy[1]}</div><a href="#measurement">View controls <span>↗</span></a>`;
  const correct = data.corpus.status === 'complete' && data.corpus.training_inputs > 0 && data.corpus.correctness_cells === data.corpus.training_inputs * data.settings.length;
  $('pipeline').innerHTML = [
    ['Source & corpus',data.corpus.status === 'complete' ? `${data.corpus.training_programs} pinned training implementations` : 'Corpus evidence unavailable', data.corpus.status === 'complete'?'done':''],
    ['Correctness',correct ? `${data.corpus.correctness_cells} recorded checks passed` : 'Coverage incomplete or unavailable',correct?'done':''],
    ['Measurement admission',data.measurement.status === 'failed' ? 'Blocked · no qualified target' : 'Not confirmed',data.measurement.status==='failed'?'blocked':''],
    ['Expanded model evaluation','Not run · awaits admitted measurements','']
  ].map(([title, note, cls])=>`<li><span class="step-icon ${cls}" aria-hidden="true">${cls==='done'?'✓':cls==='blocked'?'!':'·'}</span>${esc(title)}<small>${esc(note)}</small></li>`).join('');
  $('default-policy').textContent = labels[data.model.default] ?? 'Unavailable';
  $('default-policy').nextElementSibling.textContent = data.model.status==='not_qualified' ? 'Previous study · no qualified learned selector' : 'See recorded model evidence';
  function renderChart() {
    const target = data.measurement.targets.find(t => t.cpu===2);
    if (!target) { $('control-chart').innerHTML = '<p class="empty">CPU 2 control evidence unavailable.</p>'; return; }
    const stats = data.measurement.cases.map(c=>target.statistics[c][clock]);
    const min = Math.min(.94,...stats.map(s=>s.interval[0]))-.01;
    const max = Math.max(1.06,...stats.map(s=>s.interval[1]))+.01;
    const compact=$('control-chart').clientWidth<400;
    const width=compact?360:570, left=compact?125:141, right=compact?337:539, top=28, rowHeight=34, height=top+stats.length*rowHeight+35;
    const x = n => left+(n-min)/(max-min)*(right-left);
    const low = 1/(1+data.measurement.tolerance), high=1+data.measurement.tolerance;
    const band = `<rect x="${x(low)}" y="10" width="${x(high)-x(low)}" height="${stats.length*rowHeight+18}" rx="4" fill="#eef4ea"/>`;
    const guides = [min,1,max].map(n=>`<line x1="${x(n)}" x2="${x(n)}" y1="12" y2="${height-31}" stroke="${n===1?'#aec4a5':'#e8eee4'}" ${n===1?'stroke-dasharray="3 4"':''}/><text x="${x(n)}" y="${height-9}" text-anchor="middle" fill="#8b9885" font-size="10">${n.toFixed(2)}×</text>`).join('');
    const rows = data.measurement.cases.map((c,i)=>{
      const s=target.statistics[c][clock], y=top+i*rowHeight, color=s.passed?'#587e5e':'#b88345';
      return `<g><title>${esc(names[c]??c)}: ${ratio(s.ratio)}, interval ${ratio(s.interval[0])}–${ratio(s.interval[1])}, ${s.passed?'passed':'failed'}</title><text x="0" y="${y+4}" fill="#6f806b" font-size="11">${esc(names[c]??c)}</text><line x1="${x(s.interval[0])}" x2="${x(s.interval[1])}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="2"/><line x1="${x(s.interval[0])}" x2="${x(s.interval[0])}" y1="${y-4}" y2="${y+4}" stroke="${color}"/><line x1="${x(s.interval[1])}" x2="${x(s.interval[1])}" y1="${y-4}" y2="${y+4}" stroke="${color}"/><circle cx="${x(s.ratio)}" cy="${y}" r="4.2" fill="${color}" stroke="white" stroke-width="1.5"/></g>`;
    }).join('');
    $('control-chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">CPU 2 identical-O3 ${clock} control ratios</title><desc id="chart-desc">${stats.filter(s=>s.passed).length} of six controls pass. The shaded area is the declared tolerance. These are measurement controls, not compiler improvements.</desc>${band}${guides}${rows}</svg>`;
  }
  const headroom=data.headroom;
  $('headroom-content').innerHTML = headroom ? `<div class="headroom-body"><div class="headroom-value">${headroom.cpu_time_reduction.toFixed(1)}%<small>LESS API CPU TIME</small></div><p class="headroom-copy"><strong>BLAKE2 · random input</strong><br>No-vectorization setting vs. -O3<br>${ratio(headroom.cpu.speedup)} · interval ${ratio(headroom.cpu.interval[0])}–${ratio(headroom.cpu.interval[1])}</p></div><p class="scope-note">One preselected training case. Excluded from model fitting. This result does not establish learned generalization.</p>` : '<p class="empty">Qualified training-headroom evidence unavailable.</p>';

  function filteredPrograms() {
    const query=$('search').value.trim().toLowerCase(), split=$('split-filter').value;
    return data.programs.filter(p=>(split==='all'||p.split===split) && `${p.name} ${p.id} ${p.category} ${p.inputs.map(i=>i.id).join(' ')}`.toLowerCase().includes(query));
  }
  function programPassed(p) { return p.inputs.length>0 && p.inputs.every(i=>data.settings.every(s=>i.settings[s]==='passed')); }
  function renderPrograms() {
    const programs=filteredPrograms();
    if (!programs.some(p=>p.id===selected)) selected=programs[0]?.id??null;
    $('program-count').textContent=`${programs.length} program${programs.length===1?'':'s'}`;
    $('program-list').innerHTML = programs.length ? programs.map(p=>`<button class="program-row ${selected===p.id?'selected':''}" data-program="${esc(p.id)}" aria-pressed="${selected===p.id}"><span class="program-avatar" aria-hidden="true">${esc(p.name.slice(0,2).toUpperCase())}</span><span><strong>${esc(p.name)}</strong><small>${esc(p.category)} · ${p.inputs.length} inputs</small></span>${tag(p.split==='development'?'Reserved':programPassed(p)?'Correct':'Incomplete',p.split==='development'?'neutral':programPassed(p)?'passed-tag':'warning-tag')}</button>`).join('') : '<p class="empty">No matching programs. Try another search or split.</p>';
    renderProgramDetail();
  }
  function renderProgramDetail() {
    const p=data.programs.find(p=>p.id===selected);
    if (!p) { $('program-detail').innerHTML='<h2>No program selected</h2><p class="card-description">Change the search or dataset filter to explore an implementation.</p>';return; }
    const dev=p.split==='development';
    const inputs=p.inputs.map(i=>{
      const status=i.settings[setting]??'unavailable';
      const title={passed:'Passed',failed:'Failed',unrun:'Not executed',unavailable:'Unavailable'}[status]??'Unavailable';
      return `<div class="input-card"><header><span>${esc(i.id)}</span>${tag(title,status==='passed'?'passed-tag':status==='failed'?'warning-tag':'neutral')}</header><p>${dev?'Reserved development input. Native compilation and execution remain closed.':status==='passed'?'Two recorded pairs match O0 and the independent expected result.':'The selected setting has no complete passing correctness record.'}</p>${i.feature_count?`<p>${esc(i.feature_count)} static predictor fields · correctness timings are excluded from performance labels</p>`:''}</div>`;
    }).join('');
    $('program-detail').innerHTML=`<div class="program-detail-heading"><div><p class="eyebrow">${dev?'UNTOUCHED DEVELOPMENT':'TRAINING IMPLEMENTATION'}</p><h2>${esc(p.name)}</h2><div class="details-meta">${tag(p.category)}${tag(dev?'Reserved':'Expanded corpus')}</div></div><span class="program-avatar" aria-hidden="true">${esc(p.name.slice(0,2).toUpperCase())}</span></div><div class="setting-bar"><label for="setting-select">Compiler setting</label><select id="setting-select" class="setting-select">${data.settings.map(s=>`<option value="${esc(s)}" ${s===setting?'selected':''}>${esc(labels[s]??s)}</option>`).join('')}</select></div>${setting==='O3_large_inline'?'<p class="subtle">Large-inline is a correctness setting only in this study; it is excluded from recommendations.</p>':''}${inputs}<hr class="detail-divider"><p class="eyebrow">PERFORMANCE & POLICY</p><div class="fallback-card">${dev?'Prediction unavailable':'Default policy from the previous study'}<strong>${dev?'Not evaluated':esc(labels[data.model.default]??'Unavailable')}</strong><p>${dev?'No model-frozen development evaluation has run.':'No per-program learned recommendation is available. Expanded admission failed, so this corpus supplies no new fitted policy or performance comparison.'}</p></div><p class="eyebrow">PINNED SOURCE</p><p class="subtle">${esc(p.pin.repository??p.name)}${p.pin.commit?` · commit ${esc(p.pin.commit.slice(0,12))}`:''}</p><p class="hash">SHA256 ${esc(p.pin.sha256)}</p>`;
    $('setting-select').addEventListener('change',e=>{setting=e.target.value;renderProgramDetail();});
  }
  $('program-list').addEventListener('click',e=>{const button=e.target.closest('[data-program]');if(button){selected=button.dataset.program;renderPrograms();}});
  $('search').addEventListener('input',renderPrograms);
  $('split-filter').addEventListener('change',renderPrograms);

  const measurement=data.measurement;
  $('quality-metrics').innerHTML=[metric('Logical CPUs screened',measurement.status==='unavailable'?'—':measurement.targets.length,'All available targets','⌁'),metric('Retained matched pairs',measurement.pairs?.toLocaleString('en-IN'),'Admission data · excluded from fitting','◈'),metric('Admitted targets',measurement.status==='unavailable'?'—':measurement.targets.filter(t=>t.admitted).length,'Independent confirmation still required','◇')].join('');
  $('matrix-status').textContent=measurement.status==='failed'?'No target qualified':measurement.status==='unavailable'?'Evidence unavailable':'Confirmation required';
  function renderMatrix() {
    const targets=measurement.targets;
    if (!targets.length) {$('control-matrix').innerHTML='<p class="empty">Admission records unavailable.</p>';return;}
    $('control-matrix').innerHTML=`<table><caption class="sr-only">Recorded ${clock} clock admission controls by input and logical CPU</caption><thead><tr><th scope="col">Admission input</th>${targets.map(t=>`<th scope="col">CPU ${t.cpu}<small>${t.counts[clock]} / ${t.total} passed</small></th>`).join('')}</tr></thead><tbody>${measurement.cases.map(c=>`<tr><th scope="row">${esc(names[c]??c)}</th>${targets.map(t=>{const s=t.statistics[c][clock];return `<td><button class="control-button ${s.passed?'':'failed'}" data-control-cpu="${t.cpu}" data-control-case="${esc(c)}" aria-pressed="${selectedControl.cpu===t.cpu&&selectedControl.case===c}" aria-label="${esc(names[c]??c)}, CPU ${t.cpu}, ${clock}, ${s.passed?'passed':'failed'}">${s.passed?'Pass':'Fail'}</button></td>`;}).join('')}</tr>`).join('')}</tbody></table>`;
    renderControlDetail();
  }
  function renderControlDetail() {
    const target=measurement.targets.find(t=>t.cpu===selectedControl.cpu), s=target?.statistics[selectedControl.case]?.[clock];
    if (!s) { $('control-detail').innerHTML='<h2>Control evidence unavailable</h2>';return; }
    $('control-detail').innerHTML=`<div class="card-heading"><div><p class="eyebrow">CPU ${target.cpu} / ${clock.toUpperCase()} CLOCK</p><h2>${esc(names[selectedControl.case]??selectedControl.case)}</h2></div>${tag(s.passed?'Qualified control':'Failed control',s.passed?'passed-tag':'warning-tag')}</div><div class="control-stats"><div>Identical-O3 pooled ratio<strong>${ratio(s.ratio)}</strong></div><div>Recorded bootstrap interval<strong>${ratio(s.interval[0])}–${ratio(s.interval[1])}</strong></div></div><p class="eyebrow">BLOCK RATIOS</p><div class="block-list">${s.blocks.map((v,i)=>`<span>0${i+1} &nbsp; ${ratio(v)}</span>`).join('')}</div>${s.reasons.length?`<p class="reason-list">${s.reasons.map(esc).join(' · ')}</p>`:'<p class="subtle">This input meets the recorded clock bounds. Admission requires every input on both clocks.</p>'}<p class="subtle">Comparison uses the same optimization setting on both sides. The ratio is not an optimization gain.</p>`;
  }
  $('control-matrix').addEventListener('click',e=>{const button=e.target.closest('[data-control-cpu]');if(button){selectedControl={cpu:Number(button.dataset.controlCpu),case:button.dataset.controlCase};renderMatrix();}});
  document.querySelectorAll('[data-clock]').forEach(button=>button.addEventListener('click',()=>{
    clock=button.dataset.clock;
    document.querySelectorAll('[data-clock]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.clock===clock));
    renderChart();renderMatrix();
  }));
  function navigate() {
    const requested=location.hash.slice(1), view=['overview','benchmarks','measurement'].includes(requested)?requested:'overview';
    document.querySelectorAll('.view').forEach(section=>section.hidden=section.id!==`${view}-view`);
    document.querySelectorAll('[data-view]').forEach(link=>{link.classList.toggle('active',link.dataset.view===view);if(link.dataset.view===view)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
    $('breadcrumb').textContent={overview:'Overview',benchmarks:'Benchmarks',measurement:'Measurement quality'}[view];
    document.title=`NeuroCompiler · ${$('breadcrumb').textContent}`;
  }
  window.addEventListener('hashchange',()=>{navigate();$('main').focus({preventScroll:true});window.scrollTo(0,0);});
  window.addEventListener('resize',()=>window.requestAnimationFrame(renderChart));
  $('source-list').innerHTML=data.sources.map(s=>`<div class="source-item"><strong>${esc(s.path)}</strong>${tag(s.status,s.status==='loaded'?'passed-tag':'warning-tag')}<p class="hash">${esc(s.sha256??'No source hash available')}</p></div>`).join('');
  if(data.warnings.length)$('source-list').insertAdjacentHTML('beforeend',`<p class="reason-list">${data.warnings.map(esc).join('<br>')}</p>`);
  $('evidence-button').addEventListener('click',()=>$('evidence-dialog').showModal());
  $('topbar-evidence').addEventListener('click',()=>$('evidence-dialog').showModal());
  $('close-evidence').addEventListener('click',()=>$('evidence-dialog').close());
  $('evidence-dialog').addEventListener('click',e=>{if(e.target===$('evidence-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $('export-button').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='neurocompiler-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  const date=new Date(data.exported_at);
  $('footer-date').textContent=Number.isNaN(date.getTime())?'Snapshot date unavailable':`Exported ${date.toLocaleDateString('en-IN',{timeZone:'Asia/Kolkata',day:'numeric',month:'short',year:'numeric'})}`;
  renderChart();renderPrograms();renderMatrix();navigate();
})();
