#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/paulohspdev-cmyk/scada.git"
BASE="/opt/rc-scada"
RAPID_VERSION="6.4.7"
RAPID_URL="https://rapidscada.org/download/rapidscada_${RAPID_VERSION}_linux_en.zip"
TMP="/tmp/rc-scada-install"
ENV_FILE="/etc/rc-scada.env"

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root: sudo bash install.sh"
  exit 1
fi

PREV_CONTROL=0
if [[ -f "$ENV_FILE" ]]; then
  PREV_CONTROL="$(sed -n 's/^RC_ENABLE_IG200_CONTROL=//p' "$ENV_FILE" | tail -n1 || true)"
  [[ "$PREV_CONTROL" == "1" ]] || PREV_CONTROL=0
fi

echo "== RC Geradores SCADA =="
echo "Arquitetura: modem -> RC Reverse Bridge -> Rapid SCADA -> painel RC"
echo
echo "Instalando dependencias..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl unzip nginx python3 python3-venv python3-pip ca-certificates jq openssl sudo \
  dotnet-sdk-8.0

if ! command -v dotnet >/dev/null 2>&1; then
  echo "ERRO: .NET 8 nao foi instalado."
  exit 2
fi

echo
echo "Baixando/atualizando nosso sistema..."
if [[ -d "$BASE/.git" ]]; then
  git -C "$BASE" fetch origin main
  git -C "$BASE" pull --ff-only origin main
else
  rm -rf "$BASE"
  git clone "$REPO" "$BASE"
fi

if ! id rcscada >/dev/null 2>&1; then
  useradd --system --home "$BASE" --shell /usr/sbin/nologin rcscada
fi

chmod +x "$BASE/install.sh"
find "$BASE/scripts" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} \;
chmod +x "$BASE/bin/rc-generator" 2>/dev/null || true

echo
echo "Instalando Rapid SCADA Community ${RAPID_VERSION}..."
rm -rf "$TMP"
mkdir -p "$TMP"
curl -fL "$RAPID_URL" -o "$TMP/rapidscada.zip"
unzip -q "$TMP/rapidscada.zip" -d "$TMP/pkg"
DEB="$(find "$TMP/pkg" -type f -name 'rapidscada_*_all.deb' | head -n1 || true)"

if [[ -n "$DEB" ]]; then
  dpkg -i "$DEB" || { apt-get -f install -y; dpkg -i "$DEB"; }
else
  SCADA_DIR="$(find "$TMP/pkg" -type d -name scada | head -n1 || true)"
  DAEMONS_DIR="$(find "$TMP/pkg" -type d -name daemons | head -n1 || true)"
  [[ -n "$SCADA_DIR" && -n "$DAEMONS_DIR" ]] || {
    echo "ERRO: pacote Rapid SCADA com estrutura inesperada."
    exit 3
  }
  mkdir -p /opt/scada
  cp -a "$SCADA_DIR"/. /opt/scada/
  chmod +x /opt/scada/make_executable.sh
  /opt/scada/make_executable.sh
  cp -a "$DAEMONS_DIR"/. /etc/systemd/system/
fi

echo
echo "Preparando aplicacao RC..."
python3 -m venv "$BASE/.venv"
"$BASE/.venv/bin/pip" install --upgrade pip
"$BASE/.venv/bin/pip" install -r "$BASE/requirements.txt"
mkdir -p /var/lib/rc-scada /var/log/rc-scada
chown -R rcscada:rcscada /var/lib/rc-scada /var/log/rc-scada
chown -R rcscada:rcscada "$BASE"

cat >"$ENV_FILE" <<EOF
RC_DB_PATH=/var/lib/rc-scada/scada.db
RC_BIND=127.0.0.1
RC_WEB_PORT=8088
RC_RAPID_REMOTE_BIND=0.0.0.0
RC_RAPID_LOCAL_BIND=127.0.0.1
RC_RAPID_LOCAL_OFFSET=10000
RC_RAPID_BRIDGE_TIMEOUT=4
RC_RAPID_RECONCILE_SECONDS=5
RC_RAPID_CONTROL_SOCKET=/run/rc-scada/control.sock
RC_ENABLE_IG200_CONTROL=${PREV_CONTROL}
EOF
chmod 640 "$ENV_FILE"
chown root:rcscada "$ENV_FILE"

