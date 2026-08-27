const $=s=>document.querySelector(s);
let generators=[];
let modelCatalog=[];

function statusBadge(status){
  const map={
    online:['ONLINE','online'],
    connected:['CONECTADO','connected'],
    fault:['FALHA','fault'],
    offline:['OFFLINE','offline']
  };
  const [label,cls]=map[status]||map.offline;
  return `<span class="badge ${cls}">${label}</span>`;
}
function badge(g){return statusBadge(g.status||(g.connected&&g.poll_ok?'online':g.connected?'connected':'offline'))}
function profileBadge(profile){
  if(!profile)return '<span class="profile-badge pending">SEM PERFIL</span>';
  const state=profile.state||'awaiting_import';
  const cls=state==='active_builtin'?'validated':state==='active_imported'?'imported':state==='reference'?'reference':'pending';
  return `<span class="profile-badge ${cls}">${profile.label||'PERFIL'}</span>`;
}
function catalogBadge(item){
  const status=item?.profile_status||'unknown';
  const cls=status==='validated'?'validated':status==='reference'?'reference':status==='import_required'?'imported':'pending';
  return `<span class="profile-badge ${cls}">${item?.profile_label||'SEM PERFIL'}</span>`;
}
function niceKey(k){return k.replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase())}
function metricEntries(g,n=4){
  return Object.entries(g.values||{}).slice(0,n).map(([k,v])=>`<div class="metric"><span>${niceKey(k)}</span><b>${v}</b></div>`).join('')
}

async function refresh(){
  const [gs,ds]=await Promise.all([
    fetch('/api/generators').then(r=>r.json()),
    fetch('/api/dashboard').then(r=>r.json())
  ]);
  generators=gs;
  $('#kTotal').textContent=ds.total;
  $('#kOnline').textContent=ds.online;
  $('#kConnected').textContent=ds.connected||0;
  $('#kOffline').textContent=ds.offline;
  $('#kOperating').textContent=ds.operating;
  $('#kAlarm').textContent=ds.alarm;

  $('#cards').innerHTML=gs.length?gs.map(g=>`
    <div class="card" onclick="showGenerator(${g.id})">
      <div class="card-top"><span class="code">${g.code}</span>${badge(g)}</div>
      <div class="name">${g.name}</div>
      <div class="meta">${g.customer||'Sem cliente'} · ${g.controller_type} ${g.controller_model||''} · TCP ${g.listen_port} / ID ${g.modbus_unit}</div>
      <div class="profile-row">${profileBadge(g.profile)}</div>
      <div class="telemetry">${metricEntries(g)}</div>
    </div>`).join(''):'<p class="note">Nenhum gerador cadastrado. Use “Adicionar gerador”.</p>';

  $('#generatorRows').innerHTML=gs.map(g=>`
    <tr>
      <td><b>${g.code}</b></td>
      <td>${g.customer||'-'}<br><small>${g.name}</small></td>
      <td>${g.controller_type}<br><small>${g.controller_model||'-'}</small></td>
      <td>${g.listen_port}<br><small>Unit ${g.modbus_unit}</small></td>
      <td>${profileBadge(g.profile)}</td>
      <td>${badge(g)}</td>
      <td><button class="link" onclick="showGenerator(${g.id})">Abrir</button></td>
    </tr>`).join('');
}

async function refreshEvents(){
  const es=await fetch('/api/events').then(r=>r.json());
  $('#eventsList').innerHTML=es.map(e=>`<div class="event"><b>${e.code||'Sistema'} · ${e.level}</b><div>${e.message}</div><small>${new Date(e.created_at*1000).toLocaleString()}</small></div>`).join('')||'<p class="note">Sem eventos.</p>'
}

function showGenerator(id){
  const g=generators.find(x=>x.id===id);
  if(!g)return;
  const p=g.profile||{};
  const importAction=p.requires_import||p.state==='active_imported'||p.state==='imported_no_active_points';
  $('#drawer').classList.remove('hidden');
  $('#drawerContent').innerHTML=`
    <div class="detail-head">
      <small>${g.code}</small><h2>${g.name}</h2>${badge(g)}
      <p class="note">${g.customer||''} ${g.site?'· '+g.site:''}<br>${g.controller_type} ${g.controller_model||''}<br>Modem TCP Client → servidor porta <b>${g.listen_port}</b> · Unit ID ${g.modbus_unit}</p>
    </div>
    <div class="profile-panel">
      <div><small>Perfil Modbus</small><div>${profileBadge(p)}</div></div>
      <p class="note">${p.source_name?`Fonte: ${p.source_name}<br>`:''}${p.active_points!=null?`Pontos ativos: ${p.active_points} / ${p.points||0}`:''}</p>
      ${importAction?`
        <input id="drawerProfileFile" type="file" accept=".csv,.txt,.tsv,.json" class="hidden" onchange="importProfile(${g.id},this.files[0])">
        <button class="secondary" onclick="$('#drawerProfileFile').click()">${p.state==='active_imported'?'Substituir mapa':'Importar mapa InteliConfig/LiteEdit'}</button>
      `:''}
    </div>
    <div class="detail-grid">${Object.entries(g.values||{}).map(([k,v])=>`<div class="detail-metric"><small>${niceKey(k)}</small><b>${v}</b></div>`).join('')||'<p class="note">Aguardando telemetria.</p>'}</div>
    <p class="note">Peer: ${g.peer||'-'}<br>Último erro: ${g.last_error||'-'}</p>`;
}
function closeDrawer(){$('#drawer').classList.add('hidden')}
function closeModal(){$('#modal').classList.add('hidden');$('#formError').textContent=''}

