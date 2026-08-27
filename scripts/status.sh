#!/usr/bin/env bash
set -e

echo "== RC Geradores =="
systemctl --no-pager --full status rc-scada-web rc-scada-rapid-bridge 2>/dev/null || true

echo
echo "== Rapid SCADA =="
systemctl --no-pager --full status scadaagent6 scadaserver6 scadacomm6 scadaweb6 2>/dev/null || true

echo
echo "== Portas geradores / ponte local / web =="
ss -lntp | grep -E ':(15[0-9]{3}|25[0-9]{3}|8088|10000|10008)\b' || true

echo
echo "== Linha RC Rapid SCADA =="
if [[ -f /var/log/scada/ScadaComm/Log/line100.txt ]]; then
  cat /var/log/scada/ScadaComm/Log/line100.txt
else
  echo "line100.txt ainda nao existe"
fi

echo
echo "== Controle remoto restrito =="
if [[ -S /run/rc-scada/control.sock ]]; then
  ls -l /run/rc-scada/control.sock
  echo "socket de controle ativo"
else
  echo "socket de controle nao ativo (normal se controle opt-in nao foi instalado)"
fi

echo
echo "== Legado =="
if systemctl list-unit-files rc-scada-gateway.service --no-legend 2>/dev/null | grep -q rc-scada-gateway; then
  if systemctl is-active --quiet rc-scada-gateway.service; then
    echo "ATENCAO: rc-scada-gateway legado esta ATIVO; arquitetura atual exige que fique parado."
  else
    echo "rc-scada-gateway legado presente, mas inativo."
  fi
else
  echo "rc-scada-gateway legado nao instalado."
fi
