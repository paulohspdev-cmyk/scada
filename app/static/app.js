const $=s=>document.querySelector(s);
let generators=[];
let modelCatalog=[];

const metricLabels={
  rpm:'RPM',frequency:'Frequência',battery_voltage:'Bateria',oil_pressure:'Pressão óleo',
  coolant_temperature:'Temperatura motor',fuel_level:'Combustível',
  voltage_l1:'Tensão L1-N',voltage_l2:'Tensão L2-N',voltage_l3:'Tensão L3-N',
  voltage_l1_l2:'Tensão L1-L2',voltage_l2_l3:'Tensão L2-L3',voltage_l3_l1:'Tensão L3-L1',
  current_l1:'Corrente L1',current_l2:'Corrente L2',current_l3:'Corrente L3',power_kw:'Potência',
  run_hours:'Horas',controller_mode_raw:'Modo',binary_inputs_raw:'Entradas digitais'
};
const metricUnits={frequency:' Hz',battery_voltage:' V',oil_pressure:' bar',coolant_temperature:' °C',fuel_level:' %',rpm:' rpm',power_kw:' kW'};
const viewTitles={dashboard:'Visão Geral',generators:'Geradores',events:'Eventos',alarms:'Alarmes',trends:'Tendências',energy:'Rede & Carga',transfer:'Transferência',parallel:'Paralelismo',maintenance:'Manutenção',fuel:'Combustível',batteries:'Baterias',controllers:'Biblioteca de Controladoras',communications:'Comunicação',devices:'Modems & Gateways',reports:'Relatórios',audit:'Auditoria',settings:'Configurações'};

function statusBadge(status){
  const map={online:['ONLINE','online'],connected:['SEM DADOS','connected'],fault:['FALHA','fault'],offline:['OFFLINE','offline']};
  const [label,cls]=map[status]||map.offline;
  return `<span class="badge ${cls}">${label}</span>`;
}
function badge(g){return statusBadge(g.status||(g.connected&&g.poll_ok?'online':g.connected?'connected':'offline'))}
function niceKey(k){return metricLabels[k]||k.replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase())}
function formatMetric(k,v){
  if(v===null||v===undefined)return '-';
  if(k==='controller_mode_raw'){
    const modes={0:'OFF',1:'MAN',2:'AUTO',3:'TEST'};
    return modes[v]??v;
  }
  return `${v}${metricUnits[k]||''}`;
}
function metricBox(k,v){return `<div class="metric"><span>${niceKey(k)}</span><b>${formatMetric(k,v)}</b></div>`}
function modeOf(g){
  const v=(g.values||{}).controller_mode_raw;
  if(v===0)return 'OFF';if(v===1)return 'MAN';if(v===2)return 'AUTO';if(v===3)return 'TEST';
  return 'MODO --';
}
function cardMetrics(g){
  const v=g.values||{};
  const keys=['rpm','frequency','voltage_l1','battery_voltage'];
  return keys.map(k=>metricBox(k,v[k])).join('');
}
function generatorRunning(g){return Number((g.values||{}).rpm||0)>300}
function connectionLabel(g){return g.transport==='modbus_tcp'?'Modbus TCP / Ethernet':`TCP reverso ${g.listen_port}`}
function generatorCard(g){
  const running=generatorRunning(g);
  const values=g.values||{};
  const hasData=Object.keys(values).length>0;
  return `<article class="card" onclick="showGenerator(${g.id})">
    <div class="card-main">
      <div class="card-top"><div><span class="code">${g.code}</span><div class="name">${g.name}</div></div>${badge(g)}</div>
      <div class="meta">${g.customer||'Sem cliente'} · ${g.controller_type} ${g.controller_model||''}</div>
      <span class="mode-chip">${modeOf(g)}</span>
      <div class="power-flow">
        <div class="flow-node"><b>REDE</b><small>${values.voltage_l1??'-'} V</small></div>
        <div class="flow-line ${g.status==='online'?'on':''}"></div>
        <div class="flow-node"><b>CARGA</b><small>${values.power_kw??'-'} kW</small></div>
        <div class="flow-line ${running?'on':''}"></div>
        <div class="flow-node"><b>GERADOR</b><small>${values.rpm??0} rpm</small></div>
      </div>
      <div class="telemetry">${cardMetrics(g)}</div>
      ${hasData?'':'<div class="waiting">Aguardando telemetria homologada</div>'}
    </div>
    <div class="card-actions"><button class="cmd safe" disabled title="Preview: exige RBAC, confirmação e auditoria">START</button><button class="cmd danger" disabled title="Preview: exige RBAC, confirmação e auditoria">STOP</button><button class="cmd" disabled>AUTO</button><button class="cmd" disabled>TEST</button></div>
  </article>`;
}

async function refresh(){
  const [gs,ds]=await Promise.all([
    fetch('/api/generators').then(r=>r.json()),
    fetch('/api/dashboard').then(r=>r.json())
  ]);
  generators=gs;
  $('#kTotal').textContent=ds.total;
  $('#kOnline').textContent=ds.online;
  $('#kOffline').textContent=ds.offline;
  $('#kOperating').textContent=ds.operating;
  $('#kAlarm').textContent=ds.alarm;
  $('#cards').innerHTML=gs.length?gs.map(generatorCard).join(''):'<p class="note">Nenhum gerador cadastrado. Use “Adicionar gerador”.</p>';
  $('#generatorRows').innerHTML=gs.map(g=>`<tr><td><b>${g.code}</b></td><td>${g.customer||'-'}<br><small>${g.name}</small></td><td>${g.controller_type}<br><small>${g.controller_model||'-'}</small></td><td>${connectionLabel(g)}<br><small>Unit ${g.modbus_unit}</small></td><td>${badge(g)}</td><td><button class="link" onclick="showGenerator(${g.id})">Abrir</button></td></tr>`).join('');
}

