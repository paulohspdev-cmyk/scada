#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/rc-scada"
UNIT_SRC="$BASE/systemd/rc-scada-rapid-bridge.service"
UNIT_DST="/etc/systemd/system/rc-scada-rapid-bridge.service"
CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
TPL="/opt/scada/ScadaComm/Config/DrvModbus_RC_IG200.xml"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

[[ -f "$CFG" ]] || { echo "ERRO: configuracao Rapid SCADA ausente"; exit 2; }
[[ -f "$TPL" ]] || { echo "ERRO: template IG200 ausente. Rode rapid_stage1_prepare.sh"; exit 2; }
[[ -f "$UNIT_SRC" ]] || { echo "ERRO: unit da ponte ausente. Rode git pull."; exit 2; }

grep -q 'RC Geradores - IG200 Unit 2' "$CFG" || {
  echo "ERRO: linha de teste nao esta preparada. Rode rapid_stage1_prepare.sh"; exit 2;
}

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload

echo "== Corte controlado =="
echo "1) Parando polling Python antigo..."
systemctl stop rc-scada-gateway

echo "2) Iniciando ponte reversa para Rapid SCADA..."
systemctl restart rc-scada-rapid-bridge
sleep 2

if ! systemctl is-active --quiet rc-scada-rapid-bridge; then
  echo "ERRO: ponte nao iniciou. Restaurando gateway antigo."
  systemctl restart rc-scada-gateway
  systemctl --no-pager --full status rc-scada-rapid-bridge rc-scada-gateway || true
  exit 3
fi

echo "3) Reiniciando somente o Communicator Rapid SCADA..."
systemctl restart scadacomm6
sleep 12

echo
echo "== Servicos =="
systemctl --no-pager --full status rc-scada-rapid-bridge scadacomm6 2>/dev/null || true

echo
echo "== Portas esperadas =="
ss -lntp 2>/dev/null | grep -E ':(15001|25001)\b' || true

echo
echo "== Ultimas mensagens da ponte =="
journalctl -u rc-scada-rapid-bridge --since '-2 min' --no-pager 2>/dev/null | tail -n 80 || true

echo
echo "== Ultimas mensagens do Communicator =="
journalctl -u scadacomm6 --since '-2 min' --no-pager 2>/dev/null | tail -n 80 || true

echo
echo "== Logs de linha Rapid SCADA candidatos =="
find /opt/scada /var/log -type f \( -iname 'Line100*.log' -o -iname 'Line100*.txt' -o -iname '*line*100*' \) \
  -mmin -10 -print 2>/dev/null | head -n 20 || true

echo
echo "Corte de teste concluido."
echo "NAO habilitamos a ponte no boot ainda. Primeiro vamos validar a leitura da IG200."
