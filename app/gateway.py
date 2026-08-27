import asyncio
import os
import struct
from . import db
from .profiles import load_points

BIND = os.environ.get("RC_GATEWAY_BIND", "0.0.0.0")
POLL_SECONDS = float(os.environ.get("RC_POLL_SECONDS", "2"))
servers = {}
active_connections = {}


def crc16(data: bytes):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def rtu_request(unit, address, count):
    pdu = struct.pack(">BBHH", unit, 3, address, count)
    crc = crc16(pdu)
    return pdu + struct.pack("<H", crc)


async def rtu_response(reader, unit, count):
    head = await asyncio.wait_for(reader.readexactly(2), 3)
    ru, func = head[0], head[1]
    if ru != unit:
        raise ValueError(f"Unit ID inesperado {ru}")

    if func & 0x80:
        tail = await asyncio.wait_for(reader.readexactly(3), 3)
        frame = head + tail
        if crc16(frame[:-2]) != struct.unpack("<H", frame[-2:])[0]:
            raise ValueError("CRC inválido")
        raise ValueError(f"Exceção Modbus {frame[2]}")

    if func != 3:
        raise ValueError(f"Função Modbus inesperada {func}")

    byte_count_raw = await asyncio.wait_for(reader.readexactly(1), 3)
    byte_count = byte_count_raw[0]
    tail = await asyncio.wait_for(reader.readexactly(byte_count + 2), 3)
    frame = head + byte_count_raw + tail

    if byte_count != 2 * count:
        raise ValueError(f"resposta RTU com tamanho inesperado {byte_count}")
    if crc16(frame[:-2]) != struct.unpack("<H", frame[-2:])[0]:
        raise ValueError("CRC inválido")

    payload = frame[3:-2]
    return [
        struct.unpack(">H", payload[i : i + 2])[0]
        for i in range(0, len(payload), 2)
    ]


def tcp_request(tid, unit, address, count):
    pdu = struct.pack(">BHH", 3, address, count)
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu


async def tcp_response(reader, tid, unit, count):
    h = await asyncio.wait_for(reader.readexactly(7), 3)
    rt, proto, length, ru = struct.unpack(">HHHB", h)
    if rt != tid or proto != 0 or ru != unit:
        raise ValueError("MBAP inválido")

    body = await asyncio.wait_for(reader.readexactly(length - 1), 3)
    if body[0] & 0x80:
        raise ValueError(f"Exceção Modbus {body[1]}")
    if body[0] != 3:
        raise ValueError("Função Modbus inesperada")

    byte_count = body[1]
    payload = body[2 : 2 + byte_count]
    if byte_count != 2 * count:
        raise ValueError(f"resposta TCP com tamanho inesperado {byte_count}")

    return [
        struct.unpack(">H", payload[i : i + 2])[0]
        for i in range(0, len(payload), 2)
    ]


def combine(regs):
    v = 0
    for r in regs:
        v = (v << 16) | r
    return v


async def poll_controller_once(g, reader, writer, tid):
    points = load_points(g["controller_type"], g.get("controller_model"))
    unit = int(g["modbus_unit"])
    values = {}
    point_errors = []

    for p in points:
        try:
            if g["transport"] == "rtu_over_tcp":
                writer.write(rtu_request(unit, p["address"], p["count"]))
                await writer.drain()
                regs = await rtu_response(reader, unit, p["count"])
            else:
                current_tid = tid
                writer.write(
                    tcp_request(current_tid, unit, p["address"], p["count"])
                )
                await writer.drain()
                regs = await tcp_response(
                    reader,
                    current_tid,
                    unit,
                    p["count"],
                )
                tid = 1 if tid >= 65535 else tid + 1

            raw = combine(regs)
            values[p["key"]] = round(raw * p["scale"], 3)

        except ValueError as e:
            # Uma excecao Modbus de um registrador nao deve derrubar o modem,
            # nem impedir a leitura das outras controladoras da mesma porta.
            if "Exceção Modbus" in str(e):
                point_errors.append(f"{p['key']}: {e}")
                continue
            raise

    return values, point_errors, tid


