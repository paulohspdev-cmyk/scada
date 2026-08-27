#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/var/lib/rc-scada/rapid-stage1"
CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
TPL="/opt/scada/ScadaComm/Config/DrvModbus_RC_IG200.xml"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

systemctl stop rc-scada-rapid-bridge 2>/dev/null || true

if [[ -f "$STATE_DIR/last_backup" ]]; then
  BACKUP_DIR="$(cat "$STATE_DIR/last_backup")"
  if [[ -f "$BACKUP_DIR/ScadaCommConfig.xml" ]]; then
    cp -a "$BACKUP_DIR/ScadaCommConfig.xml" "$CFG"
    echo "Configuracao Rapid restaurada de $BACKUP_DIR"
  fi
  if [[ -f "$BACKUP_DIR/DrvModbus_RC_IG200.xml" ]]; then
    cp -a "$BACKUP_DIR/DrvModbus_RC_IG200.xml" "$TPL"
  else
    rm -f "$TPL"
  fi
else
  echo "Aviso: backup da preparacao nao encontrado; configuracao Rapid nao foi alterada pelo rollback."
fi

systemctl restart scadacomm6 2>/dev/null || true
systemctl restart rc-scada-gateway
sleep 4

echo
echo "== Rollback concluido =="
systemctl --no-pager --full status rc-scada-gateway scadacomm6 2>/dev/null || true
ss -lntp 2>/dev/null | grep -E ':(15001|25001)\b' || true
