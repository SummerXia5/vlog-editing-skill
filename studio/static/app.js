'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clock = t => `${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
let project = null, active = null, filter = 'all', style = 'journal', styles = {}, currentView = 'library';
let inspectorSignature = '', toastTimer, refreshing = false;
function toast(message) { $('#toast').textContent=message; $('#toast').classList.remove('hidden'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.add('hidden'),7000); }
async function api(path, data) {
  const res = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Studio-Request':'1'},body:JSON.stringify(data)});
  const value=await res.json(); if(!res.ok) throw new Error(value.error || '请求失败'); return value;
}
function showView(view) {
  currentView=view;
  ['library','plan','delivery'].forEach(v=>{ $(`#${v}-view`).classList.toggle('hidden',v!==view); $(`.nav[data-view="${v}"]`).classList.toggle('active',v===view); });
  renderPlans();
}
async function bootstrap(preferred) {
  const state=await api('/api/state'); styles=state.styles;
  const picker=$('#project-picker'); picker.replaceChildren();
  if(!state.projects.length) picker.add(new Option('创建你的第一个项目',''));
  state.projects.forEach(p=>picker.add(new Option(p.name,p.id)));
  const wanted=preferred || localStorage.getItem('vlog-studio-project');
  if(state.projects.some(p=>p.id===wanted)) picker.value=wanted;
  await refresh();
}
async function refresh() {
  if(refreshing) return; const id=$('#project-picker').value;
  if(!id) {render();return;} refreshing=true;
  try {project=await api(`/api/projects/${id}`);localStorage.setItem('vlog-studio-project',id);render();}
  catch(e){toast(e.message);} finally {refreshing=false;}
}
function render() {
  $('#project-name').textContent=project?.name || '新的旅程';
  const assets=project?.assets || [], selects=project?.selects || [], exports=project?.exports || [];
  $('#asset-count').textContent=assets.length;$('#export-count').textContent=exports.length;$('#select-count').textContent=selects.length;
  const proxyCount=assets.filter(a=>a.is_proxy).length;
  $('#library-meta').textContent=assets.length ? `${assets.length} 个视频 · ${proxyCount} 个代理 · ${selects.length} 个已确认选段` : '添加 LRV 代理与原片，开始整理你的旅程。';
  $('#empty').classList.toggle('hidden',assets.length>0);
  const shown=assets.filter(a=>filter==='all'||(filter==='proxy'?a.is_proxy:!a.is_proxy));
  $('#asset-grid').innerHTML=shown.map(a=>`<button class="asset-card ${active===a.id?'selected':''}" data-asset="${a.id}"><div class="thumb">${a.poster?`<img src="/api/assets/${a.id}/poster" alt="${esc(a.name)} 预览帧">`:'<span class="placeholder-play">▷</span>'}<span class="tag">${a.is_proxy?'LRV / PROXY':'ORIGINAL'}</span><span class="duration">${a.duration?clock(a.duration):'待探测'}</span></div><div class="asset-info"><strong>${esc(a.name)}</strong><small>${a.metadata?`${a.metadata.video.width} × ${a.metadata.video.height} · `:''}${(a.bytes/1024/1024).toFixed(1)} MB · ${selects.some(s=>s.asset_id===a.id)?'含已保留片段':'尚未审看'}</small></div></button>`).join('');
  if(assets.length && !shown.length) $('#asset-grid').innerHTML='<p class="muted">这个分类还没有素材。</p>';
  $('#asset-grid').querySelectorAll('[data-asset]').forEach(b=>b.onclick=()=>{active=b.dataset.asset;inspectorSignature='';render();});
  renderInspector();
  $('#selects-list').innerHTML=selects.length?selects.map((s,i)=>{const a=assets.find(a=>a.id===s.original_id);return `<div class="select-row"><span class="number">${String(i+1).padStart(2,'0')}</span><div><strong>${esc(s.chapter)} · ${esc(a?.name)}</strong><small>${clock(s.in/30)} – ${clock((s.in+s.frames)/30)} · ${esc(s.note || '已确认选段')}</small></div><button data-remove="${s.id}" aria-label="移除选段 ${i+1}">×</button></div>`;}).join(''):'<p class="muted">还没有选段。点开素材，播放后标记 IN / OUT。</p>';
  $('#selects-list').querySelectorAll('[data-remove]').forEach(b=>b.onclick=async()=>{try{await api(`/api/projects/${project.id}/remove-select`,{select_id:b.dataset.remove});await refresh();}catch(e){toast(e.message);}});
  renderPlans();renderJobs();renderDeliveries();
}
function renderInspector() {
  const a=project?.assets.find(a=>a.id===active); const panel=$('#inspector'); panel.classList.toggle('hidden',!a);if(!a)return;
  const signature=JSON.stringify([a.id,a.status,a.preview,project.assets.filter(a=>!a.is_proxy).map(a=>a.id)]);
  if(signature===inspectorSignature)return;inspectorSignature=signature;
  const originals=project.assets.filter(a=>!a.is_proxy&&a.status==='ready');
  const stem=n=>n.toLowerCase().replace(/\.[^.]+$/,'').replace(/^lrv_/,'vid_');
  const candidates=originals.filter(o=>stem(o.name)===stem(a.name));
  panel.innerHTML=`<h3>${esc(a.name)}</h3>${a.preview?`<video id="source-player" controls playsinline preload="metadata" src="/api/assets/${a.id}/preview"></video>`:'<div class="callout">点击下方按钮生成浏览器预览。上传时只读取媒体信息，不自动解码全部原片。</div>'}
    <label><input type="checkbox" id="sdr-check">我已确认本段是 SDR（非 HDR）</label>
    ${!a.preview?`<button id="prepare-preview" class="secondary" ${a.status!=='ready'?'disabled':''}>${a.status==='ready'?'生成可播放预览':'正在读取媒体信息…'}</button>`:''}
    <form id="select-form"><div class="range-row"><label>IN · 秒<input type="number" id="in-time" min="0" step="0.001" value="0" required></label><label>OUT · 秒<input type="number" id="out-time" min="0" step="0.001" value="${Math.floor((a.duration||0)*30)/30}" required></label></div>
    <button type="button" id="mark-in" class="secondary">当前帧设为 IN</button> <button type="button" id="mark-out" class="secondary">设为 OUT</button>
    ${a.is_proxy?`<label>对应原片<select id="original-id"><option value="">选择原片（需核对同步）</option>${originals.map(o=>`<option value="${o.id}" ${candidates.length===1&&candidates[0].id===o.id?'selected':''}>${esc(o.name)}</option>`).join('')}</select></label><label><input type="checkbox" id="alignment-check">已核对代理与原片前后内容同步</label>`:''}
    <label>属于哪一章？<input id="chapter" value="旅程" maxlength="120"></label><label>片段类型<select id="category"><option value="experience">体验</option><option value="reaction">真实反应 / 互动</option><option value="scenery">风景</option><option value="detail">生活细节</option></select></label>
    <label>为什么留下？<textarea id="note" rows="2" maxlength="2000" placeholder="真实台词、动作、笑点或声音…"></textarea></label>
    <label><input type="checkbox" id="review-check" required>已播放并审看这段前后内容</label><label><input type="checkbox" id="audio-check">已听审本段声音（无音轨可不选）</label>
    <details open><summary>原片时间码</summary><p>填写已核对的起始时间码（秒或分数秒）。原片确实没有时间码时填 0；不是本段 IN 点。</p><input id="tc-start" placeholder="例如 0 或 3600" required aria-label="原片起始时间码"></details>
    <button type="submit" class="primary" ${a.status!=='ready'?'disabled':''}>＋ 保留这个瞬间</button></form>`;
  if($('#prepare-preview'))$('#prepare-preview').onclick=async()=>{try{await api(`/api/projects/${project.id}/preview`,{asset_id:a.id,sdr_confirmed:$('#sdr-check').checked});toast('预览已加入后台队列。');await refresh();}catch(e){toast(e.message);}};
  $('#mark-in').onclick=()=>{if($('#source-player'))$('#in-time').value=$('#source-player').currentTime.toFixed(3);};
  $('#mark-out').onclick=()=>{if($('#source-player'))$('#out-time').value=$('#source-player').currentTime.toFixed(3);};
  $('#select-form').onsubmit=async e=>{e.preventDefault();try{await api(`/api/projects/${project.id}/selects`,{asset_id:a.id,original_id:$('#original-id')?.value||a.id,in_seconds:Number($('#in-time').value),out_seconds:Number($('#out-time').value),chapter:$('#chapter').value,category:$('#category').value,note:$('#note').value,reviewed:$('#review-check').checked,audio_reviewed:$('#audio-check').checked,sdr_confirmed:$('#sdr-check').checked,alignment_confirmed:$('#alignment-check')?.checked||false,tc_start:$('#tc-start').value});toast('选段已保存。原视频保持完整。');await refresh();}catch(e){toast(e.message);}};
}
function orderedSelects(){const s=[...(project?.selects||[])];if(style!=='journal'){const tag=style==='cinematic'?'scenery':'reaction';s.sort((a,b)=>Number(b.category===tag)-Number(a.category===tag));}return s;}
function renderPlans(){
  const codes={journal:'01 / Journal',cinematic:'02 / Cinematic',playful:'03 / Playful'};
  $('#plan-cards').innerHTML=Object.entries(styles).map(([id,s])=>`<button class="plan-card ${id===style?'active':''}" data-style="${id}"><span>${codes[id]}</span><strong>${esc(s.name)}</strong><p>${esc(s.description)}</p><small>${id===style?'● 当前选择':'○ 选择这个方向'} · 排序模板</small></button>`).join('');
  $('#plan-cards').querySelectorAll('[data-style]').forEach(b=>b.onclick=()=>{style=b.dataset.style;renderPlans();});
  $('#plan-heading').textContent=styles[style]?.name||'旅行手记';$('#plan-description').textContent=styles[style]?.description||'';
  const selects=orderedSelects();$('#plan-sequence').innerHTML=selects.length?selects.map((s,i)=>`<div class="story-step"><span>${String(i+1).padStart(2,'0')}</span><span>${esc(s.chapter)}<br><span class="muted">${esc(s.note||'已审片')}</span></span><small>${(s.frames/30).toFixed(1)} 秒</small></div>`).join(''):'<p class="muted">先在素材库保留几个瞬间，故事线就会出现在这里。</p>';
  $('#export-button').disabled=!selects.length;
}
function renderJobs(){
  const names={inspect:'读取媒体信息',preview:'生成素材预览',export:'编译初剪与工程'}, statuses={queued:'等待中',running:'处理中',succeeded:'已完成',failed:'未完成'};
  const jobs=[...(project?.jobs||[])].reverse().slice(0,8);
  $('#jobs').innerHTML=jobs.length?jobs.map(j=>`<div class="job"><span>${j.status==='succeeded'?'✓':j.status==='failed'?'!':'◌'}</span><div>${names[j.task]||esc(j.task)}${j.error?`<div class="job-error">${esc(j.error)}</div>`:''}</div><span class="status ${j.status}">${statuses[j.status]}</span>${j.status==='failed'?`<button data-retry="${j.id}">重试</button>`:''}</div>`).join(''):'<p class="muted">添加素材后，这里会显示实际处理进度。</p>';
  $('#jobs').querySelectorAll('[data-retry]').forEach(b=>b.onclick=async()=>{try{await api(`/api/projects/${project.id}/retry`,{job_id:b.dataset.retry});await refresh();}catch(e){toast(e.message);}});
}
function renderDeliveries(){
  const exports=project?.exports||[];
  // Preserve playing videos during job polling.
  const signature=exports.map(e=>e.id).join(','); if($('#deliveries').dataset.signature===signature)return;$('#deliveries').dataset.signature=signature;
  $('#deliveries').innerHTML=exports.length?[...exports].reverse().map((e,i)=>`<article class="delivery-card"><video controls playsinline preload="metadata" src="/api/exports/${e.id}/preview"></video><div><span class="eyebrow">ROUGH CUT / VERSION ${String(exports.length-i).padStart(2,'0')}</span><h3>${esc(styles[e.style]?.name)}</h3><p>${clock(e.duration)} · 原声初剪 · 下载后继续编辑<br>预览完整解码通过 · FCP 原生导入未验证</p><div class="download-row"><a class="primary" href="/api/exports/${e.id}/preview?download=1">下载 MP4 ↓</a><a class="secondary" href="/api/exports/${e.id}/package">FCP 工程包 ↓</a><a class="secondary" href="/api/exports/${e.id}/xml">FCPXML ↓</a></div><p class="muted">工程包包含 XML、剪辑表、编译配置与校验记录，不打包原视频。</p></div></article>`).join(''):'<div class="empty"><h3>你的第一版初剪，正在路上。</h3><p>先保留选段，再到「故事方案」生成。</p></div>';
}
function startUpload(){if(!project){$('#project-dialog').showModal();return;}$('#file-input').click();}
async function uploadFiles(files){
  if(!project)return;const projectId=project.id;
  for(let i=0;i<files.length;i++){
    const file=files[i];toast(`上传 ${i+1}/${files.length}：${file.name}`);
    try{await new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST',`/api/projects/${projectId}/upload`);xhr.setRequestHeader('X-Studio-Request','1');xhr.setRequestHeader('X-Filename',encodeURIComponent(file.name));xhr.upload.onprogress=e=>{if(e.lengthComputable)toast(`上传 ${i+1}/${files.length} · ${Math.round(e.loaded/e.total*100)}%：${file.name}`);};xhr.onload=()=>{let data;try{data=JSON.parse(xhr.responseText);}catch{reject(new Error('上传响应异常'));return;}xhr.status<300?resolve(data):reject(new Error(data.error));};xhr.onerror=()=>reject(new Error('上传中断，可重新选择同一文件重试'));xhr.send(file);});}
    catch(e){toast(e.message);break;}
  }
  $('#file-input').value='';await refresh();
}
$('#new-project').onclick=()=>$('#project-dialog').showModal();$('#cancel-project').onclick=()=>$('#project-dialog').close();
$('#project-form').onsubmit=async e=>{e.preventDefault();try{const p=await api('/api/projects',{name:$('#project-title').value,brief:$('#project-brief').value});$('#project-dialog').close();active=null;inspectorSignature='';await bootstrap(p.id);toast('项目已创建。现在可以添加素材。');}catch(e){toast(e.message);}};
$('#project-picker').onchange=()=>{active=null;inspectorSignature='';project=null;$('#deliveries').dataset.signature='unset';refresh();};
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>showView(b.dataset.view));document.querySelectorAll('.filter').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x===b));render();});
$('#upload-main').onclick=startUpload;$('#upload-empty').onclick=startUpload;$('#file-input').onchange=e=>uploadFiles([...e.target.files]);
$('#export-button').onclick=async()=>{try{await api(`/api/projects/${project.id}/export`,{style,shape:$('#shape').value});showView('delivery');toast('开始生成独立版本，可在处理记录查看进度。');await refresh();}catch(e){toast(e.message);}};
bootstrap().catch(e=>toast(e.message));setInterval(()=>{if(project?.jobs.some(j=>['queued','running'].includes(j.status)))refresh();},1800);
