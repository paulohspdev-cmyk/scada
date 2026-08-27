#!/usr/bin/env bash
set -euo pipefail

CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
TPL_SRC="/opt/rc-scada/rapid/templates/DrvModbus_RC_IG200.xml"
TPL_DST="/opt/scada/ScadaComm/Config/DrvModbus_RC_IG200.xml"
STATE_DIR="/var/lib/rc-scada/rapid-stage1"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${STATE_DIR}/backup-${STAMP}"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

[[ -f "$CFG" ]] || { echo "ERRO: $CFG nao encontrado"; exit 2; }
[[ -f "$TPL_SRC" ]] || { echo "ERRO: $TPL_SRC nao encontrado. Rode git pull."; exit 2; }

mkdir -p "$BACKUP_DIR"
cp -a "$CFG" "$BACKUP_DIR/ScadaCommConfig.xml"
if [[ -f "$TPL_DST" ]]; then
  cp -a "$TPL_DST" "$BACKUP_DIR/DrvModbus_RC_IG200.xml"
fi
printf '%s\n' "$BACKUP_DIR" >"$STATE_DIR/last_backup"

install -m 0644 "$TPL_SRC" "$TPL_DST"

python3 - "$CFG" <<'PY'
import sys
import xml.etree.ElementTree as ET

cfg = sys.argv[1]
tree = ET.parse(cfg)
root = tree.getroot()
lines = root.find("Lines")
if lines is None:
    lines = ET.SubElement(root, "Lines")

# Idempotente: remove somente nossa linha de teste anterior.
for line in list(lines):
    if line.tag == "Line" and (line.get("number") == "100" or line.get("name") == "RC Geradores - IG200 Unit 2"):
        lines.remove(line)

line = ET.SubElement(lines, "Line", {
    "active": "true",
    "isBound": "false",
    "number": "100",
    "name": "RC Geradores - IG200 Unit 2",
})
opts = ET.SubElement(line, "LineOptions")
for tag, value in [
    ("ReqRetries", "1"),
    ("CycleDelay", "200"),
    ("CmdEnabled", "false"),
    ("PollAfterCmd", "false"),
    ("DetailedLog", "true"),
]:
    ET.SubElement(opts, tag).text = value

channel = ET.SubElement(line, "Channel", {"type": "TcpClient", "driver": "DrvCnlBasic"})
for name, value in [
    ("Host", "127.0.0.1"),
    ("TcpPort", "25001"),
    ("ReconnectAfter", "2"),
    ("StayConnected", "true"),
    ("DisconnectOnError", "false"),
    ("Behavior", "Master"),
    ("ConnectionMode", "Shared"),
]:
    ET.SubElement(channel, "Option", {"name": name, "value": value})

custom = ET.SubElement(line, "CustomOptions")
ET.SubElement(custom, "Option", {"name": "TransMode", "value": "TCP"})

devpoll = ET.SubElement(line, "DevicePolling")
ET.SubElement(devpoll, "Device", {
    "active": "true",
    "isBound": "false",
    "number": "200",
    "name": "InteliGen 200",
    "driver": "DrvModbus",
    "numAddress": "2",
    "strAddress": "",
    "pollOnCmd": "false",
    "timeout": "2500",
    "delay": "1000",
    "time": "00:00:00",
    "period": "00:00:00",
    "cmdLine": "DrvModbus_RC_IG200.xml",
})

ET.indent(tree, space="  ")
tree.write(cfg, encoding="utf-8", xml_declaration=True)
PY

# Valida XML antes de qualquer reinicio.
python3 - <<'PY'
import xml.etree.ElementTree as ET
ET.parse('/opt/scada/ScadaComm/Config/ScadaCommConfig.xml')
ET.parse('/opt/scada/ScadaComm/Config/DrvModbus_RC_IG200.xml')
print('XML OK')
PY

echo
echo "Preparacao concluida. NENHUM servico foi reiniciado."
echo "Backup: $BACKUP_DIR"
echo "Linha preparada: Rapid SCADA -> 127.0.0.1:25001 -> Unit ID 2"
echo "Template: $TPL_DST"
echo
echo "Proximo passo, somente quando solicitado: rapid_stage1_cutover.sh"
