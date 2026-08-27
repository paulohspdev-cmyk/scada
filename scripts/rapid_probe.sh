#!/usr/bin/env bash
set -u

BASE=/opt/rc-scada
SCADA=/opt/scada

echo "============================================================"
echo " RC GERADORES - DIAGNOSTICO RAPID SCADA (SOMENTE LEITURA)"
echo "============================================================"
echo

echo "== Sistema =="
uname -a 2>/dev/null || true
printf 'Data UTC: '; date -u '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || true
echo

echo "== Pacotes / .NET =="
dpkg -l 2>/dev/null | grep -i rapidscada || true
dotnet --list-runtimes 2>/dev/null | sed -n '1,80p' || true
echo

echo "== Servicos Rapid SCADA =="
for svc in scadaagent6.service scadaserver6.service scadacomm6.service scadaweb6.service; do
  echo "--- $svc ---"
  systemctl show "$svc" -p LoadState -p ActiveState -p SubState -p ExecStart -p WorkingDirectory --no-pager 2>/dev/null || true
done
echo

echo "== Unit do Communicator =="
systemctl cat scadacomm6.service 2>/dev/null || true
echo

echo "== Estrutura principal /opt/scada =="
if [[ -d "$SCADA" ]]; then
  find "$SCADA" -maxdepth 3 -type d -print 2>/dev/null | sort | sed -n '1,180p'
else
  echo "/opt/scada nao existe"
fi
echo

echo "== Drivers e arquivos relacionados a Modbus =="
if [[ -d "$SCADA" ]]; then
  find "$SCADA" -type f \( -iname '*modbus*' -o -iname 'Drv*.dll' \) -print 2>/dev/null | sort | sed -n '1,220p'
fi
echo

echo "== Arquivos de configuracao que mencionam Modbus =="
if [[ -d "$SCADA" ]]; then
  grep -RilE 'Modbus|DrvModbus' "$SCADA/Instances" "$SCADA/ScadaComm" "$SCADA/ScadaServer" 2>/dev/null | sort | sed -n '1,160p'
fi
echo

echo "== XML/JSON de instancias e configuracao =="
if [[ -d "$SCADA" ]]; then
  find "$SCADA" -maxdepth 6 -type f \( -iname '*.xml' -o -iname '*.json' \) -print 2>/dev/null | sort | sed -n '1,240p'
fi
echo

echo "== GenMon instalado =="
if [[ -d "$BASE/vendor/genmon/.git" ]]; then
  printf 'Commit: '
  git -C "$BASE/vendor/genmon" rev-parse --short HEAD 2>/dev/null || true
  printf 'Branch: '
  git -C "$BASE/vendor/genmon" branch --show-current 2>/dev/null || true
  echo "Perfis de controladoras:"
  find "$BASE/vendor/genmon/data/controller" -maxdepth 1 -type f -print 2>/dev/null | sort | sed -n '1,120p'
else
  echo "GenMon nao encontrado em $BASE/vendor/genmon"
fi
echo

echo "== Portas atuais =="
ss -lntp 2>/dev/null | grep -E ':(150[0-9]{2}|250[0-9]{2}|8088)\b' || true
echo

echo "== Servicos RC =="
systemctl show rc-scada-web.service rc-scada-gateway.service rc-scada-rapid-bridge.service \
  -p Names -p LoadState -p ActiveState -p SubState -p ExecStart --no-pager 2>/dev/null || true
echo

echo "============================================================"
echo " FIM DO DIAGNOSTICO - nenhum arquivo foi alterado"
echo "============================================================"
