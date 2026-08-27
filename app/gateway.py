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


def rtu_request(unit, address, count, function=3):
    if function not in (3, 4):
        raise ValueError(f"Função Modbus de leitura não suportada: {function}")
    pdu = struct.pack(">BBHH", unit, function, address, count)
    crc = crc16(pdu)
    return pdu + struct.pack("<H", crc)


async def rtu_response(reader, unit, count, function=3):
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

    if func != function:
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


def tcp_request(tid, unit, address, count, function=3):
    if function not in (3, 4):
        raise ValueError(f"Função Modbus de leitura não suportada: {function}")
    pdu = struct.pack(">BHH", function, address, count)
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu


async def tcp_response(reader, tid, unit, count, function=3):
    """Lê frames MBAP completos e descarta respostas atrasadas/estranhas.

    Em uma porta compartilhada, uma Unit ID lenta ou tráfego que chegue pelo
    gateway serial não pode desalinhavar o socket das demais controladoras.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 3.0

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()

        h = await asyncio.wait_for(reader.readexactly(7), remaining)
        rt, proto, length, ru = struct.unpack(">HHHB", h)

        if proto != 0:
            raise ValueError(f"MBAP inválido: protocol={proto}")
        if length < 2 or length > 260:
            raise ValueError(f"MBAP inválido: length={length}")

        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()

        body = await asyncio.wait_for(reader.readexactly(length - 1), remaining)

        # Sempre consumimos o frame completo antes de decidir ignorá-lo.
        if rt != tid or ru != unit:
            continue

        if not body:
            raise ValueError("resposta Modbus TCP vazia")
        if body[0] & 0x80:
            if len(body) < 2:
                raise ValueError("exceção Modbus TCP incompleta")
            raise ValueError(f"Exceção Modbus {body[1]}")
        if body[0] != function:
            raise ValueError(f"Função Modbus inesperada {body[0]}")
        if len(body) < 2:
            raise ValueError("resposta Modbus TCP incompleta")

        byte_count = body[1]
        payload = body[2 : 2 + byte_count]
        if byte_count != 2 * count or len(payload) != byte_count:
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


def decode_value(regs, point):
    dtype = str(point.get("datatype", "")).lower()
    raw = combine(regs)

    if dtype == "int16" and len(regs) == 1:
        raw = struct.unpack(">h", struct.pack(">H", regs[0]))[0]
    elif dtype == "int32" and len(regs) >= 2:
        raw = struct.unpack(">i", struct.pack(">I", combine(regs[:2])))[0]
    elif dtype == "float32" and len(regs) >= 2:
        raw = struct.unpack(">f", struct.pack(">HH", regs[0], regs[1]))[0]

    scale = float(point.get("scale", 1.0) or 1.0)
    value = raw * scale
    if isinstance(value, float):
        return round(value, 3)
    return value


async def poll_controller_once(g, reader, writer, tid):
    points = load_points(g)
    unit = int(g["modbus_unit"])
    values = {}
    point_errors = []

    if not points:
        return values, ["perfil sem pontos Modbus configurados"], tid

    for p in points:
        try:
            function = int(p.get("function", 3))
            if function not in (3, 4):
                point_errors.append(f"{p.get('key','point')}: função {function} ignorada")
                continue

            if g["transport"] == "rtu_over_tcp":
                writer.write(
                    rtu_request(
                        unit,
                        int(p["address"]),
                        int(p["count"]),
                        function,
                    )
                )
                await writer.drain()
                regs = await rtu_response(
                    reader,
                    unit,
                    int(p["count"]),
                    function,
                )
            else:
                current_tid = tid
                writer.write(
                    tcp_request(
                        current_tid,
                        unit,
                        int(p["address"]),
                        int(p["count"]),
                        function,
                    )
                )
                await writer.drain()
                regs = await tcp_response(
                    reader,
                    current_tid,
                    unit,
                    int(p["count"]),
                    function,
                )
                tid = 1 if tid >= 65535 else tid + 1

            values[p["key"]] = decode_value(regs, p)

        except ValueError as e:
            # Uma exceção de um ponto não derruba o modem nem as outras Units.
            if "Exceção Modbus" in str(e):
                point_errors.append(f"{p.get('key','point')}: {e}")
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
        for g in generators:
            db.update_telemetry(
                g["id"],
                connected=True,
                poll_ok=False,
                error=str(e),
            )
            db.add_event(g["id"], "WARN", f"Falha de polling: {e}")
    finally:
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
                    g.get("profile_updated_at"),
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
