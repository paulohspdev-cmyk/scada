#!/usr/bin/env bash
set -e
echo "== RC SCADA =="
systemctl --no-pager --full status rc-scada-web rc-scada-gateway 2>/dev/null || true
echo
echo "== Rapid SCADA =="
systemctl --no-pager --full status scadaserver6 scadacomm6 scadaweb6 2>/dev/null || true
echo
echo "== Portas geradores =="
ss -lntp | grep -E ':(150[0-9]{2}|8088)\b' || true
