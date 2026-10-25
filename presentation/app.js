'use strict';
const $ = id => document.getElementById(id);
const labels = {O1:'O1', O2:'O2', NeuroCompiler:'NeuroCompiler', O3: 'O3', mem2reg_loop_rotate_licm_O3: 'Loop preparation → O3', O3_gvn_dce: 'O3 → GVN → DCE', instcombine_O3: 'Instcombine → O3'};
const shortLabels = {O1:'O1', O2:'O2', NeuroCompiler:'NeuroCompiler', O3: 'O3 baseline', mem2reg_loop_rotate_licm_O3: 'Loop prep → O3', O3_gvn_dce: 'O3 + GVN / DCE', instcombine_O3: 'Instcombine → O3'};
const verdicts = {same_binary:'Same binary as O3',inconclusive:'Inconclusive',faster_in_demo:'Faster in this demo',slower_in_demo:'Slower in this demo',no_clear_difference:'No clear difference'};
let session, analysis = null, latest = null, activeJob = null, dirty = true, clock = 'cpu', pollTimer, busy = false;
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const signed = n => `${n >= 0 ? '+' : ''}${n.toFixed(4)}`;
const estimate = score => Math.abs(score)>Math.log(4) ? 'Outside reporting range' : `${Math.abs(100*Math.expm1(-score)).toFixed(1)}% ${score>=0?'less':'more'} time`;
const pipeline = choice => labels[choice] || choice;

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-NeuroCompiler-Token':session.token},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function setTab(name, focus = false) {
  document.querySelectorAll('[data-tab]').forEach(button => {
    const selected = button.dataset.tab === name;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
    if (selected && focus) button.focus();
    $(`panel-${button.dataset.tab}`).hidden = !selected;
  });
  if (name === 'benchmark' && latest?.measurement?.status === 'completed') drawChart();
  if (name === 'ir' && analysis && !dirty) renderIR();
}
document.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => setTab(button.dataset.tab));
  button.addEventListener('keydown', event => {
    const tabs = [...document.querySelectorAll('[data-tab]')];
    let index = tabs.indexOf(button);
    if (event.key === 'ArrowRight') index = (index+1)%tabs.length;
    else if (event.key === 'ArrowLeft') index = (index-1+tabs.length)%tabs.length;
    else if (event.key === 'Home') index = 0;
    else if (event.key === 'End') index = tabs.length-1;
    else return;
    event.preventDefault(); setTab(tabs[index].dataset.tab, true);
  });
});
$('scope-shortcut').addEventListener('click', () => {setTab('scope'); $('results-heading').scrollIntoView({behavior:'smooth',block:'start'});});

