#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/rc-scada"
SRC="$BASE/rapid/reader"
OUT="$BASE/.rapid-reader"
CFG="/opt/scada/ScadaComm/Config/ScadaCommConfig.xml"
LINE_INFO="/var/log/scada/ScadaComm/Log/line100.txt"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0"
  exit 1
fi

[[ -f "$SRC/RcRapidReader.csproj" ]] || { echo "ERRO: projeto do leitor não encontrado"; exit 2; }
[[ -f "$CFG" ]] || { echo "ERRO: configuração do Rapid SCADA não encontrada"; exit 2; }

if [[ -f /opt/scada/ScadaComm/ScadaCommon.dll ]]; then
  SCADA_COMMON="/opt/scada/ScadaComm/ScadaCommon.dll"
else
  SCADA_COMMON="$(find /opt/scada -type f -name ScadaCommon.dll -print -quit)"
fi
[[ -n "${SCADA_COMMON:-}" && -f "$SCADA_COMMON" ]] || { echo "ERRO: ScadaCommon.dll não encontrado"; exit 2; }
SCADA_DLL_DIR="$(dirname "$SCADA_COMMON")"

echo "== Estado Rapid SCADA =="
systemctl is-active --quiet scadaserver6 || { echo "ERRO: scadaserver6 não está ativo"; exit 3; }
systemctl is-active --quiet scadacomm6 || { echo "ERRO: scadacomm6 não está ativo"; exit 3; }
systemctl is-active --quiet rc-scada-rapid-bridge || { echo "ERRO: rc-scada-rapid-bridge não está ativo"; exit 3; }
if [[ -f "$LINE_INFO" ]]; then
  grep -q 'Status[[:space:]]*: Normal' "$LINE_INFO" || { echo "ERRO: linha 100 do Communicator não está Normal"; cat "$LINE_INFO"; exit 3; }
fi

echo
echo "== Compilando cliente oficial ScadaClient =="
rm -rf "$OUT"
mkdir -p "$OUT"
dotnet build "$SRC/RcRapidReader.csproj" -c Release -o "$OUT" -p:ScadaCommonPath="$SCADA_COMMON" --nologo

# Garante no runtime as dependências publicadas junto com o Communicator.
find "$SCADA_DLL_DIR" -maxdepth 1 -type f -name 'Scada*.dll' -exec cp -n {} "$OUT/" \;

echo
echo "== Lendo canais 2001..2008 diretamente do Rapid SCADA Server =="
RESULT="$(dotnet "$OUT/RcRapidReader.dll" "$CFG" 2001 2002 2003 2004 2005 2006 2007 2008)"
printf '%s\n' "$RESULT" | python3 -m json.tool

printf '%s' "$RESULT" | python3 -c '
import json,sys
p=json.load(sys.stdin)
chs=p.get("channels",[])
if not p.get("ok") or len(chs)!=8:
    raise SystemExit("ERRO: resposta incompleta do Rapid SCADA")
if not any(int(x.get("stat",0))>0 for x in chs):
    raise SystemExit("ERRO: Rapid SCADA respondeu, mas os 8 canais estão indefinidos")
print("OK: Rapid SCADA Server possui dados atuais definidos")
'

echo
echo "== Tornando a arquitetura definitiva no boot =="
systemctl stop rc-scada-gateway 2>/dev/null || true
systemctl disable rc-scada-gateway 2>/dev/null || true
systemctl enable rc-scada-rapid-bridge

echo
echo "== Reiniciando somente o painel RC =="
systemctl restart rc-scada-web
sleep 5

echo
echo "== API Geradores =="
curl -fsS http://127.0.0.1:8088/api/generators | python3 -m json.tool

echo
echo "== Dashboard =="
curl -fsS http://127.0.0.1:8088/api/dashboard | python3 -m json.tool

echo
echo "== Serviços finais =="
systemctl --no-pager --full status rc-scada-web rc-scada-rapid-bridge scadaserver6 scadacomm6 2>/dev/null || true

echo
echo "ETAPA 3 CONCLUÍDA"
echo "Polling: Rapid SCADA Communicator"
echo "Dados do painel: Rapid SCADA Server"
echo "Ponte reversa: rc-scada-rapid-bridge (habilitada no boot)"
echo "Gateway Python antigo: desabilitado"