async def poll_port(generators, reader, writer):
    """Faz polling sequencial de todos os Unit IDs ligados ao mesmo modem."""
    tid = 1

    while not reader.at_eof():
        for g in generators:
            try:
                values, point_errors, tid = await poll_controller_once(
                    g,
                    reader,
                    writer,
                    tid,
                )

                if values:
                    db.update_telemetry(
                        g["id"],
                        connected=True,
                        poll_ok=True,
                        values=values,
                        error="",
                    )
                else:
                    db.update_telemetry(
                        g["id"],
                        connected=True,
                        poll_ok=False,
                        values={},
                        error=(
                            "; ".join(point_errors[:3])
                            or "sem dados Modbus válidos"
                        ),
                    )

            except asyncio.TimeoutError:
                # Um Unit ID pode estar offline enquanto o outro continua na
                # mesma rede RS485. Mantemos a sessao TCP do modem ativa.
                db.update_telemetry(
                    g["id"],
                    connected=True,
                    poll_ok=False,
                    error=f"timeout Modbus no Unit ID {g['modbus_unit']}",
                )
                continue

        await asyncio.sleep(POLL_SECONDS)


async def client(port, generators, reader, writer):
    peer = writer.get_extra_info("peername")
    old = active_connections.get(port)
    if old and old is not writer:
        try:
            old.close()
        except Exception:
            pass

    active_connections[port] = writer

    for g in generators:
        db.update_telemetry(
            g["id"],
            connected=True,
            poll_ok=False,
            peer=peer,
            error="",
        )
        db.add_event(
            g["id"],
            "INFO",
            f"Modem conectado de {peer} na porta {port}; Unit ID {g['modbus_unit']}",
        )

    try:
        await poll_port(generators, reader, writer)
    except Exception as e:
        # Erro de framing/conexao e fatal para a sessao compartilhada.
        for g in generators:
            db.update_telemetry(
                g["id"],
                connected=True,
                poll_ok=False,
                error=str(e),
            )
            db.add_event(g["id"], "WARN", f"Falha de polling: {e}")
    finally:
        # Se uma conexao nova ja substituiu esta, nao marque os geradores como
        # offline por causa do fechamento tardio da conexao antiga.
        if active_connections.get(port) is writer:
            active_connections.pop(port, None)
            for g in generators:
                db.update_telemetry(
                    g["id"],
                    connected=False,
                    poll_ok=False,
                    error="desconectado",
                )

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _close_port(port):
    current = servers.pop(port, None)
    if current:
        current["server"].close()
        await current["server"].wait_closed()

    writer = active_connections.get(port)
    if writer:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def reconcile():
    while True:
        enabled = [g for g in db.list_generators() if g["enabled"]]
        by_port = {}
        for g in enabled:
            by_port.setdefault(int(g["listen_port"]), []).append(g)

        for port, generators in by_port.items():
            generators.sort(key=lambda g: (int(g["modbus_unit"]), g["id"]))
            signature = tuple(
                (
                    g["id"],
                    g["transport"],
                    int(g["modbus_unit"]),
                    g["controller_type"],
                    g.get("controller_model"),
                )
                for g in generators
            )

            current = servers.get(port)
            if current and current["signature"] == signature:
                continue

            if current:
                await _close_port(port)

            snapshot = tuple(generators)
            srv = await asyncio.start_server(
                lambda r, w, p=port, gg=snapshot: client(p, gg, r, w),
                BIND,
                port,
            )
            servers[port] = {"server": srv, "signature": signature}

            for g in generators:
                db.add_event(
                    g["id"],
                    "INFO",
                    f"Gateway ouvindo {BIND}:{port} para Modbus Unit ID {g['modbus_unit']}",
                )

        for port in list(servers):
            if port not in by_port:
                await _close_port(port)

        await asyncio.sleep(5)


async def main():
    db.init_db()
    await reconcile()


if __name__ == "__main__":
    asyncio.run(main())
