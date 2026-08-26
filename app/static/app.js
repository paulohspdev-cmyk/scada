const $=s=>document.querySelector(s);
let generators=[];
function badge(g){if(g.connected&&g.poll_ok)return '<span class="badge online">ONLINE</span>';if(g.connected)return '<span class="badge connected">CONECTADO</span>';return '<span class="badge offline">OFFLINE</span>'}
function niceKey(k){return k.replaceAll('_',' ').replace(/\b\w/g,m=>m.toUpperCase())}
function metricEntries(g,n=4){return Object.entries(g.values||{}).slice(0,n).map(([k,v])=>`<div class="metric"><span>${niceKey(k)}</span><b>${v}</b></div>`).join('')}
async function refresh(){
  const [gs,ds]=await Promise.all([fetch('/api/generators').then(r=>r.json()),fetch('/api/dashboard').then(r=>r.json())]);
  generators=gs;
  $('#kTotal').textContent=ds.total;$('#kOnline').textContent=ds.online;$('#kOffline').textContent=ds.offline;$('#kOperating').textContent=ds.operating;$('#kAlarm').textContent=ds.alarm;
  $('#cards').innerHTML=gs.length?gs.map(g=>`<div class="card" onclick="showGenerator(${g.id})"><div class="card-top"><span class="code">${g.code}</span>${badge(g)}</div><div class="name">${g.name}</div><div class="meta">${g.customer||'Sem cliente'} · ${g.controller_type} ${g.controller_model||''} · TCP ${g.listen_port}</div><div class="telemetry">${metricEntries(g)}</div></div>`).join(''):'<p class="note">Nenhum gerador cadastrado. Use “Adicionar gerador”.</p>';
  $('#generatorRows').innerHTML=gs.map(g=>`<tr><td><b>${g.code}</b></td><td>${g.customer||'-'}<br><small>${g.name}</small></td><td>${g.controller_type}<br><small>${g.controller_model||'-'}</small></td><td>${g.listen_port}</td><td>${badge(g)}</td><td><button class="link" onclick="showGenerator(${g.id})">Abrir</button></td></tr>`).join('');
}
async function refreshEvents(){const es=await fetch('/api/events').then(r=>r.json());$('#eventsList').innerHTML=es.map(e=>`<div class="event"><b>${e.code||'Sistema'} · ${e.level}</b><div>${e.message}</div><small>${new Date(e.created_at*1000).toLocaleString()}</small></div>`).join('')||'<p class="note">Sem eventos.</p>'}
function showGenerator(id){const g=generators.find(x=>x.id===id);if(!g)return;$('#drawer').classList.remove('hidden');$('#drawerContent').innerHTML=`<div class="detail-head"><small>${g.code}</small><h2>${g.name}</h2>${badge(g)}<p class="note">${g.customer||''} ${g.site?'· '+g.site:''}<br>${g.controller_type} ${g.controller_model||''}<br>Modem TCP Client → servidor porta <b>${g.listen_port}</b> · Unit ID ${g.modbus_unit}</p></div><div class="detail-grid">${Object.entries(g.values||{}).map(([k,v])=>`<div class="detail-metric"><small>${niceKey(k)}</small><b>${v}</b></div>`).join('')||'<p class="note">Aguardando telemetria.</p>'}</div><p class="note">Peer: ${g.peer||'-'}<br>Último erro: ${g.last_error||'-'}</p>`}
function closeDrawer(){$('#drawer').classList.add('hidden')}
function closeModal(){$('#modal').classList.add('hidden');$('#formError').textContent=''}
$('#addBtn').onclick=()=>$('#modal').classList.remove('hidden');
$('#generatorForm').onsubmit=async e=>{e.preventDefault();const fd=new FormData(e.target),data=Object.fromEntries(fd.entries());if(!data.listen_port)delete data.listen_port;data.modbus_unit=Number(data.modbus_unit||1);const r=await fetch('/api/generators',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){const x=await r.json();$('#formError').textContent=x.error||'Erro ao cadastrar';return}e.target.reset();closeModal();await refresh()};
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>{document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));$('#'+b.dataset.view).classList.remove('hidden');$('#title').textContent=b.textContent;if(b.dataset.view==='events')refreshEvents()});
refresh();setInterval(refresh,3000);
