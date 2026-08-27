"""Ponte entre modems TCP Client remotos e o Rapid SCADA local.

O modem continua iniciando a conexão para a porta pública do gerador (ex.:
15001). O Rapid SCADA se conecta somente em localhost à porta deslocada
(ex.: 25001) e atua como mestre Modbus. A ponte apenas encaminha requisições
Modbus TCP, serializa o acesso ao mesmo barramento remoto e reescreve o TID.

Nesta fase somente FC03 e FC04 são permitidas. Escritas são rejeitadas.
"""

import asyncio
import os
import struct

from . import db

REMOTE_BIND = os.environ.get("RC_RAPID_REMOTE_BIND", os.environ.get("RC_GATEWAY_BIND", "0.0.0.0"))
LOCAL_BIND = os.environ.get("RC_RAPID_LOCAL_BIND", "127.0.0.1")
LOCAL_OFFSET = int(os.environ.get("RC_RAPID_LOCAL_OFFSET", "10000"))
TIMEOUT = float(os.environ.get("RC_RAPID_BRIDGE_TIMEOUT", "4"))
RECONCILE_SECONDS = float(os.environ.get("RC_RAPID_RECONCILE_SECONDS", "5"))

READ_FUNCTIONS = {3, 4}


def log(message):
    print(f"[rapid-bridge] {message}", flush=True)


def mbap(tid, unit, pdu):
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu


def exception_pdu(function, code):
    return bytes([(function | 0x80) & 0xFF, code & 0xFF])


