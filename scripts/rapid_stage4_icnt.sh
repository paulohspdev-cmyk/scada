#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/rc-scada"
DAT="/opt/scada/BaseDAT"
CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
TOOL="$BASE/scripts/rapid_dat.py"
PROBE_SRC="$BASE/rapid/templates/DrvModbus_RC_ICNT_PROBE.xml"
FULL_SRC="$BASE/rapid/templates/DrvModbus_RC_ICNT.xml"
PROBE_DST="/opt/scada/ScadaComm/Config/DrvModbus_RC_ICNT_PROBE.xml"
FULL_DST="/opt/scada/ScadaComm/Config/DrvModbus_RC_ICNT.xml"
REPO_BINDINGS="$BASE/rapid/bindings.json"
RUNTIME_BINDINGS="/var/lib/rc-scada/rapid-bindings.json"
READER="$BASE/.rapid-reader/RcRapidReader.dll"
STATE_DIR="/var/lib/rc-scada/rapid-stage4"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$STATE_DIR/backup-$STAMP"
LINE_INFO="/var/log/scada/ScadaComm/Log/line100.txt"
LINE_LOG="/var/log/scada/ScadaComm/Log/line100.log"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

for f in "$CFG" "$TOOL" "$PROBE_SRC" "$FULL_SRC" "$REPO_BINDINGS" "$READER" \
         "$DAT/device.dat" "$DAT/cnl.dat"; do
  [[ -f "$f" ]] || { echo "ERRO: arquivo ausente: $f"; exit 2; }
done

for svc in scadaserver6 scadacomm6 rc-scada-rapid-bridge; do
  systemctl is-active --quiet "$svc" || { echo "ERRO: $svc não está ativo"; exit 3; }
done

mkdir -p "$BACKUP_DIR"
cp -a "$CFG" "$DAT/device.dat" "$DAT/cnl.dat" "$BACKUP_DIR/"
if [[ -f "$RUNTIME_BINDINGS" ]]; then
  cp -a "$RUNTIME_BINDINGS" "$BACKUP_DIR/rapid-bindings.json"
  touch "$BACKUP_DIR/had-runtime-bindings"
fi
if [[ -f "$PROBE_DST" ]]; then cp -a "$PROBE_DST" "$BACKUP_DIR/DrvModbus_RC_ICNT_PROBE.xml"; fi
if [[ -f "$FULL_DST" ]]; then cp -a "$FULL_DST" "$BACKUP_DIR/DrvModbus_RC_ICNT.xml"; fi
printf '%s\n' "$BACKUP_DIR" >"$STATE_DIR/last_backup"

restore_templates() {
  if [[ -f "$BACKUP_DIR/DrvModbus_RC_ICNT_PROBE.xml" ]]; then
    cp -a "$BACKUP_DIR/DrvModbus_RC_ICNT_PROBE.xml" "$PROBE_DST"
  else
    rm -f "$PROBE_DST"
  fi
  if [[ -f "$BACKUP_DIR/DrvModbus_RC_ICNT.xml" ]]; then
    cp -a "$BACKUP_DIR/DrvModbus_RC_ICNT.xml" "$FULL_DST"
  else
    rm -f "$FULL_DST"
  fi
}

restore_runtime_bindings() {
  if [[ -f "$BACKUP_DIR/had-runtime-bindings" ]]; then
    cp -a "$BACKUP_DIR/rapid-bindings.json" "$RUNTIME_BINDINGS"
  else
    rm -f "$RUNTIME_BINDINGS"
  fi
}

rollback_full() {
  rc=$?
  trap - ERR
  echo
  echo "ERRO na etapa InteliCompact. Restaurando IG200 estável automaticamente..."
  systemctl stop scadacomm6 2>/dev/null || true
  systemctl stop scadaserver6 2>/dev/null || true
  cp -a "$BACKUP_DIR/device.dat" "$DAT/device.dat"
  cp -a "$BACKUP_DIR/cnl.dat" "$DAT/cnl.dat"
  cp -a "$BACKUP_DIR/ScadaCommConfig.xml" "$CFG"
  restore_templates
  restore_runtime_bindings
  systemctl start scadaserver6 || true
  sleep 2
  systemctl start scadacomm6 || true
  systemctl restart rc-scada-web 2>/dev/null || true
  echo "Rollback concluído. A InteliGen 200 foi preservada."
  echo "Backup: $BACKUP_DIR"
  exit "$rc"
}

echo "== Etapa 4: InteliCompact NT / Unit 1 =="
echo "Backup: $BACKUP_DIR"
echo
echo "1) Atualizando a ponte compartilhada sem permitir escritas..."
systemctl restart rc-scada-rapid-bridge

# Aguarda o modem restabelecer a sessão física.
CONNECTED=0
for _ in $(seq 1 15); do
  if journalctl -u rc-scada-rapid-bridge --since '-30 sec' --no-pager 2>/dev/null | grep -q 'modem conectado'; then
    CONNECTED=1
    break
  fi
  sleep 1
