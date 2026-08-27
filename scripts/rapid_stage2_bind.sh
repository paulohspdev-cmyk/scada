#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/rc-scada"
DAT="/opt/scada/BaseDAT"
CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
TOOL="$BASE/scripts/rapid_dat.py"
STATE_DIR="/var/lib/rc-scada/rapid-stage2"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$STATE_DIR/backup-$STAMP"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

for f in "$DAT/commline.dat" "$DAT/device.dat" "$DAT/cnl.dat" "$CFG" "$TOOL"; do
  [[ -f "$f" ]] || { echo "ERRO: arquivo ausente: $f"; exit 2; }
done

mkdir -p "$BACKUP_DIR"
cp -a "$DAT/commline.dat" "$DAT/device.dat" "$DAT/cnl.dat" "$CFG" "$BACKUP_DIR/"
printf '%s\n' "$BACKUP_DIR" >"$STATE_DIR/last_backup"

echo "== Validando BaseDAT existente =="
python3 "$TOOL" check "$DAT/commline.dat" "$DAT/device.dat" "$DAT/cnl.dat"

echo
echo "Backup: $BACKUP_DIR"
echo "Parando somente Server e Communicator para atualizar a base..."
systemctl stop scadacomm6
systemctl stop scadaserver6

rollback_on_error() {
  rc=$?
  echo
  echo "ERRO durante a vinculação. Restaurando backup automaticamente..."
  cp -a "$BACKUP_DIR/commline.dat" "$DAT/commline.dat"
  cp -a "$BACKUP_DIR/device.dat" "$DAT/device.dat"
  cp -a "$BACKUP_DIR/cnl.dat" "$DAT/cnl.dat"
  cp -a "$BACKUP_DIR/ScadaCommConfig.xml" "$CFG"
  systemctl restart scadaserver6 || true
  systemctl restart scadacomm6 || true
  exit "$rc"
}
trap rollback_on_error ERR

echo
echo "== Criando entidades Rapid SCADA =="
python3 "$TOOL" append "$DAT/commline.dat" CommLineNum \
  '{"CommLineNum":100,"Name":"RC Geradores 15001","Descr":"Reverse TCP bridge 15001 -> 25001"}'

python3 "$TOOL" append "$DAT/device.dat" DeviceNum \
  '{"DeviceNum":200,"Name":"InteliGen 200","Code":"IG200","DevTypeID":null,"NumAddress":2,"StrAddress":"","CommLineNum":100,"Descr":"ComAp InteliGen 200 - Modbus Unit 2"}'

python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2001,"Active":true,"Name":"IG200 RPM","Code":"ig200_rpm","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"rpm","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2002,"Active":true,"Name":"IG200 Tensao L1-N","Code":"ig200_voltage_l1","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"voltage_l1","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2003,"Active":true,"Name":"IG200 Tensao L2-N","Code":"ig200_voltage_l2","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"voltage_l2","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2004,"Active":true,"Name":"IG200 Tensao L3-N","Code":"ig200_voltage_l3","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"voltage_l3","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2005,"Active":true,"Name":"IG200 Tensao L1-L2","Code":"ig200_voltage_l1_l2","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"voltage_l1_l2","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2006,"Active":true,"Name":"IG200 Tensao L2-L3","Code":"ig200_voltage_l2_l3","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"voltage_l2_l3","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2007,"Active":true,"Name":"IG200 Tensao L3-L1","Code":"ig200_voltage_l3_l1","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"voltage_l3_l1","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'
python3 "$TOOL" append "$DAT/cnl.dat" CnlNum \
  '{"CnlNum":2008,"Active":true,"Name":"IG200 Frequencia x100","Code":"ig200_frequency_raw","DataTypeID":null,"DataLen":null,"CnlTypeID":1,"ObjNum":null,"DeviceNum":200,"TagNum":null,"TagCode":"frequency_raw","FormulaEnabled":false,"InFormula":null,"OutFormula":null,"FormatID":null,"OutFormatID":null,"QuantityID":null,"UnitID":null,"LimID":null,"ArchiveMask":null,"EventMask":null}'

echo
echo "== Ativando vínculo da linha e do dispositivo =="
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
    raise SystemExit("ERRO: linha 100 não encontrada; execute rapid_stage1_prepare.sh")
line.set("isBound", "true")

devpoll = line.find("DevicePolling")
if devpoll is None:
    raise SystemExit("ERRO: DevicePolling ausente na linha 100")
dev = next((x for x in devpoll.findall("Device") if x.get("number") == "200"), None)
if dev is None:
    raise SystemExit("ERRO: dispositivo 200 não encontrado")
dev.set("isBound", "true")

ET.indent(tree, space="  ")
tree.write(cfg, encoding="utf-8", xml_declaration=True)
print("XML vinculado: Line 100 / Device 200")
PY

python3 "$TOOL" check "$DAT/commline.dat" "$DAT/device.dat" "$DAT/cnl.dat"
python3 - <<'PY'
import xml.etree.ElementTree as ET
ET.parse('/opt/scada/ScadaComm/Config/ScadaCommConfig.xml')
print('XML OK')
PY

echo
echo "== Subindo Rapid SCADA =="
systemctl start scadaserver6
sleep 3
systemctl start scadacomm6
sleep 12

trap - ERR

echo
echo "== Serviços =="
systemctl --no-pager --full status scadaserver6 scadacomm6 rc-scada-rapid-bridge 2>/dev/null || true

echo
echo "== Linha 100 =="
cat /var/log/scada/ScadaComm/Log/line100.txt 2>/dev/null || true

echo
echo "== Último polling =="
tail -n 80 /var/log/scada/ScadaComm/Log/line100.log 2>/dev/null || true

echo
echo "== Canais gravados no BaseDAT =="
python3 "$TOOL" show "$DAT/cnl.dat" | grep -E '200[1-8]|ig200_|IG200' -C 2 || true

echo
echo "Vinculação concluída. Canais Rapid SCADA: 2001..2008"
echo "Backup para rollback: $BACKUP_DIR"
