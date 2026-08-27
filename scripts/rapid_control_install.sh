#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/rc-scada"
SERVICE_SRC="$BASE/systemd/rc-scada-rapid-bridge.service"
SERVICE_DST="/etc/systemd/system/rc-scada-rapid-bridge.service"
CLI="$BASE/bin/rc-generator"
ENV_FILE="/etc/rc-scada.env"
SOCKET="/run/rc-scada/control.sock"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

for f in "$SERVICE_SRC" "$CLI" "$ENV_FILE"; do
  [[ -f "$f" ]] || { echo "ERRO: arquivo ausente: $f"; exit 2; }
done

systemctl is-active --quiet scadaserver6 || { echo "ERRO: Rapid SCADA Server não está ativo"; exit 3; }
systemctl is-active --quiet scadacomm6 || { echo "ERRO: Rapid SCADA Communicator não está ativo"; exit 3; }

echo "== Instalando controle remoto restrito da InteliGen 200 =="
echo "O TCP do Rapid SCADA continuará bloqueando toda escrita Modbus genérica."
echo "Somente START/STOP do device 200 serão aceitos pelo socket Unix local."

install -m 0644 "$SERVICE_SRC" "$SERVICE_DST"
chmod 0755 "$CLI"

if grep -q '^RC_ENABLE_IG200_CONTROL=' "$ENV_FILE"; then
  sed -i 's/^RC_ENABLE_IG200_CONTROL=.*/RC_ENABLE_IG200_CONTROL=1/' "$ENV_FILE"
else
  printf '\nRC_ENABLE_IG200_CONTROL=1\n' >> "$ENV_FILE"
fi

if grep -q '^RC_RAPID_CONTROL_SOCKET=' "$ENV_FILE"; then
  sed -i 's#^RC_RAPID_CONTROL_SOCKET=.*#RC_RAPID_CONTROL_SOCKET=/run/rc-scada/control.sock#' "$ENV_FILE"
else
  printf 'RC_RAPID_CONTROL_SOCKET=/run/rc-scada/control.sock\n' >> "$ENV_FILE"
fi

systemctl daemon-reload
systemctl restart rc-scada-rapid-bridge

SOCKET_OK=0
for _ in $(seq 1 20); do
  if [[ -S "$SOCKET" ]]; then
    SOCKET_OK=1
    break
  fi
  sleep 1
done
if [[ "$SOCKET_OK" != "1" ]]; then
  echo "ERRO: socket $SOCKET não foi criado"
  systemctl --no-pager --full status rc-scada-rapid-bridge || true
  journalctl -u rc-scada-rapid-bridge --since '-2 min' --no-pager || true
  exit 4
fi

MODEM_OK=0
for _ in $(seq 1 25); do
  if journalctl -u rc-scada-rapid-bridge --since '-45 sec' --no-pager 2>/dev/null | grep -q 'porta 15001: modem conectado'; then
    MODEM_OK=1
    break
  fi
  sleep 1
done
if [[ "$MODEM_OK" != "1" ]]; then
  echo "ERRO: modem da porta 15001 ainda não reconectou após o restart."
  echo "Não execute comando de partida enquanto isso não estiver conectado."
  journalctl -u rc-scada-rapid-bridge --since '-2 min' --no-pager | tail -n 80 || true
  exit 5
fi

# O Communicator deve reconectar sozinho ao listener local. Se não, reinicia
# apenas o Communicator, sem tocar no Server.
LOCAL_OK=0
for _ in $(seq 1 15); do
  if journalctl -u rc-scada-rapid-bridge --since '-45 sec' --no-pager 2>/dev/null | grep -q 'Rapid SCADA conectado'; then
    LOCAL_OK=1
    break
  fi
  sleep 1
done
if [[ "$LOCAL_OK" != "1" ]]; then
  systemctl restart scadacomm6
  sleep 5
fi

echo
echo "== Estado final =="
systemctl is-active rc-scada-rapid-bridge scadacomm6 scadaserver6
ls -l "$SOCKET"
journalctl -u rc-scada-rapid-bridge --since '-90 sec' --no-pager | tail -n 30 || true

echo
echo "CONTROLE INSTALADO. Nenhum comando de máquina foi executado."
echo "Para partida, somente após confirmar que a área/equipamento estão seguros e autorizados:"
echo "  sudo /opt/rc-scada/bin/rc-generator start --device 200 --confirm"
echo
echo "Se a controladora exigir senha de acesso para Engine Cmd:"
echo "  sudo /opt/rc-scada/bin/rc-generator start --device 200 --confirm --ask-password"