done
if [[ "$CONNECTED" != "1" ]]; then
  echo "ERRO: modem não reconectou à ponte após o restart"
  systemctl restart scadacomm6 || true
  exit 4
fi

echo
echo "2) Probe somente leitura: Unit 1 / FC03 / endereço 57..."
install -m 0644 "$PROBE_SRC" "$PROBE_DST"

python3 - "$CFG" <<'PY'
import sys
import xml.etree.ElementTree as ET

cfg = sys.argv[1]
tree = ET.parse(cfg)
root = tree.getroot()
lines = root.find("Lines")
if lines is None:
    raise SystemExit("ERRO: <Lines> não encontrado")
line = next((x for x in lines.findall("Line") if x.get("number") == "100"), None)
if line is None:
    raise SystemExit("ERRO: linha 100 não encontrada")
line.set("name", "RC Geradores 15001")
devpoll = line.find("DevicePolling")
if devpoll is None:
    raise SystemExit("ERRO: DevicePolling ausente")
for dev in list(devpoll.findall("Device")):
    if dev.get("number") == "201":
        devpoll.remove(dev)
ET.SubElement(devpoll, "Device", {
    "active": "true",
    "isBound": "false",
    "number": "201",
    "name": "InteliCompact NT",
    "driver": "DrvModbus",
    "numAddress": "1",
    "strAddress": "",
    "pollOnCmd": "false",
    "timeout": "2500",
    "delay": "500",
    "time": "00:00:00",
    "period": "00:00:00",
    "cmdLine": "DrvModbus_RC_ICNT_PROBE.xml",
})
ET.indent(tree, space="  ")
tree.write(cfg, encoding="utf-8", xml_declaration=True)
PY

python3 - <<'PY'
import xml.etree.ElementTree as ET
ET.parse('/opt/scada/ScadaComm/Config/ScadaCommConfig.xml')
ET.parse('/opt/scada/ScadaComm/Config/DrvModbus_RC_ICNT_PROBE.xml')
print('XML probe OK')
PY

systemctl restart scadacomm6
sleep 14

echo
echo "== Resultado do probe =="
cat "$LINE_INFO" 2>/dev/null || true

echo
echo "== Últimas mensagens da linha =="
tail -n 100 "$LINE_LOG" 2>/dev/null || true

if ! grep -Eq '\[201\][[:space:]]+InteliCompact NT[[:space:]]*:[[:space:]]*Normal' "$LINE_INFO" 2>/dev/null; then
  echo
  echo "PROBE NÃO CONFIRMOU UNIT 1. Não vou cadastrar pontos incorretos no Rapid SCADA."
  echo "Restaurando apenas a configuração anterior; IG200 permanece ativa."
  cp -a "$BACKUP_DIR/ScadaCommConfig.xml" "$CFG"
  restore_templates
  systemctl restart scadacomm6 || true
  echo
echo "== Ponte =="
  journalctl -u rc-scada-rapid-bridge --since '-3 min' --no-pager | tail -n 100 || true
  echo
  echo "Backup: $BACKUP_DIR"
  exit 10
fi

echo
echo "PROBE OK: Rapid SCADA recebeu resposta válida da InteliCompact NT no Unit ID 1."
echo "3) Vinculando os 6 pontos somente leitura ao Rapid SCADA Server..."

trap rollback_full ERR
systemctl stop scadacomm6
systemctl stop scadaserver6

python3 "$TOOL" append "$DAT/device.dat" DeviceNum \
  '{"DeviceNum":201,"Name":"InteliCompact NT","Code":"ICNT","DevTypeID":null,"NumAddress":1,"StrAddress":"","CommLineNum":100,"Descr":"ComAp InteliCompact NT - Modbus Unit 1"}'

python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2101,"Active":true,"Name":"ICNT Tensao Bateria x10","Code":"icnt_battery_voltage_raw","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":201,"TagNum":null,"TagCode":"battery_voltage_raw","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2102,"Active":true,"Name":"ICNT Pressao Oleo x10","Code":"icnt_oil_pressure_raw","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":201,"TagNum":null,"TagCode":"oil_pressure_raw","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2103,"Active":true,"Name":"ICNT Temperatura Motor","Code":"icnt_coolant_temperature","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":201,"TagNum":null,"TagCode":"coolant_temperature","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2104,"Active":true,"Name":"ICNT Nivel Combustivel","Code":"icnt_fuel_level","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":201,"TagNum":null,"TagCode":"fuel_level","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2105,"Active":true,"Name":"ICNT Entradas Digitais","Code":"icnt_binary_inputs_raw","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":201,"TagNum":null,"TagCode":"binary_inputs_raw","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2106,"Active":true,"Name":"ICNT Modo Controladora","Code":"icnt_controller_mode_raw","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":201,"TagNum":null,"TagCode":"controller_mode_raw","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'

