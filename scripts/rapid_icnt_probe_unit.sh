#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/rc-scada"
LOCAL_HOST="127.0.0.1"
LOCAL_PORT="25001"
ADDRESS="57"
COUNT="1"
UNIT="${1:-}"

if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0 <unit_id>"
  exit 1
fi

if [[ -z "$UNIT" || ! "$UNIT" =~ ^[0-9]+$ ]] || (( UNIT < 1 || UNIT > 247 )); then
  echo "Uso: sudo bash $0 <unit_id>"
  echo "Exemplo: sudo bash $0 4"
  exit 2
fi

systemctl is-active --quiet rc-scada-rapid-bridge || {
  echo "ERRO: rc-scada-rapid-bridge não está ativa"
  exit 3
}
systemctl is-active --quiet scadacomm6 || {
  echo "ERRO: scadacomm6 não está ativo"
  exit 3
}

restore_comm() {
  rc=$?
  trap - EXIT INT TERM
  systemctl start scadacomm6 >/dev/null 2>&1 || true
  sleep 7
  echo
  echo "== Estado da linha 100 após o probe =="
  cat /var/log/scada/ScadaComm/Log/line100.txt 2>/dev/null || true
  exit "$rc"
}
trap restore_comm EXIT INT TERM

echo "== Probe seguro InteliCompact NT =="
echo "Unit ID : $UNIT"
echo "Função  : FC03 (somente leitura)"
echo "Endereço: $ADDRESS"
echo

echo "Parando somente o Communicator para não haver dois clientes locais..."
systemctl stop scadacomm6
sleep 1

python3 - "$LOCAL_HOST" "$LOCAL_PORT" "$UNIT" "$ADDRESS" "$COUNT" <<'PY'
import socket
import struct
import sys

host = sys.argv[1]
port = int(sys.argv[2])
unit = int(sys.argv[3])
address = int(sys.argv[4])
count = int(sys.argv[5])

tid = 0x7A01
pdu = struct.pack(">BHH", 3, address, count)
frame = struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu

print(f"Conectando a {host}:{port} ...")
with socket.create_connection((host, port), timeout=3.0) as s:
    # Deve ser maior que RC_RAPID_BRIDGE_TIMEOUT (4 s), para receber a
    # exceção limpa da bridge em vez de abandonar a requisição no meio.
    s.settimeout(7.0)
    s.sendall(frame)

    def recv_exact(n):
        data = b""
        while len(data) < n:
            chunk = s.recv(n - len(data))
            if not chunk:
                raise RuntimeError("conexão fechada antes da resposta completa")
            data += chunk
        return data

    hdr = recv_exact(7)
    rtid, proto, length, runit = struct.unpack(">HHHB", hdr)
    if proto != 0 or length < 2 or length > 260:
        raise RuntimeError(f"MBAP inválido: tid={rtid} proto={proto} length={length} unit={runit}")
    body = recv_exact(length - 1)

    print("MBAP:", hdr.hex(" ").upper())
    print("PDU :", body.hex(" ").upper())

    if rtid != tid:
        raise RuntimeError(f"TID inesperado: {rtid}, esperado {tid}")
    if runit != unit:
        raise RuntimeError(f"Unit inesperado: {runit}, esperado {unit}")
    if not body:
        raise RuntimeError("PDU vazio")

    fc = body[0]
    if fc & 0x80:
        code = body[1] if len(body) > 1 else -1
        if code == 11:
            print(f"RESULTADO: SEM RESPOSTA do Unit {unit} (bridge retornou exceção 0x0B após timeout).")
            raise SystemExit(10)
        print(f"RESULTADO: Unit {unit} respondeu exceção Modbus {code}.")
        raise SystemExit(11)

    if fc != 3 or len(body) != 4 or body[1] != 2:
        raise RuntimeError(f"resposta FC03 inesperada: {body.hex()}")

    value = struct.unpack(">H", body[2:4])[0]
    signed = value if value < 0x8000 else value - 0x10000
    print(f"RESULTADO: UNIT {unit} RESPONDEU corretamente.")
    print(f"Registro {address}: uint16={value} int16={signed} hex=0x{value:04X}")
PY

# Só chega aqui quando o Unit respondeu FC03 corretamente.
echo
echo "PROBE CONFIRMADO: Unit $UNIT respondeu ao FC03 no endereço $ADDRESS."