echo
echo "Compilando cliente oficial do Rapid SCADA Server..."
SCADA_COMMON="$(find /opt/scada -type f -name ScadaCommon.dll -print -quit)"
if [[ -n "$SCADA_COMMON" && -f "$SCADA_COMMON" ]]; then
  OUT="$BASE/.rapid-reader"
  rm -rf "$OUT"
  mkdir -p "$OUT"
  dotnet build "$BASE/rapid/reader/RcRapidReader.csproj" \
    -c Release -o "$OUT" -p:ScadaCommonPath="$SCADA_COMMON" --nologo
  SCADA_DLL_DIR="$(dirname "$SCADA_COMMON")"
  find "$SCADA_DLL_DIR" -maxdepth 1 -type f -name 'Scada*.dll' \
    -exec cp --update=none {} "$OUT/" \; 2>/dev/null || true
  chown -R rcscada:rcscada "$OUT"
else
  echo "AVISO: ScadaCommon.dll nao encontrado; leitor do Server nao foi compilado."
fi

echo
echo "Instalando servicos atuais..."
cp "$BASE/systemd/rc-scada-web.service" /etc/systemd/system/
cp "$BASE/systemd/rc-scada-rapid-bridge.service" /etc/systemd/system/
systemctl daemon-reload

# O gateway Python antigo nao pertence mais a arquitetura oficial.
systemctl disable --now rc-scada-gateway.service 2>/dev/null || true
rm -f /etc/systemd/system/rc-scada-gateway.service
systemctl daemon-reload

sudo -u rcscada env RC_DB_PATH=/var/lib/rc-scada/scada.db \
  PYTHONPATH="$BASE" "$BASE/.venv/bin/python" "$BASE/scripts/init_db.py"

echo
echo "Configurando Nginx..."
cp "$BASE/nginx/rc-scada.conf" /etc/nginx/sites-available/rc-scada
ln -sfn /etc/nginx/sites-available/rc-scada /etc/nginx/sites-enabled/rc-scada
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx

echo
echo "Ativando Rapid SCADA..."
for svc in scadaagent6.service scadaserver6.service scadacomm6.service scadaweb6.service; do
  if [[ -f "/etc/systemd/system/$svc" ]] || \
     systemctl list-unit-files "$svc" --no-legend 2>/dev/null | grep -q "$svc"; then
    systemctl enable "$svc" || true
    systemctl restart "$svc" || true
  fi
done

echo
echo "Ativando painel e RC Reverse Bridge..."
systemctl enable --now rc-scada-web.service rc-scada-rapid-bridge.service

IP="$(hostname -I | awk '{print $1}')"
echo
echo "============================================================"
echo " RC GERADORES INSTALADO"
echo "============================================================"
echo " Interface:  http://${IP:-IP_DA_VM}/"
echo " Banco RC:   /var/lib/rc-scada/scada.db"
echo " Rapid:      /opt/scada"
echo " Bridge:     rc-scada-rapid-bridge"
echo
echo " Arquitetura:"
echo "   modem -> bridge -> Rapid SCADA Communicator -> Server -> painel"
echo
echo " Diagnostico:"
echo "   sudo $BASE/scripts/status.sh"
echo "   sudo $BASE/scripts/rapid_probe.sh"
echo
echo " IMPORTANTE:"
echo "   Device Templates/canais devem ser provisionados somente para modelos"
echo "   Modbus validados. O cadastro TCP sozinho nao valida o mapa da controladora."
echo
echo " Controle remoto permanece opt-in. Para a IG200 validada:"
echo "   sudo $BASE/scripts/rapid_control_install.sh"
echo "============================================================"