install -m 0644 "$FULL_SRC" "$FULL_DST"

python3 - "$CFG" <<'PY'
import sys
import xml.etree.ElementTree as ET
cfg=sys.argv[1]
tree=ET.parse(cfg)
root=tree.getroot()
lines=root.find('Lines')
line=next((x for x in lines.findall('Line') if x.get('number')=='100'),None)
if line is None: raise SystemExit('ERRO: linha 100 ausente')
line.set('name','RC Geradores 15001')
line.set('isBound','true')
dev=next((x for x in line.find('DevicePolling').findall('Device') if x.get('number')=='201'),None)
if dev is None: raise SystemExit('ERRO: dispositivo 201 ausente')
dev.set('isBound','true')
dev.set('cmdLine','DrvModbus_RC_ICNT.xml')
ET.indent(tree,space='  ')
tree.write(cfg,encoding='utf-8',xml_declaration=True)
PY

mkdir -p "$(dirname "$RUNTIME_BINDINGS")"
python3 - "$REPO_BINDINGS" "$RUNTIME_BINDINGS" <<'PY'
import json,sys
src,dst=sys.argv[1:3]
data=json.load(open(src,encoding='utf-8'))
data=[x for x in data if not (
    str(x.get('controller_type','')).upper()=='COMAP' and
    str(x.get('controller_model','')).strip().lower()=='intelicompact nt' and
    int(x.get('listen_port') or 0)==15001 and int(x.get('modbus_unit') or 0)==1
)]
data.append({
  'controller_type':'COMAP',
  'controller_model':'InteliCompact NT',
  'listen_port':15001,
  'modbus_unit':1,
  'rapid_device_num':201,
  'channels':{
    'battery_voltage':{'cnl':2101,'scale':0.1},
    'oil_pressure':{'cnl':2102,'scale':0.1},
    'coolant_temperature':{'cnl':2103,'scale':1.0},
    'fuel_level':{'cnl':2104,'scale':1.0},
    'binary_inputs_raw':{'cnl':2105,'scale':1.0},
    'controller_mode_raw':{'cnl':2106,'scale':1.0}
  }
})
with open(dst,'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
    f.write('\n')
print('Bindings runtime OK:',dst)
PY

python3 "$TOOL" check "$DAT/device.dat" "$DAT/cnl.dat"
python3 - <<'PY'
import xml.etree.ElementTree as ET
ET.parse('/opt/scada/ScadaComm/Config/ScadaCommConfig.xml')
ET.parse('/opt/scada/ScadaComm/Config/DrvModbus_RC_ICNT.xml')
print('XML final OK')
PY

systemctl start scadaserver6
sleep 3
systemctl start scadacomm6
sleep 20

[[ -f "$LINE_INFO" ]] || { echo "ERRO: line100.txt ausente"; false; }
grep -Eq '\[200\][[:space:]]+InteliGen 200[[:space:]]*:[[:space:]]*Normal' "$LINE_INFO" || { echo "ERRO: IG200 deixou de estar Normal"; cat "$LINE_INFO"; false; }
grep -Eq '\[201\][[:space:]]+InteliCompact NT[[:space:]]*:[[:space:]]*Normal' "$LINE_INFO" || { echo "ERRO: ICNT não ficou Normal com o mapa completo"; cat "$LINE_INFO"; false; }

echo
echo "== Canais ICNT diretamente do Rapid SCADA Server =="
RESULT="$(dotnet "$READER" "$CFG" 2101 2102 2103 2104 2105 2106)"
printf '%s\n' "$RESULT" | python3 -m json.tool
printf '%s' "$RESULT" | python3 -c '
import json,sys
p=json.load(sys.stdin)
chs=p.get("channels",[])
if not p.get("ok") or len(chs)!=6:
    raise SystemExit("ERRO: resposta incompleta do Rapid SCADA para ICNT")
undef=[x.get("cnl") for x in chs if int(x.get("stat",0))<=0]
if undef:
    raise SystemExit("ERRO: canais ICNT indefinidos: "+",".join(map(str,undef)))
print("OK: 6 canais ICNT definidos no Rapid SCADA Server")
'

systemctl restart rc-scada-web
sleep 5
trap - ERR

echo
echo "== Linha compartilhada final =="
cat "$LINE_INFO" || true

echo
echo "== API Geradores =="
curl -fsS http://127.0.0.1:8088/api/generators | python3 -m json.tool

echo
echo "== Dashboard =="
curl -fsS http://127.0.0.1:8088/api/dashboard | python3 -m json.tool

echo
echo "ETAPA 4 CONCLUÍDA"
echo "15001 compartilhada pelo Rapid SCADA"
echo "Unit 1: InteliCompact NT / Device 201 / canais 2101..2106"
echo "Unit 2: InteliGen 200 / Device 200 / canais 2001..2008"
echo "Bridge: somente leitura FC03/FC04"
echo "Backup: $BACKUP_DIR"
