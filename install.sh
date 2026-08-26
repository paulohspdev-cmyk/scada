#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/paulohspdev-cmyk/scada.git"
BASE="/opt/rc-scada"
RAPID_VERSION="6.4.7"
RAPID_URL="https://rapidscada.org/download/rapidscada_${RAPID_VERSION}_linux_en.zip"
TMP="/tmp/rc-scada-install"

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root: sudo bash install.sh"
  exit 1
fi

echo "== RC Geradores SCADA =="
echo "Instalando dependências..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl unzip nginx python3 python3-venv python3-pip ca-certificates jq openssl

if ! command -v dotnet >/dev/null 2>&1 || ! dotnet --list-runtimes 2>/dev/null | grep -q 'Microsoft.AspNetCore.App 8'; then
  echo "Instalando ASP.NET Core Runtime 8..."
  if ! DEBIAN_FRONTEND=noninteractive apt-get install -y aspnetcore-runtime-8.0; then
    mkdir -p /usr/share/dotnet
    curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
    bash /tmp/dotnet-install.sh --channel 8.0 --runtime aspnetcore --install-dir /usr/share/dotnet
    ln -sfn /usr/share/dotnet/dotnet /usr/bin/dotnet
  fi
fi

if ! id rcscada >/dev/null 2>&1; then
  useradd --system --home "$BASE" --shell /usr/sbin/nologin rcscada
fi

echo "Baixando/atualizando nosso sistema..."
if [[ -d "$BASE/.git" ]]; then
  git -C "$BASE" fetch origin main
  git -C "$BASE" reset --hard origin/main
else
  rm -rf "$BASE"
  git clone "$REPO" "$BASE"
fi

mkdir -p "$BASE/vendor"
echo "Baixando GenMon oficial..."
if [[ -d "$BASE/vendor/genmon/.git" ]]; then
  git -C "$BASE/vendor/genmon" pull --ff-only
else
  git clone --depth 1 https://github.com/jgyates/genmon.git "$BASE/vendor/genmon"
fi

echo "Instalando Rapid SCADA Community ${RAPID_VERSION}..."
rm -rf "$TMP"; mkdir -p "$TMP"
curl -fL "$RAPID_URL" -o "$TMP/rapidscada.zip"
unzip -q "$TMP/rapidscada.zip" -d "$TMP/pkg"
DEB="$(find "$TMP/pkg" -type f -name 'rapidscada_*_all.deb' | head -n1 || true)"
if [[ -n "$DEB" ]]; then
  dpkg -i "$DEB" || { apt-get -f install -y; dpkg -i "$DEB"; }
else
  SCADA_DIR="$(find "$TMP/pkg" -type d -name scada | head -n1 || true)"
  DAEMONS_DIR="$(find "$TMP/pkg" -type d -name daemons | head -n1 || true)"
  [[ -n "$SCADA_DIR" && -n "$DAEMONS_DIR" ]] || { echo "Pacote Rapid SCADA com estrutura inesperada."; exit 2; }
  mkdir -p /opt/scada
  cp -a "$SCADA_DIR"/. /opt/scada/
  chmod +x /opt/scada/make_executable.sh
  /opt/scada/make_executable.sh
  cp -a "$DAEMONS_DIR"/. /etc/systemd/system/
fi

echo "Preparando aplicação RC..."
python3 -m venv "$BASE/.venv"
"$BASE/.venv/bin/pip" install --upgrade pip
"$BASE/.venv/bin/pip" install -r "$BASE/requirements.txt"
mkdir -p /var/lib/rc-scada /var/log/rc-scada
chown -R rcscada:rcscada /var/lib/rc-scada /var/log/rc-scada
chown -R rcscada:rcscada "$BASE"

cat >/etc/rc-scada.env <<EOF
RC_DB_PATH=/var/lib/rc-scada/scada.db
RC_BIND=127.0.0.1
RC_WEB_PORT=8088
GENMON_ROOT=/opt/rc-scada/vendor/genmon
RC_GATEWAY_BIND=0.0.0.0
RC_POLL_SECONDS=2
EOF
chmod 640 /etc/rc-scada.env
chown root:rcscada /etc/rc-scada.env

cp "$BASE/systemd/rc-scada-web.service" /etc/systemd/system/
cp "$BASE/systemd/rc-scada-gateway.service" /etc/systemd/system/
systemctl daemon-reload

sudo -u rcscada env RC_DB_PATH=/var/lib/rc-scada/scada.db \
  PYTHONPATH="$BASE" "$BASE/.venv/bin/python" "$BASE/scripts/init_db.py"

echo "Configurando Nginx para a interface RC..."
cp "$BASE/nginx/rc-scada.conf" /etc/nginx/sites-available/rc-scada
ln -sfn /etc/nginx/sites-available/rc-scada /etc/nginx/sites-enabled/rc-scada
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx

echo "Ativando RC SCADA..."
systemctl enable --now rc-scada-web rc-scada-gateway

echo "Ativando serviços Rapid SCADA disponíveis..."
for svc in scadaagent6.service scadaserver6.service scadacomm6.service scadaweb6.service; do
  if [[ -f "/etc/systemd/system/$svc" ]] || systemctl list-unit-files "$svc" --no-legend 2>/dev/null | grep -q "$svc"; then
    systemctl enable "$svc" || true
    systemctl restart "$svc" || true
  fi
done

IP="$(hostname -I | awk '{print $1}')"
echo
echo "============================================================"
echo " RC GERADORES INSTALADO"
echo "============================================================"
echo " Interface: http://${IP:-IP_DA_VM}/"
echo " Banco:     /var/lib/rc-scada/scada.db"
echo " GenMon:    $BASE/vendor/genmon"
echo " Rapid:     /opt/scada"
echo
echo " Cadastre o primeiro gerador pela interface."
echo " O sistema atribuirá portas TCP a partir de 15001."
echo " Libere/encaminhe no firewall apenas as portas usadas."
echo
echo " Status:"
echo "   $BASE/scripts/status.sh"
echo
echo " Atualização futura:"
echo "   cd $BASE && sudo git pull && sudo systemctl restart rc-scada-web rc-scada-gateway"
echo "============================================================"
