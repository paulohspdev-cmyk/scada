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
    const modes={0:'OFF',1:'MAN',2:'AUT',3:'TEST'};
    return modes[v]??v;
  }
  return `${v}${metricUnits[k]||''}`;
}
function metricEntries(g,n=6){
  return Object.entries(g.values||{}).slice(0,n).map(([k,v])=>`<div class="metric"><span>${niceKey(k)}</span><b>${formatMetric(k,v)}</b></div>`).join('')
}

function raw(g,key){return (g.values||{})[key]}
function shown(g,key,unit='',digits=null){
  const value=raw(g,key);
  if(value===null||value===undefined||value==='')return `--${unit}`;
  const num=Number(value);
  if(Number.isFinite(num)){
    const out=digits===null?String(value):num.toFixed(digits).replace('.',',');
    return `${out}${unit}`;
  }
  return `${value}${unit}`;
}
function controllerMode(g){
  const m=raw(g,'controller_mode_raw');
  const modes={0:'OFF',1:'MAN',2:'AUTO',3:'TEST'};
  return modes[m]??'--';
}
function isRunning(g){return Number(raw(g,'rpm')||0)>300}
function isOnline(g){return g.status==='online'||(g.connected&&g.poll_ok)}
function gaugeNeedle(rpm){
  const n=Math.max(0,Math.min(4000,Number(rpm)||0));
  const deg=-105+(n/4000)*210;
  const rad=deg*Math.PI/180;
  const x=100+64*Math.cos(rad);
  const y=88+64*Math.sin(rad);
  return {x:x.toFixed(1),y:y.toFixed(1)};
}
function rpmGauge(g){
  const rpm=Number(raw(g,'rpm')||0);
  const p=gaugeNeedle(rpm);
  return `<svg class="rpm-gauge" viewBox="0 0 200 116" aria-label="RPM ${rpm}">
    <path d="M24 91 A76 76 0 0 1 176 91" pathLength="100" class="gauge-track"/>
    <path d="M24 91 A76 76 0 0 1 151 34" pathLength="100" class="gauge-green"/>
    <path d="M151 34 A76 76 0 0 1 169 57" pathLength="100" class="gauge-yellow"/>
    <path d="M169 57 A76 76 0 0 1 176 91" pathLength="100" class="gauge-red"/>
    <g class="gauge-ticks">
      <text x="17" y="103">0</text><text x="30" y="44">1000</text><text x="88" y="20">2000</text><text x="147" y="44">3000</text><text x="174" y="103">4000</text>
    </g>
    <line x1="100" y1="88" x2="${p.x}" y2="${p.y}" class="gauge-needle"/>
    <circle cx="100" cy="88" r="6" class="gauge-hub"/>
    <text x="100" y="76" class="gauge-label">RPM</text>
    <text x="100" y="105" class="gauge-value">${rpm}</text>
  </svg>`;
}
function engineRow(icon,label,value,unit='',digits=null,maintenance=false){
  return `<div class="engine-row ${maintenance?'maintenance-row':''}"><span class="engine-icon">${icon}</span><span class="engine-label">${label}</span><span class="engine-line"></span><strong>${value===null||value===undefined?'--':(Number.isFinite(Number(value))&&digits!==null?Number(value).toFixed(digits).replace('.',','):value)}${unit}</strong></div>`;
}
function voltageRow(label,mains,generator){
  const fmt=v=>v===null||v===undefined?'--':`${v} V`;
  return `<div class="voltage-row"><span>${label}</span><b>${fmt(mains)}</b><b class="gen-v">${fmt(generator)}</b></div>`;
}
function industrialCard(g){
  const v=g.values||{};
  const running=isRunning(g);
  const online=isOnline(g);
  const mode=controllerMode(g);
  const alarm=g.status==='fault';
  const rpm=Number(v.rpm||0);
  return `<article class="generator-card-v2 ${online?'is-online':'is-offline'}" onclick="showGenerator(${g.id})">
    <div class="gc-head">
      <div class="gc-title"><span class="gen-round">G</span><strong>${g.name||g.code}</strong></div>
      <div class="gc-alerts"><span class="warn-triangle">△</span><span class="alarm-count ${alarm?'active':''}">${alarm?'1':'0'}</span></div>
    </div>

    <section class="gc-section power-section">
      <div class="section-title-row"><strong>POWER FLOW</strong><span>MODE: <b>${mode}</b></span></div>
      <div class="power-canvas">
        <div class="pwr-fail">PWR<br>FAIL</div>
        <div class="mains-symbol"><span>✦</span></div>
        <div class="freq-top">${shown(g,'frequency',' Hz',1)}</div>

        <div class="switch-stack">
          <label>MCB</label><button type="button" disabled onclick="event.stopPropagation()">I</button><button type="button" class="off" disabled onclick="event.stopPropagation()">O</button>
          <label>GCB</label><button type="button" disabled onclick="event.stopPropagation()">I</button><button type="button" class="off" disabled onclick="event.stopPropagation()">O</button>
        </div>

        <div class="bus ${online?'energized':''}">
          <span class="bus-dot d1"></span><span class="bus-dot d2"></span><span class="bus-dot d3"></span>
          <span class="bus-breaker top"></span><span class="bus-breaker bottom ${running?'closed':''}"></span>
        </div>
        <div class="load-branch ${running?'energized':''}"></div>
        <div class="load-box"><span>⌂</span><b>LOAD</b><strong>${shown(g,'power_kw',' kW',1)}</strong></div>
        <div class="generator-symbol">G</div>
        <div class="freq-bottom">${shown(g,'frequency',' Hz',1)}</div>

        <div class="run-buttons">
          <button type="button" class="start" disabled onclick="event.stopPropagation()">START</button>
          <button type="button" class="stop" disabled onclick="event.stopPropagation()">STOP</button>
        </div>
      </div>
    </section>

    <section class="gc-section engine-section">
      <div class="section-title">ENGINE STATUS</div>
      ${engineRow('◒','Oil Pressure',v.oil_pressure,' bar',1)}
      ${engineRow('♨','Coolant Temp.',v.coolant_temperature,' °C',0)}
      ${engineRow('▥','Fuel Level',v.fuel_level,' %',0)}
      ${engineRow('▣','Battery Voltage',v.battery_voltage,' V',1)}
      ${engineRow('ϟ','Alternator Volt.',v.alternator_voltage,' V',1)}
      ${engineRow('◷','Maintenance',v.maintenance_hours,' h',0,true)}
      ${engineRow('◴','Run Hours',v.run_hours,' h',1)}
    </section>

    <section class="gc-section rpm-section">
      <div class="section-title">RPM</div>
      ${rpmGauge(g)}
    </section>

    <section class="gc-section voltage-section">
      <div class="section-title voltage-title"><span>MAINS / GENERATOR</span><small><b>MAINS</b><b>GENERATOR</b></small></div>
      ${voltageRow('L1-N Voltage',v.mains_voltage_l1,v.voltage_l1)}
      ${voltageRow('L2-N Voltage',v.mains_voltage_l2,v.voltage_l2)}
      ${voltageRow('L3-N Voltage',v.mains_voltage_l3,v.voltage_l3)}
      ${voltageRow('L1-L2 Voltage',v.mains_voltage_l1_l2,v.voltage_l1_l2)}
    </section>
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

  $('#cards').innerHTML=gs.length?gs.map(industrialCard).join(''):'<p class="note">Nenhum gerador cadastrado. Use “Adicionar gerador”.</p>';

  $('#generatorRows').innerHTML=gs.map(g=>`
    <tr>
      <td><b>${g.code}</b></td>
      <td>${g.customer||'-'}<br><small>${g.name}</small></td>
      <td>${g.controller_type}<br><small>${g.controller_model||'-'}</small></td>
      <td>${g.listen_port}<br><small>Unit ${g.modbus_unit}</small></td>
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
  $('#drawer').classList.remove('hidden');
  $('#drawerContent').innerHTML=`
    <div class="detail-head">
      <small>${g.code}</small><h2>${g.name}</h2>${badge(g)}
      <p class="note">${g.customer||''} ${g.site?'· '+g.site:''}<br>${g.controller_type} ${g.controller_model||''}<br>TCP <b>${g.listen_port}</b> · Modbus ID ${g.modbus_unit}</p>
    </div>
    <div class="detail-grid">${Object.entries(g.values||{}).map(([k,v])=>`<div class="detail-metric"><small>${niceKey(k)}</small><b>${formatMetric(k,v)}</b></div>`).join('')||'<p class="note">Aguardando dados da controladora.</p>'}</div>
    ${g.status==='fault'?`<p class="error">Comunicação: ${g.last_error||'falha de leitura'}</p>`:''}`;
}
function closeDrawer(){$('#drawer').classList.add('hidden')}
function closeModal(){$('#modal').classList.add('hidden');$('#formError').textContent=''}

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
      items.forEach(m=>{const o=document.createElement('option');o.value=m.model;o.textContent=m.model;group.appendChild(o)});
      sel.appendChild(group);
    });
  }catch(e){sel.innerHTML='<option value="">Erro ao carregar modelos</option>'}
}

$('#controllerType').onchange=loadControllerModels;
$('#addBtn').onclick=async()=>{$('#modal').classList.remove('hidden');await loadControllerModels()};

$('#generatorForm').onsubmit=async e=>{
  e.preventDefault();
  $('#formError').textContent='';
  const fd=new FormData(e.target);
  const data=Object.fromEntries(fd.entries());
  if(!data.listen_port)delete data.listen_port;
  data.modbus_unit=Number(data.modbus_unit||1);
  const r=await fetch('/api/generators',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const obj=await r.json();
  if(!r.ok){$('#formError').textContent=obj.error||'Erro ao cadastrar';return}
  e.target.reset();closeModal();await loadControllerModels();await refresh();
};

document.querySelectorAll('.nav').forEach(b=>b.onclick=async()=>{
  document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));
  $('#'+b.dataset.view).classList.remove('hidden');
  $('#title').textContent=b.textContent;
  if(b.dataset.view==='events')await refreshEvents();
});

loadControllerModels();
refresh();
setInterval(refresh,3000);