async function refreshEvents(){
  const es=await fetch('/api/events').then(r=>r.json());
  $('#eventsList').innerHTML=es.map(e=>`<div class="event"><b>${e.code||'Sistema'} · ${e.level}</b><div>${e.message}</div><small>${new Date(e.created_at*1000).toLocaleString()}</small></div>`).join('')||'<p class="note">Sem eventos.</p>';
}

async function refreshControllerLibrary(){
  const el=$('#controllerLibrary');
  el.innerHTML='<p class="note">Carregando biblioteca...</p>';
  try{
    const packs=await fetch('/api/controller-library').then(r=>r.json());
    el.innerHTML=packs.map(p=>{
      const caps=Object.entries(p.capabilities||{}).filter(([,v])=>v).map(([k])=>`<span class="cap">${k.replaceAll('_',' ')}</span>`).join('');
      const status=p.status==='field_validated'?'HOMOLOGADO':p.status==='investigation'?'LABORATÓRIO':p.status;
      return `<div class="library-card"><div class="scope ${p.scope}">${p.scope==='production'?'PRODUÇÃO':'LAB'} · ${status}</div><h3>${p.manufacturer} ${p.model}</h3><p>${p.notes||''}</p><div class="caps">${caps||'<span class="cap">sem capacidades liberadas</span>'}</div><p><small>${p.pack_path}</small></p></div>`;
    }).join('')||'<p class="note">Nenhum Controller Pack cadastrado.</p>';
  }catch(e){el.innerHTML='<p class="error">Falha ao carregar Controller Library.</p>'}
}

function showGenerator(id){
  const g=generators.find(x=>x.id===id);if(!g)return;
  const running=generatorRunning(g);
  $('#drawer').classList.remove('hidden');
  $('#drawerContent').innerHTML=`
    <div class="detail-head"><small>${g.code}</small><h2>${g.name}</h2>${badge(g)}<p class="note">${g.customer||''} ${g.site?'· '+g.site:''}<br>${g.controller_type} ${g.controller_model||''}<br>${connectionLabel(g)} · Modbus ID ${g.modbus_unit}</p></div>
    <div class="power-flow"><div class="flow-node"><b>REDE</b><small>${(g.values||{}).voltage_l1??'-'} V</small></div><div class="flow-line ${g.status==='online'?'on':''}"></div><div class="flow-node"><b>CARGA</b><small>${(g.values||{}).power_kw??'-'} kW</small></div><div class="flow-line ${running?'on':''}"></div><div class="flow-node"><b>GERADOR</b><small>${(g.values||{}).rpm??0} rpm</small></div></div>
    <div class="control-preview"><button disabled>OFF</button><button disabled>MAN</button><button disabled>AUTO</button><button disabled>TEST</button><button disabled>START</button><button disabled>STOP</button><button disabled>MCB</button><button disabled>GCB</button></div>
    <p class="note">Comandos web estão visíveis apenas como preview. A execução será liberada por capacidade, usuário, confirmação, intertravamentos e auditoria.</p>
    <div class="detail-grid">${Object.entries(g.values||{}).map(([k,v])=>`<div class="detail-metric"><small>${niceKey(k)}</small><b>${formatMetric(k,v)}</b></div>`).join('')||'<p class="note">Aguardando dados da controladora.</p>'}</div>
    ${g.status==='fault'?`<p class="error">Comunicação: ${g.last_error||'falha de leitura'}</p>`:''}`;
}
function closeDrawer(){$('#drawer').classList.add('hidden')}
function closeModal(){$('#modal').classList.add('hidden');$('#formError').textContent=''}

async function loadControllerModels(){
  const type=$('#controllerType').value;const sel=$('#controllerModel');sel.innerHTML='<option value="">Carregando modelos...</option>';
  try{
    modelCatalog=await fetch('/api/controller-models?type='+encodeURIComponent(type)).then(r=>r.json());
    const families={};modelCatalog.forEach(m=>(families[m.family]??=[]).push(m));
    sel.innerHTML='<option value="">Selecione o modelo</option>';
    Object.entries(families).forEach(([family,items])=>{const group=document.createElement('optgroup');group.label=family;items.forEach(m=>{const o=document.createElement('option');o.value=m.model;o.textContent=m.model;group.appendChild(o)});sel.appendChild(group)});
  }catch(e){sel.innerHTML='<option value="">Erro ao carregar modelos</option>'}
}

$('#controllerType').onchange=loadControllerModels;
$('#addBtn').onclick=async()=>{$('#modal').classList.remove('hidden');await loadControllerModels()};
$('#generatorForm').onsubmit=async e=>{
  e.preventDefault();$('#formError').textContent='';const fd=new FormData(e.target);const data=Object.fromEntries(fd.entries());if(!data.listen_port)delete data.listen_port;data.modbus_unit=Number(data.modbus_unit||1);
  const r=await fetch('/api/generators',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const obj=await r.json();if(!r.ok){$('#formError').textContent=obj.error||'Erro ao cadastrar';return}e.target.reset();closeModal();await loadControllerModels();await refresh();
};

document.querySelectorAll('.nav').forEach(b=>b.onclick=async()=>{
  document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));const view=b.dataset.view;$('#'+view).classList.remove('hidden');$('#title').textContent=viewTitles[view]||b.textContent;if(view==='events')await refreshEvents();if(view==='controllers')await refreshControllerLibrary();
});

loadControllerModels();refresh();setInterval(refresh,3000);