class BridgePort:
    def __init__(self, remote_port):
        self.remote_port = int(remote_port)
        self.local_port = self.remote_port + LOCAL_OFFSET
        self.remote_server = None
        self.local_server = None
        self.remote_reader = None
        self.remote_writer = None
        self.remote_peer = None
        self.remote_lock = asyncio.Lock()
        self.next_tid = 1

    def alloc_tid(self):
        tid = self.next_tid
        self.next_tid = 1 if tid >= 65535 else tid + 1
        return tid

    async def start(self):
        self.remote_server = await asyncio.start_server(
            self.accept_remote,
            REMOTE_BIND,
            self.remote_port,
        )
        try:
            self.local_server = await asyncio.start_server(
                self.accept_local,
                LOCAL_BIND,
                self.local_port,
            )
        except Exception:
            self.remote_server.close()
            await self.remote_server.wait_closed()
            self.remote_server = None
            raise

        log(
            f"porta {self.remote_port}: modem em {REMOTE_BIND}:{self.remote_port}; "
            f"Rapid SCADA em {LOCAL_BIND}:{self.local_port}"
        )

    async def stop(self):
        if self.remote_server:
            self.remote_server.close()
            await self.remote_server.wait_closed()
            self.remote_server = None
        if self.local_server:
            self.local_server.close()
            await self.local_server.wait_closed()
            self.local_server = None
        await self.clear_remote()

    async def clear_remote(self, only_writer=None):
        writer = self.remote_writer
        if only_writer is not None and writer is not only_writer:
            return
        self.remote_reader = None
        self.remote_writer = None
        self.remote_peer = None
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def accept_remote(self, reader, writer):
        peer = writer.get_extra_info("peername")
        old = self.remote_writer
        self.remote_reader = reader
        self.remote_writer = writer
        self.remote_peer = peer

        if old and old is not writer:
            try:
                old.close()
                await old.wait_closed()
            except Exception:
                pass

        log(f"porta {self.remote_port}: modem conectado de {peer}")

        try:
            # Não consumimos bytes aqui. A leitura do socket remoto acontece
            # somente enquanto uma requisição local do Rapid está sob lock.
            await writer.wait_closed()
        except Exception:
            pass
        finally:
            if self.remote_writer is writer:
                self.remote_reader = None
                self.remote_writer = None
                self.remote_peer = None
                log(f"porta {self.remote_port}: modem desconectado")

    async def read_remote_response(self, expected_tid, expected_unit, expected_function):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + TIMEOUT

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError()

            reader = self.remote_reader
            if reader is None:
                raise ConnectionError("modem desconectado")

            header = await asyncio.wait_for(reader.readexactly(7), remaining)
            tid, proto, length, unit = struct.unpack(">HHHB", header)
            if proto != 0 or length < 2 or length > 260:
                raise ValueError(
                    f"MBAP remoto inválido: tid={tid} proto={proto} length={length} unit={unit}"
                )

            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            pdu = await asyncio.wait_for(reader.readexactly(length - 1), remaining)

            # Fundamental em barramento compartilhado: sempre consumimos o
            # frame inteiro antes de descartar respostas atrasadas de outro TID
            # ou Unit ID. Assim o stream não perde alinhamento.
            if tid != expected_tid or unit != expected_unit:
                log(
                    f"porta {self.remote_port}: descartado frame atrasado "
                    f"tid={tid} unit={unit}; esperado tid={expected_tid} unit={expected_unit}"
                )
                continue

            if not pdu:
                raise ValueError("PDU remoto vazio")
            response_function = pdu[0]
            if response_function not in (expected_function, expected_function | 0x80):
                raise ValueError(
                    f"função remota inesperada {response_function}; esperada {expected_function}"
                )
            return pdu

    async def transact(self, local_tid, unit, pdu):
        if not pdu:
            return exception_pdu(0, 3)

        function = pdu[0]
        if function not in READ_FUNCTIONS:
            # Illegal Function. Nenhuma escrita passa pela ponte nesta fase.
            return exception_pdu(function, 1)

        async with self.remote_lock:
            reader = self.remote_reader
            writer = self.remote_writer
            if reader is None or writer is None or writer.is_closing():
                # Gateway Target Device Failed to Respond.
                return exception_pdu(function, 11)

            remote_tid = self.alloc_tid()
            try:
                writer.write(mbap(remote_tid, unit, pdu))
                await writer.drain()
                return await self.read_remote_response(remote_tid, unit, function)
            except asyncio.TimeoutError:
                # Um Unit ID que não responde não deve derrubar a sessão física
                # compartilhada por outras controladoras. Se uma resposta chegar
                # atrasada, read_remote_response() a consome e descarta pelo TID/Unit.
                log(
                    f"porta {self.remote_port}: timeout Unit {unit} FC{function:02d}; "
                    "mantendo conexão compartilhada"
                )
                return exception_pdu(function, 11)
            except (ConnectionError, asyncio.IncompleteReadError) as exc:
                log(
                    f"porta {self.remote_port}: conexão perdida Unit {unit} FC{function:02d}: {type(exc).__name__}"
                )
                await self.clear_remote(only_writer=writer)
                return exception_pdu(function, 11)
            except Exception as exc:
                log(
                    f"porta {self.remote_port}: erro remoto Unit {unit} FC{function:02d}: {exc}"
                )
                await self.clear_remote(only_writer=writer)
                return exception_pdu(function, 11)

    async def accept_local(self, reader, writer):
        peer = writer.get_extra_info("peername")
        log(f"porta local {self.local_port}: Rapid SCADA conectado de {peer}")
        try:
            while not reader.at_eof():
                header = await reader.readexactly(7)
                local_tid, proto, length, unit = struct.unpack(">HHHB", header)
                if proto != 0 or length < 2 or length > 260:
                    raise ValueError(
                        f"MBAP local inválido: proto={proto} length={length} unit={unit}"
                    )
                pdu = await reader.readexactly(length - 1)
                response_pdu = await self.transact(local_tid, unit, pdu)
                writer.write(mbap(local_tid, unit, response_pdu))
                await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        except ConnectionResetError:
            pass
        except Exception as exc:
            log(f"porta local {self.local_port}: sessão encerrada por erro: {exc}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            log(f"porta local {self.local_port}: Rapid SCADA desconectado")


bridges = {}


async def reconcile():
    while True:
        enabled = [g for g in db.list_generators() if g.get("enabled")]
        wanted_ports = sorted({int(g["listen_port"]) for g in enabled})

        for port in wanted_ports:
            if port in bridges:
                continue
            bridge = BridgePort(port)
            await bridge.start()
            bridges[port] = bridge

        for port in list(bridges):
            if port in wanted_ports:
                continue
            bridge = bridges.pop(port)
            await bridge.stop()
            log(f"porta {port}: ponte removida")

        await asyncio.sleep(RECONCILE_SECONDS)


async def main():
    db.init_db()
    log("iniciando ponte Rapid SCADA em modo somente leitura (FC03/FC04)")
    try:
        await reconcile()
    finally:
        await asyncio.gather(*(b.stop() for b in list(bridges.values())), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