function updateButtons() {
  $('analyze').disabled = !session || busy || !$('source').value.trim();
  $('compare').disabled = busy || dirty || !analysis || !$('trusted').checked;
  $('cancel').disabled = !activeJob;
  ['source','arguments','iterations','stdin','example','upload','reset'].forEach(id => $(id).disabled = busy);
}
function updateLines() {
  const source = $('source').value;
  $('line-numbers').textContent = Array.from({length:source.split('\n').length}, (_,i)=>i+1).join('\n');
  $('source-size').textContent = `${new TextEncoder().encode(source).length.toLocaleString()} bytes`;
  $('line-numbers').scrollTop = $('source').scrollTop;
}
function customExample() {
  if (!$('example').querySelector('[value="custom"]')) {
    const option = document.createElement('option');
    option.value = 'custom'; option.textContent = 'Custom / restored program'; option.disabled = true;
    $('example').append(option);
  }
  $('example').value = 'custom';
}
function restoreInput(result) {
  $('source').value=result.input.source;
  $('arguments').value=result.input.arguments.map(a=>`'${a.replace(/'/g,`'\\''`)}'`).join(' ');
  $('stdin').value=result.input.stdin; $('iterations').value=result.input.iterations;
  const example = session.examples.find(e=>e.source===result.input.source);
  if (example) { $('example').value=example.id; $('example-description').textContent=example.description; }
  else { customExample(); $('example-description').textContent='Your locally saved C program and input. Only execute code you trust.'; }
  updateLines();
}
function markDirty() {
  dirty = true;
  analysis = latest = null;
  $('downloads').hidden = true;
  $('decision-empty').hidden = false;
  $('decision-content').hidden = true;
  $('decision-empty').querySelector('h3').textContent = 'Your input changed. Make a fresh prediction.';
  $('benchmark-content').innerHTML = '<div class="empty-state compact"><h3>No current comparison.</h3><p>Analyze the updated program and input before running it.</p></div>';
  $('ir-base').textContent = 'Analyze the current input to inspect its LLVM IR.';
  $('ir-candidate').textContent = 'Candidate IR will appear here.';
  $('ir-metrics').textContent = '';
  ['compile','predict','compare'].forEach(step => $(`step-${step}`).className = '');
  updateLines(); updateButtons();
}
['source','arguments','iterations','stdin'].forEach(id => $(id).addEventListener('input', markDirty));
$('source').addEventListener('scroll', () => $('line-numbers').scrollTop = $('source').scrollTop);
$('trusted').addEventListener('change', updateButtons);

function loadExample() {
  const example = session.examples.find(item => item.id === $('example').value);
  if (!example) return;
  $('source').value = example.source;
  $('arguments').value = example.arguments;
  $('iterations').value = example.iterations;
  $('stdin').value = example.stdin;
  $('filename').textContent = `${example.id}.c`;
  $('example-description').textContent = example.description;
  $('error').hidden = true; markDirty();
}
$('example').addEventListener('change', loadExample);
$('reset').addEventListener('click', () => {if($('example').value==='custom')$('example').value=session.examples[0].id;loadExample();});
$('upload').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.c') || file.size > 49152) {
    showError('Choose a .c file up to 48 KiB.'); return;
  }
  $('source').value = await file.text();
  $('filename').textContent = file.name;
  customExample();
  $('arguments').value = ''; $('stdin').value = ''; $('iterations').value = 0;
  $('example-description').textContent = 'Your program: self-contained C, deterministic stdout, libc/libm only. Only execute code you trust.';
  markDirty(); $('upload').value = '';
});
function showError(message) { $('error').textContent = message; $('error').hidden = false; }
function startProgress(job) {
  activeJob = job.id; busy = true;
  $('error').hidden = true; $('progress-panel').hidden = false;
  $('progress').value = job.percent; $('progress-message').textContent = job.message;
  updateButtons(); poll(job.id);
}
async function poll(id) {
  try {
    const job = await api(`/api/jobs/${id}`);
    if (id !== activeJob) return;
    $('progress').value = job.percent; $('progress-message').textContent = job.message;
    $('step-compile').className = ['compile','pipelines'].includes(job.stage) ? 'active' : 'done';
    $('step-predict').className = job.stage === 'predict' ? 'active' : (job.stage === 'baselines' || analysis ? 'done' : '');
    $('step-compare').className = ['correctness','measure'].includes(job.stage) ? 'active' : '';
    if (job.status === 'running') {pollTimer = setTimeout(() => poll(id), 500); return;}
    activeJob = null; busy = false; $('progress-panel').hidden = true;
    if (job.status === 'completed') {
      latest = job.result;
      if (latest.kind === 'analysis') {
        analysis = latest; dirty = false;
        restoreInput(analysis);
        renderDecision(latest); setTab('decision');
        $('step-compile').className = $('step-predict').className = 'done';
      } else {
        renderBenchmark(latest); setTab('benchmark');
        $('step-compare').className = 'done';
      }
      $('downloads').hidden = false;
      $('download-md').href = `/api/jobs/${id}/report.md`;
      $('download-json').href = `/api/jobs/${id}/report.json`;
      await refreshScorecard();
    } else if (job.status !== 'cancelled') showError(job.message);
    updateButtons();
  } catch (error) {
    activeJob = null; busy = false; $('progress-panel').hidden = true;
    showError(`${error.message} If a job was running, reload the page to reconnect or stop the server with Ctrl+C.`);
    updateButtons();
  }
}
$('analyze').addEventListener('click', async () => {
  busy = true; updateButtons();
  try {
    const iterations = Number($('iterations').value);
    if (!Number.isSafeInteger(iterations)) throw new Error('Iterations descriptor must be a whole number.');
    const job = await api('/api/jobs', {operation:'analyze',source:$('source').value,arguments:$('arguments').value,stdin:$('stdin').value,iterations});
    startProgress(job);
  } catch (error) {busy = false; updateButtons(); showError(error.message);}
});
$('compare').addEventListener('click', async () => {
  busy = true; updateButtons();
  try {
    const job = await api('/api/jobs', {operation:'compare',analysis_id:analysis.id,trusted_code:$('trusted').checked});
    startProgress(job);
  } catch (error) {busy = false; updateButtons(); showError(error.message);}
});
$('cancel').addEventListener('click', async () => {
  if (!activeJob) return;
  try {await api(`/api/jobs/${activeJob}/cancel`, {});} catch (error) {showError(error.message);}
});

function renderDecision(result) {
  const d = result.decision, metrics = d.metrics.O3;
  const candidates = Object.keys(d.scores).filter(c => c !== 'O3');
  const best = candidates.reduce((a,b)=>d.scores[a]>d.scores[b]?a:b);
  $('decision-empty').hidden = true; $('decision-content').hidden = false;
  $('decision-content').innerHTML = `<div class="decision-grid"><div class="prediction-card"><span class="small-label">NEUROCOMPILER'S DECISION</span><span class="badge">EXPERIMENTAL</span><div class="prediction-choice">${escape(d.choice==='O3'?'Keep O3':pipeline(d.choice))}</div><p>${escape(d.reason)}</p><p>${d.diagnostics?.distinct_executables ?? 4} distinct executable(s) in the model’s four-pipeline menu<br>Static prediction · no program execution</p><div class="approved-line">Research default (model unqualified)<strong>O3</strong></div></div><div class="analysis-side"><div class="feature-strip"><div><strong>${metrics.instructions}</strong><span>O3 IR instructions</span></div><div><strong>${metrics.cyclic_regions}</strong><span>cyclic CFG regions</span></div><div><strong>${metrics.functions}</strong><span>defined functions</span></div></div><h3>Model estimates vs O3</h3><div class="score-list">${Object.entries(d.scores).map(([c,score])=>`<div class="score-row"><span>${escape(pipeline(c))}${d.aliases[c] !== c ? `<small>Same binary as ${escape(pipeline(d.aliases[c]))}</small>`:''}</span><strong>${score===0?'No predicted change':estimate(score)}</strong></div>`).join('')}</div><p class="result-note">Estimates come from ${d.feature_count} static fields per alternative. They are predictions, not measured gains or confidence probabilities. O3 is also a valid NeuroCompiler decision.</p></div></div><details class="attribution"><summary>How the model made this decision · technical details</summary><div class="attribution-header"><h3>Inside the prediction</h3><select id="explanation-choice" aria-label="Pipeline explanation">${candidates.map(c=>`<option value="${c}">${escape(pipeline(c))}</option>`).join('')}</select></div><p>Largest linear contributions to this pipeline’s raw model score. These explain the model, not the physical cause of runtime.</p><div id="attribution-content"></div></details><p class="result-note">Prediction frozen ${escape(new Date(result.prediction_frozen_at).toLocaleTimeString())} · Source SHA256 ${escape(result.source_sha256.slice(0,16))}… · No native execution. <button class="text-button" id="go-benchmark">Test this prediction →</button></p>`;
  $('explanation-choice').value = d.choice === 'O3' ? best : d.choice;
  const exports = document.createElement('div');
  exports.className='artifact-exports';
  exports.innerHTML=`<a href="/api/jobs/${result.id}/selected.bc" download>↓ Export model choice .bc</a><a href="/api/jobs/${result.id}/approved.bc" download>↓ Export approved O3 .bc</a><span>Compiled LLVM10 bitcode · experimental choice remains unqualified</span>`;
  $('decision-content').append(exports);
  if(d.diagnostics?.recommendation_notes?.length){
    const note=document.createElement('p');note.className='result-note';
    note.textContent=d.diagnostics.recommendation_notes.join(' ');
    $('decision-content').querySelector('.prediction-card').append(note);
  }
  $('explanation-choice').addEventListener('change', renderAttribution);
  $('go-benchmark').addEventListener('click', () => setTab('benchmark'));
  renderAttribution();
  $('ir-choice').innerHTML = Object.keys(result.artifacts).filter(c=>c!=='O3').map(c=>`<option value="${c}">${escape(pipeline(c))}</option>`).join('');
  $('ir-choice').value = d.choice === 'O3' ? best : d.choice;
}
function renderAttribution() {
  const choice = $('explanation-choice').value;
  const explanation = analysis.decision.explanations[choice];
  $('attribution-content').innerHTML = `<div class="attribution-list">${explanation.top_contributions.map(item=>`<div class="contribution ${item.contribution<0?'negative':''}"><span>${escape(item.feature)}</span><strong>${signed(item.contribution)}</strong></div>`).join('')}</div><p>Raw log score ${signed(explanation.raw_score)}; intercept ${signed(explanation.intercept)}. Remaining features also contribute.${explanation.outside_training_scale_fields ? ` ${explanation.outside_training_scale_fields} fields exceed six training standard deviations; this is an extrapolation warning, not a calibrated uncertainty score.`:''}${analysis.decision.aliases[choice]==='O3' ? ' This binary matches O3, so the selection score is overridden to zero.':''}</p>`;
}
function renderBenchmark(result) {
  const m = result.measurement, correctness = result.correctness;
  if (m.status === 'blocked') {
    $('benchmark-content').innerHTML = `<div class="quality-banner"><strong>Comparison blocked.</strong> ${escape(m.reason)}</div><div class="table-scroll"><table><thead><tr><th>PIPELINE</th><th>MATCHES O0 OUTPUT</th><th>STDOUT PREVIEW</th></tr></thead><tbody>${Object.entries(correctness.checks).map(([c,v])=>`<tr><td>${escape(pipeline(c))}</td><td>${v.passed?'Passed':'Mismatch'}</td><td><code>${escape(v.stdout_preview||'(empty)')}</code></td></tr>`).join('')}</tbody></table></div><p class="result-note">${escape(correctness.scope)}</p>`;
    return;
  }
  const choice = result.decision.choice;
  const selected = m.cells[choice];
  $('benchmark-content').innerHTML = `<div class="benchmark-heading"><h3>Prediction: ${escape(pipeline(choice))}</h3><div class="clock-switch" aria-label="Timing clock"><button data-clock="cpu" class="${clock==='cpu'?'selected':''}" aria-pressed="${clock==='cpu'}">CPU</button><button data-clock="wall" class="${clock==='wall'?'selected':''}" aria-pressed="${clock==='wall'}">WALL</button></div></div><div class="quality-banner ${(m.four_way?m.four_way.status==='reliable_winner':m.self_control_passed)?'passed':''}"><strong>${m.four_way?(m.four_way.controls_passed?'All executable self-controls passed.':'One or more executable self-controls failed.'):(m.self_control_passed?'O3 self-control passed.':'O3 self-control did not qualify.')}</strong> Direct comparisons decide the preference on both clocks; all observed times remain visible.</div><div id="nc-summary" class="nc-summary"></div><div class="chart-wrap"><canvas id="timing-chart" role="img" aria-label="Compiler comparison chart; values and reliability details follow in the table."></canvas></div><p class="chart-caption">O3 TIME ÷ CANDIDATE TIME · ABOVE 1 = FASTER · ADJUSTED BOOTSTRAP INTERVALS</p><div class="table-scroll"><table><thead><tr><th>PIPELINE</th><th>MEDIAN TIME</th><th>RATIO [ADJUSTED INTERVAL]</th><th>INTERPRETATION</th></tr></thead><tbody id="timing-table"></tbody></table></div><div class="correctness-card"><span class="check-mark">✓</span><div><h4>Output checks passed / O0 + all six built pipelines</h4><p>${escape(correctness.scope)}</p><pre>${escape(correctness.checks['O0 reference'].stdout_preview || '(empty stdout)')}</pre></div></div><p class="result-note">${escape(m.timer)} ${m.pairs_per_distinct_cell} pairs per distinct cell; all samples retained. Binary aliases reuse the canonical measurement. The table includes post-prediction candidate exploration; the fastest observed candidate is not automatically the model recommendation.</p><details class="input-details"><summary>Measurement protocol & interpretation</summary><p class="muted">${escape(m.quality_rule)}</p><p class="muted">${escape(m.interval_scope)}</p><p class="muted">${escape(m.scope)}</p></details>`;
  document.querySelectorAll('[data-clock]').forEach(button=>button.addEventListener('click',()=>{
    clock = button.dataset.clock;
    document.querySelectorAll('[data-clock]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});
    renderTimingTable(); drawChart();
  }));
  renderTimingTable();
}
function renderTimingTable() {
  renderOutcome();
  if(latest.measurement.four_way){renderFourWayTable();return;}
  $('timing-table').innerHTML = Object.entries(latest.measurement.cells).map(([choice,cell])=>{
    const s = cell.clocks[clock];
    const tone = cell.verdict === 'faster_in_demo'?'good':cell.verdict === 'slower_in_demo'?'bad':'';
    const same=latest.decision.aliases[choice]==='O3';
    return `<tr><td>${escape(pipeline(choice))}${choice===latest.decision.choice?'<span class="predicted-tag">NEUROCOMPILER CHOICE</span>':''}</td><td class="runtime-cell">${(s.median_seconds*1000).toFixed(2)} <small>ms</small></td><td>${same?'1.000× · same executable':`${s.speedup.toFixed(3)}× [${s.interval[0].toFixed(3)}, ${s.interval[1].toFixed(3)}]`}</td><td><span class="verdict ${tone}">${same?'Unchanged code':escape(verdicts[cell.verdict])}</span>${cell.alias_of?`<span class="predicted-tag">Shared binary / ${escape(pipeline(cell.alias_of))}</span>`:''}</td></tr>`;
  }).join('');
}
function renderOutcome() {
  if(latest.measurement.four_way){renderFourWayOutcome();return;}
  const summary=latest.measurement.summary?.clocks[clock], panel=$('nc-summary');
  if(!summary || !panel)return;
  const delta=summary.time_change_percent;
  const difference=summary.same_executable?'0.0% change':`${Math.abs(delta).toFixed(1)}% ${delta>0?'more':'less'} time`;
  const gap=summary.gap_to_best_percent===null?'Not available':`${summary.gap_to_best_percent.toFixed(1)}%`;
  const clockSummaries=latest.measurement.summary.clocks;
  const bothQualified=clockSummaries.cpu.qualified && clockSummaries.wall.qualified && clockSummaries.cpu.status===clockSummaries.wall.status;
  const preferred=bothQualified && !summary.same_executable && ['faster','slower'].includes(summary.status) ? summary.preferred_choice : null;
  const preference=summary.same_executable?'Same executable — no preference':preferred==='O3'?'Prefer O3 over NeuroCompiler’s choice':preferred?'Prefer NeuroCompiler’s choice over O3':bothQualified?'No clear winner — O3 remains the default':'No reliable preference yet';
  const runtimeCards=`<div class="preference-banner ${preferred?'has-preference':''}"><span class="small-label">DEMO PREFERENCE / BOTH CLOCKS</span><strong id="preferred-option">${preference}</strong><span>${summary.same_executable?'NeuroCompiler chose the baseline executable. Timing noise does not create a winner.':preferred?'Supported by qualified CPU and wall comparisons on this input. This does not qualify the model for deployment.':'A lower observed runtime alone is not sufficient to choose a winner.'}</span></div><div class="runtime-showcase"><div class="runtime-card ${preferred==='O3'?'is-preferred':''}"><span class="small-label">O3 BASELINE</span><strong id="o3-runtime">${summary.baseline_ms.toFixed(2)} <small>ms</small></strong><span>Program runtime · ${clock.toUpperCase()}</span></div><div class="runtime-card ${preferred && preferred!=='O3'?'is-preferred':''}"><span class="small-label">NEUROCOMPILER CHOICE</span><strong id="nc-runtime">${summary.neurocompiler_ms.toFixed(2)} <small>ms</small></strong><span>${escape(pipeline(latest.decision.choice))} · ${clock.toUpperCase()}</span></div></div><p class="result-note">Paired geometric-mean executable times; analysis and compilation time are excluded. Other pipeline runtimes are listed below.</p>`;
  panel.innerHTML=`<div class="benchmark-heading"><h3>NeuroCompiler vs O3</h3><span class="badge ${summary.qualified?'green':'amber'}">${summary.same_executable?'SAME EXECUTABLE':summary.qualified?'DEMO MEASUREMENT':'UNRELIABLE MEASUREMENT'}</span></div><p class="outcome-headline">${escape(summary.headline)}</p>${runtimeCards}<div class="feature-strip"><div><strong>${difference}</strong><span>${summary.same_executable?'Exact code identity, not a measured speedup':summary.qualified?'Paired time difference on this input':'Observed point estimate only; not a reliable gain/loss'}</span></div><div><strong>${gap}</strong><span>Point-estimate gap to fastest qualified sample in this menu</span></div></div>${summary.best_measured_choice?`<p class="result-note">Fastest qualified point estimate: <strong>${escape(pipeline(summary.best_measured_choice))}</strong>. This is post-measurement exploration, separate from the pre-timing model prediction.</p>`:'<p class="result-note">The fastest reliable alternative cannot be identified because the measurement checks did not qualify.</p>'}${summary.failure_reasons.length?`<details class="input-details"><summary>Why the timing is inconclusive</summary><ul>${summary.failure_reasons.map(r=>`<li>${escape(r)}</li>`).join('')}</ul><p class="muted">The raw O3 self-control ratio is ${latest.measurement.cells.O3.clocks[clock].speedup.toFixed(3)}×; it measures timing noise, not a change in O3 code. All samples remain in the JSON report. Controls and model thresholds were not relaxed.</p></details>`:''}`;
}
function fourWayWinners(){const r=latest.measurement.four_way;return r.status==='reliable_winner' && r.controls_passed && r.complete_pair_coverage ? r.winner_options : [];}
function renderFourWayOutcome(){
  const ranking=latest.measurement.four_way, stats=ranking.clocks[clock], winner=fourWayWinners();
  const title=ranking.status==='identical'?'All four entries are the same executable':ranking.status==='reliable_winner'?(winner.length===1?`Prefer ${winner[0]} for this input`:`Shared preference: ${winner.join(' / ')} (same executable)`):ranking.status==='no_clear_winner'?'No clear winner':'No reliable preference yet';
  $('nc-summary').innerHTML=`<div class="benchmark-heading"><h3>O1 vs O2 vs O3 vs NeuroCompiler</h3><span class="badge ${winner.length?'green':'amber'}">${winner.length?'HEAD-TO-HEAD DEMO RESULT':'OBSERVED TIMES / CHECK QUALITY'}</span></div><div class="preference-banner ${winner.length?'has-preference':''}"><span class="small-label">FOUR-WAY DEMO PREFERENCE / BOTH CLOCKS</span><strong id="preferred-option">${title}</strong><span>${ranking.status==='reliable_winner'?'The winning executable passed self-controls and direct adjusted-interval comparisons against every distinct competitor on both clocks.':'Observed numbers alone do not establish a winner. Identical entries share one executable and measurement.'}</span></div><div class="runtime-showcase four-way">${Object.entries(stats.options).map(([label,option])=>`<div class="runtime-card ${winner.includes(label)?'is-preferred':''}"><span class="small-label">${label==='NeuroCompiler'?'NEUROCOMPILER CHOICE':label+' BASELINE'}</span><strong id="${label==='NeuroCompiler'?'nc':label.toLowerCase()}-runtime">${option.runtime_ms.toFixed(2)} <small>ms</small></strong><span>${label==='NeuroCompiler'?escape(pipeline(option.artifact)):label} · ${clock.toUpperCase()}</span>${option.same_as.length?`<span class="identity-note">Same executable as ${escape(option.same_as.join(' / '))}</span>`:''}</div>`).join('')}</div><p class="result-note">Geometric-mean native executable times, with equal observations per distinct executable. Model inference and compilation are excluded. Identical entries reuse measurements. O1/O2 are comparison baselines; the current model selects from its original four pipelines.</p><div class="feature-strip"><div><strong>${escape(stats.fastest_observed_options.join(' / '))}</strong><span>Fastest observed on ${clock.toUpperCase()}; ${winner.length?'see the confirmed demo preference above':'not a reliable winner'}</span></div><div><strong>${stats.observed_nc_gap_percent.toFixed(1)}%</strong><span>Observed NeuroCompiler time gap to fastest point estimate; ${winner.length?'input-specific demo result':'unreliable until quality checks qualify'}</span></div></div><details class="input-details"><summary>How the four-way result is checked</summary><p class="muted">${escape(ranking.scope)}</p><p class="muted">${ranking.distinct_executables} distinct executable(s), ${ranking.head_to_head_cells} direct comparison cell(s). All executable self-controls passed: ${ranking.controls_passed}. All direct comparisons qualified: ${ranking.all_pairs_qualified}. A shared O3/NeuroCompiler winner is not a learned gain over O3.</p></details>`;
  const caption=$('timing-chart')?.parentElement.nextElementSibling;
  if(caption)caption.textContent='OBSERVED GEOMETRIC-MEAN RUNTIME · LOWER IS FASTER · PREFERENCE REQUIRES HEAD-TO-HEAD CHECKS';
}
function renderFourWayTable(){
  const ranking=latest.measurement.four_way, stats=ranking.clocks[clock], base=stats.options.O3.runtime_ms;
  const header=$('timing-table').closest('table').querySelector('thead');
  header.innerHTML='<tr><th>ENTRY / ACTUAL PIPELINE</th><th>GEOMETRIC-MEAN RUNTIME</th><th>OBSERVED RATIO VS O3</th><th>RESULT</th></tr>';
  $('timing-table').innerHTML=Object.entries(stats.options).map(([label,option])=>`<tr><td>${escape(label)}${label==='NeuroCompiler'?`<span class="predicted-tag">Model chose ${escape(pipeline(option.artifact))}</span>`:''}</td><td class="runtime-cell">${option.runtime_ms.toFixed(2)} <small>ms</small></td><td>${(base/option.runtime_ms).toFixed(3)}×</td><td>${fourWayWinners().includes(label)?'Reliable demo preference':ranking.status==='identical'?'Same executable':ranking.status==='inconclusive'?'Inconclusive':'No clear advantage'}${option.same_as.length?`<span class="predicted-tag">Same executable as ${escape(option.same_as.join(' / '))}</span>`:''}</td></tr>`).join('');
}
function drawFourWayChart(){
  const canvas=$('timing-chart');if(!canvas || $('panel-benchmark').hidden)return;
  const width=canvas.clientWidth,height=canvas.clientHeight,dpr=window.devicePixelRatio||1;
  canvas.width=width*dpr;canvas.height=height*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
  const options=latest.measurement.four_way.clocks[clock].options, entries=Object.entries(options);
  const left=Math.min(140,width*.35),right=75,maximum=Math.max(...entries.map(([,o])=>o.runtime_ms))*1.08 || 1;
  entries.forEach(([label,option],i)=>{
    const y=25+i*48,bar=(width-left-right)*option.runtime_ms/maximum;
    ctx.font='11px ui-monospace,monospace';ctx.textAlign='right';ctx.fillStyle='#526f61';ctx.fillText(label,left-12,y+18);
    ctx.fillStyle=fourWayWinners().includes(label)?'#82b95c':label==='NeuroCompiler'?'#1d6a4e':'#c7d5bf';
    ctx.fillRect(left,y,Math.max(1,bar),26);ctx.textAlign='left';ctx.fillStyle='#355347';ctx.fillText(option.runtime_ms.toFixed(2)+' ms',left+bar+8,y+18);
  });
}

function drawChart() {
  if(latest.measurement.four_way){drawFourWayChart();return;}
  const canvas = $('timing-chart');
  if (!canvas || $('panel-benchmark').hidden) return;
  const width = canvas.clientWidth, height = canvas.clientHeight, dpr = window.devicePixelRatio || 1;
  canvas.width = width*dpr; canvas.height = height*dpr;
  const ctx = canvas.getContext('2d'); ctx.scale(dpr,dpr);
  const entries = Object.entries(latest.measurement.cells);
  const plotted = (choice,cell) => latest.decision.aliases[choice]==='O3' ? {speedup:1,interval:[1,1]} : cell.clocks[clock];
  const all = entries.flatMap(([choice,c])=>plotted(choice,c).interval);
  let low = Math.min(.95,...all), high = Math.max(1.05,...all);
  const pad = (high-low)*.12; low = Math.max(0,low-pad); high+=pad;
  const left = Math.min(155,width*.38), right=35, top=24, bottom=30;
  const x = value => left+(value-low)/(high-low)*(width-left-right);
  ctx.font='10px ui-monospace, monospace'; ctx.fillStyle='#789087'; ctx.strokeStyle='#e4ebe3';
  for(let i=0;i<=4;i++) {
    const value=low+(high-low)*i/4, position=x(value);
    ctx.beginPath();ctx.moveTo(position,top-8);ctx.lineTo(position,height-bottom);ctx.stroke();
    ctx.textAlign='center';ctx.fillText(`${value.toFixed(2)}×`,position,height-9);
  }
  ctx.strokeStyle='#789087';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(x(1),top-10);ctx.lineTo(x(1),height-bottom);ctx.stroke();ctx.setLineDash([]);
  entries.forEach(([choice,cell],i)=>{
    const y=top+20+i*(height-top-bottom-25)/Math.max(1,entries.length-1),stat=plotted(choice,cell);
    const selected=choice===latest.decision.choice;
    ctx.textAlign='right';ctx.fillStyle=selected?'#1d6a4e':'#647572';ctx.font=`${selected?'600 ':''}${width<500?'8':'10'}px ui-monospace, monospace`;
    ctx.fillText(shortLabels[choice],left-12,y+3);
    ctx.strokeStyle=selected?'#2f7950':'#a2b4a1';ctx.lineWidth=selected?3:2;
    ctx.beginPath();ctx.moveTo(x(stat.interval[0]),y);ctx.lineTo(x(stat.interval[1]),y);ctx.stroke();
    [stat.interval[0],stat.interval[1]].forEach(v=>{ctx.beginPath();ctx.moveTo(x(v),y-4);ctx.lineTo(x(v),y+4);ctx.stroke();});
    ctx.fillStyle=selected?'#1d6a4e':'#83997f';ctx.beginPath();ctx.arc(x(stat.speedup),y,selected?5:4,0,Math.PI*2);ctx.fill();
  });
}
window.addEventListener('resize',()=>{if(latest?.measurement?.status==='completed')drawChart();});

let irSequence = 0;
async function renderIR() {
  if (!analysis || dirty || !$('ir-choice').value) return;
  const sequence = ++irSequence, choice = $('ir-choice').value, analysisId=analysis.id;
  try {
    const [base,candidate] = await Promise.all(['O3',choice].map(c=>fetch(`/api/jobs/${analysis.id}/ir/${c}`).then(r=>{if(!r.ok)throw new Error('IR unavailable.');return r.text();})));
    if(sequence!==irSequence || !analysis || analysis.id!==analysisId || dirty) return;
    const baseLines=new Set(base.split('\n')), candidateLines=new Set(candidate.split('\n'));
    // Highlight lines unique to either module; this is a set comparison, not
    // an instruction-aligned semantic diff. Keep large modules responsive.
    const render=(text,other)=>text.length>250000?escape(text):text.split('\n').map(line=>`<span class="${line && !other.has(line)?'ir-changed':'ir-line'}">${escape(line)||' '}</span>`).join('');
    $('ir-base').innerHTML=render(base,candidateLines);$('ir-candidate').innerHTML=render(candidate,baseLines);
    $('ir-title').textContent=`CANDIDATE / ${pipeline(choice)}`;
    const metrics=analysis.comparison_metrics || analysis.decision.metrics;
    const bm=metrics.O3, cm=metrics[choice];
    $('ir-metrics').innerHTML=`<div class="ir-statline"><span>IR instructions: ${bm.instructions} → ${cm.instructions}</span><span>Blocks: ${bm.blocks} → ${cm.blocks}</span><span>Vector instructions: ${bm.vector} → ${cm.vector}</span><span>Highlight: text lines absent from the other module</span></div>`;
  } catch(error){showError(error.message);}
}
$('ir-choice').addEventListener('change',renderIR);

async function refreshScorecard() {
  const panel=$('session-scorecard');
  try {
    const data=await api('/api/scorecard'), t=data.totals;
    const groupNames={training_example:'Known training example',bundled_demo:'Other bundled demos',custom:'Custom / unverified provenance'};
    panel.innerHTML=`<div class="scorecard-metrics"><div><strong>${t.inputs}</strong><span>Input/model pairs assessed</span></div><div><strong>${t.kept_o3} / ${t.changed_choice}</strong><span>Kept O3 / chose different code</span></div><div><strong>${t.wins} / ${t.losses}</strong><span>NeuroCompiler vs O3: qualified wins / losses</span></div><div><strong>${t.unchanged} / ${t.inconclusive}</strong><span>Unchanged code / inconclusive differences</span></div></div><div class="four-way-scorecard"><h3>Qualified four-way preferences</h3><div class="scorecard-metrics five">${['O1','O2','O3','NeuroCompiler','shared'].map(k=>`<div><strong>${t['best_'+k]||0}</strong><span>${k==='shared'?'Shared executable winner':escape(k)}</span></div>`).join('')}</div><p class="result-note">${t.four_way_inconclusive||0} inconclusive; ${t.four_way_no_clear||0} no clear winner; ${t.four_way_identical||0} all entries identical. Training and custom inputs remain separate in the table.</p></div><div class="table-scroll"><table><thead><tr><th>INPUT PROVENANCE</th><th>ASSESSED</th><th>TESTED</th><th>NC WINS VS O3</th><th>NC LOSSES VS O3</th><th>UNCHANGED</th><th>NO CLEAR DIFFERENCE</th><th>INCONCLUSIVE</th><th>BLOCKED</th><th>FOUR-WAY PREFERENCES</th></tr></thead><tbody>${Object.entries(data.groups).map(([key,g])=>`<tr><td>${groupNames[key]}</td>${['inputs','tested','wins','losses','unchanged','no_clear_difference','inconclusive','blocked'].map(k=>`<td>${g[k]}</td>`).join('')}<td>O1 ${g.best_O1||0} / O2 ${g.best_O2||0} / O3 ${g.best_O3||0} / NC ${g.best_NeuroCompiler||0} / Shared ${g.best_shared||0}</td></tr>`).join('')}</tbody></table></div><p class="result-note">${t.tested} input/model pair(s) have a completed comparison; ${t.unqualified_timings} failed timing checks. Unchanged-code results can also have failed timing checks. ${data.source_files} distinct source text(s), not independent program families.</p><details class="input-details"><summary>How these session counts work</summary><p class="muted">${escape(data.scope)}</p><p class="muted">${escape(data.provenance_note)}</p><p class="muted">${escape(data.quality_note)}</p></details>`;
  } catch(error) { panel.textContent='Session scorecard unavailable. '+error.message; }
}

async function init() {
  try {
    session = await api('/api/session');
    $('connection').classList.add('ready');$('connection').lastChild.textContent='LLVM 10 / ready';
    $('example').innerHTML=session.examples.map(e=>`<option value="${escape(e.id)}">${escape(e.name)}</option>`).join('');
    $('example').disabled=false;loadExample();
    $('decision-empty').querySelector('h3').textContent='A decision starts with your code.';
    const m=session.model;
    $('model-details').innerHTML=`<dl><dt>MODEL</dt><dd>Ridge regression / ${escape(m.policy)}</dd><dt>TRAINING COVERAGE</dt><dd>${m.real_training_programs} real + ${m.synthetic_training_programs} synthetic programs<br>${m.training_rows} candidate targets · 156 fields per target</dd><dt>APPROVED POLICY</dt><dd>O3 · experimental model not deployment-qualified</dd><dt>INFERENCE</dt><dd>Portable JSON coefficients from the existing model. No retraining, sklearn runtime, or pickle loading.</dd><dt>ORIGINAL MODEL SHA256</dt><dd class="hash">${escape(m.source_model_sha256)}</dd></dl>`;
    const history=await api('/api/jobs');
    const previousAnalysis=history.jobs.find(j=>j.status==='completed' && j.result.kind==='analysis');
    if(previousAnalysis) {
      analysis=previousAnalysis.result;dirty=false;
      restoreInput(analysis);
      $('filename').textContent='last-experiment.c';renderDecision(analysis);
      const priorComparison=history.jobs.find(j=>j.status==='completed' && j.result.analysis_id===analysis.id);
      latest=priorComparison?priorComparison.result:analysis;
      if(priorComparison)renderBenchmark(latest);
      $('downloads').hidden=false;$('download-md').href=`/api/jobs/${latest.id}/report.md`;$('download-json').href=`/api/jobs/${latest.id}/report.json`;
      $('step-compile').className=$('step-predict').className='done';
    }
    await refreshScorecard();
    const running=history.jobs.find(j=>j.status==='running');
    if(running) startProgress(running);
    updateButtons();
  } catch(error){$('connection').classList.add('offline');$('connection').lastChild.textContent='Backend unavailable';showError(`${error.message} Start the app with scripts/serve_presentation.py inside WSL2/Linux.`);}
}
init();