async function importProfile(id,file){
  if(!file)return;
  const fd=new FormData();fd.append('file',file);
  const r=await fetch(`/api/generators/${id}/profile/import`,{method:'POST',body:fd});
  const x=await r.json();
  if(!r.ok){alert(x.error||'Erro ao importar mapa');return}
  await refresh();
  showGenerator(id);
  alert(`Mapa importado: ${x.active_points} pontos ativos, ${x.review_points} para revisão.`);
}

function updateModelHint(){
  const name=$('#controllerModel').value;
  const item=modelCatalog.find(x=>x.model===name);
  $('#modelHint').textContent=item?item.hint:'Selecione o modelo para carregar o perfil de comunicação correto.';
  $('#modelProfileBadge').innerHTML=item?catalogBadge(item):'';
  $('#profileImportBox').classList.toggle('hidden',!(item&&item.requires_import));
}

async function loadControllerModels(){
  const type=$('#controllerType').value;
  const sel=$('#controllerModel');
  sel.innerHTML='<option value="">Carregando modelos...</option>';
  try{
    modelCatalog=await fetch('/api/controller-models?type='+encodeURIComponent(type)).then(r=>r.json());
    const families={};
    modelCatalog.forEach(m=>(families[m.family]??=[]).push(m));
    sel.innerHTML='<option value="">Selecione o modelo</option>';
    Object.entries(families).forEach(([family,items])=>{
      const group=document.createElement('optgroup');group.label=family;
      items.forEach(m=>{const o=document.createElement('option');o.value=m.model;o.textContent=`${m.model} — ${m.profile_label}`;group.appendChild(o)});
      sel.appendChild(group);
    });
    updateModelHint();
  }catch(e){
    sel.innerHTML='<option value="">Erro ao carregar modelos</option>';
    $('#modelHint').textContent='Falha ao carregar catálogo de controladoras.';
  }
}

async function loadControllerLibrary(){
  const brand=$('#libraryBrand').value;
  const rows=await fetch('/api/controller-models?type='+encodeURIComponent(brand)).then(r=>r.json());
  $('#controllerRows').innerHTML=rows.map(m=>`
    <tr>
      <td>${m.family}</td>
      <td><b>${m.model}</b></td>
      <td>${catalogBadge(m)}</td>
      <td><small>${m.hint}</small></td>
    </tr>`).join('');
}

$('#controllerType').onchange=loadControllerModels;
$('#controllerModel').onchange=updateModelHint;
$('#libraryBrand').onchange=loadControllerLibrary;
$('#addBtn').onclick=async()=>{
  $('#modal').classList.remove('hidden');
  $('#profileFile').value='';
  await loadControllerModels();
};

$('#generatorForm').onsubmit=async e=>{
  e.preventDefault();
  $('#formError').textContent='';
  const file=$('#profileFile').files[0];
  const fd=new FormData(e.target);
  const data=Object.fromEntries(fd.entries());
  delete data.profile_file;
  if(!data.listen_port)delete data.listen_port;
  data.modbus_unit=Number(data.modbus_unit||1);

  const r=await fetch('/api/generators',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const obj=await r.json();
  if(!r.ok){$('#formError').textContent=obj.error||'Erro ao cadastrar';return}

  if(file){
    const upload=new FormData();upload.append('file',file);
    const pr=await fetch(`/api/generators/${obj.id}/profile/import`,{method:'POST',body:upload});
    const px=await pr.json();
    if(!pr.ok){
      $('#formError').textContent=`Gerador cadastrado, mas o mapa não foi importado: ${px.error||'erro'}`;
      await refresh();
      return;
    }
  }

  e.target.reset();
  closeModal();
  await loadControllerModels();
  await refresh();
};

document.querySelectorAll('.nav').forEach(b=>b.onclick=async()=>{
  document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));
  $('#'+b.dataset.view).classList.remove('hidden');
  $('#title').textContent=b.textContent;
  if(b.dataset.view==='events')await refreshEvents();
  if(b.dataset.view==='controllers')await loadControllerLibrary();
});

loadControllerModels();
loadControllerLibrary();
refresh();
setInterval(refresh,3000);
