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


def parse_rtu(frame, unit, count):
    if len(frame) != 5 + 2 * count:
        raise ValueError(f"resposta RTU com tamanho inesperado {len(frame)}")
    if frame[0] != unit:
        raise ValueError(f"Unit ID inesperado {frame[0]}")
    if frame[1] & 0x80:
        raise ValueError(f"Exceção Modbus {frame[2]}")
    if frame[1] != 3:
        raise ValueError(f"Função Modbus inesperada {frame[1]}")
    if crc16(frame[:-2]) != struct.unpack("<H", frame[-2:])[0]:
        raise ValueError("CRC inválido")
    payload = frame[3:-2]
    return [struct.unpack(">H", payload[i : i + 2])[0] for i in range(0, len(payload), 2)]


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
    payload = body[2:]
    return [struct.unpack(">H", payload[i : i + 2])[0] for i in range(0, len(payload), 2)]


def combine(regs):
    v = 0
    for r in regs:
        v = (v << 16) | r
    return v


async def poll(g, reader, writer):
    points = load_points(g["controller_type"], g.get("controller_model"))
    unit = int(g["modbus_unit"])
    tid = 1

    while not reader.at_eof():
        values = {}
        point_errors = []

        for p in points:
            try:
                if g["transport"] == "rtu_over_tcp":
                    writer.write(rtu_request(unit, p["address"], p["count"]))
                    await writer.drain()
                    frame = await asyncio.wait_for(reader.readexactly(5 + 2 * p["count"]), 3)
                    regs = parse_rtu(frame, unit, p["count"])
                else:
                    writer.write(tcp_request(tid, unit, p["address"], p["count"]))
                    await writer.drain()
                    regs = await tcp_response(reader, tid, unit, p["count"])
                    tid = 1 if tid >= 65535 else tid + 1

                raw = combine(regs)
                values[p["key"]] = round(raw * p["scale"], 3)

            except ValueError as e:
                # Exceção Modbus para um ponto individual não deve derrubar a
                # sessão TCP inteira. Registramos o ponto e seguimos o polling.
                if "Exceção Modbus" in str(e):
                    point_errors.append(f"{p['key']}: {e}")
                    continue
                raise

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
                error="; ".join(point_errors[:3]) or "sem dados Modbus válidos",
            )

        await asyncio.sleep(POLL_SECONDS)


async def client(g, reader, writer):
    peer = writer.get_extra_info("peername")
    old = active_connections.get(g["id"])
    if old and old is not writer:
        try:
            old.close()
        except Exception:
            pass

    active_connections[g["id"]] = writer
    db.update_telemetry(g["id"], connected=True, poll_ok=False, peer=peer, error="")
    db.add_event(g["id"], "INFO", f"Modem conectado de {peer}")

    try:
        await poll(g, reader, writer)
    except Exception as e:
        db.update_telemetry(g["id"], connected=True, poll_ok=False, error=str(e))
        db.add_event(g["id"], "WARN", f"Falha de polling: {e}")
    finally:
        if active_connections.get(g["id"]) is writer:
            active_connections.pop(g["id"], None)
        db.update_telemetry(g["id"], connected=False, poll_ok=False, error="desconectado")
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def reconcile():
    while True:
        wanted = {g["id"]: g for g in db.list_generators() if g["enabled"]}

        for gid, g in wanted.items():
            current = servers.get(gid)
            signature = (
                g["listen_port"],
                g["transport"],
                g["modbus_unit"],
                g["controller_type"],
                g.get("controller_model"),
            )

            if current and current["signature"] == signature:
                continue

            if current:
                current["server"].close()
                await current["server"].wait_closed()

            srv = await asyncio.start_server(
                lambda r, w, gg=g: client(gg, r, w),
                BIND,
                int(g["listen_port"]),
            )
            servers[gid] = {"server": srv, "signature": signature}
            db.add_event(gid, "INFO", f"Gateway ouvindo {BIND}:{g['listen_port']}")

        for gid in list(servers):
            if gid not in wanted:
                servers[gid]["server"].close()
                await servers[gid]["server"].wait_closed()
                servers.pop(gid)

        await asyncio.sleep(5)


async def main():
    db.init_db()
    await reconcile()


if __name__ == "__main__":
    asyncio.run(main())
