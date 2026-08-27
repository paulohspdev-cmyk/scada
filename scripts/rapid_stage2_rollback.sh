#!/usr/bin/env bash
set -euo pipefail

DAT="/opt/scada/BaseDAT"
CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
STATE_DIR="/var/lib/rc-scada/rapid-stage2"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

[[ -f "$STATE_DIR/last_backup" ]] || { echo "ERRO: backup stage2 não encontrado"; exit 2; }
BACKUP_DIR="$(cat "$STATE_DIR/last_backup")"
for f in commline.dat device.dat cnl.dat ScadaCommConfig.xml; do
  [[ -f "$BACKUP_DIR/$f" ]] || { echo "ERRO: $BACKUP_DIR/$f ausente"; exit 2; }
done

echo "Restaurando: $BACKUP_DIR"
systemctl stop scadacomm6
systemctl stop scadaserver6
cp -a "$BACKUP_DIR/commline.dat" "$DAT/commline.dat"
cp -a "$BACKUP_DIR/device.dat" "$DAT/device.dat"
cp -a "$BACKUP_DIR/cnl.dat" "$DAT/cnl.dat"
cp -a "$BACKUP_DIR/ScadaCommConfig.xml" "$CFG"
systemctl start scadaserver6
sleep 2
systemctl start scadacomm6
sleep 5
systemctl --no-pager --full status scadaserver6 scadacomm6 2>/dev/null || true
echo "Rollback stage2 concluído."
