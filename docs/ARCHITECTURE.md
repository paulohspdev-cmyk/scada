# Arquitetura

## Objetivo

Centralizar ComAp e DSE conectados por modems que iniciam sessões TCP para a VM pública.

```text
ComAp/DSE
   |
RS485/Ethernet
   |
Modem TCP Client
   |
Internet
   |
VM pública
   +-- RC Gateway (TCP Server + Modbus master)
   +-- Rapid SCADA
   +-- RC Backend / SQLite
   +-- Interface web RC Geradores
   +-- GenMon (vendor externo, referência de perfis)
```

## Papéis

### RC Gateway
Aceita conexão reversa em uma porta por gerador. Dentro dessa sessão atua como cliente/master Modbus. Nesta fase suporta:
- Modbus RTU transportado transparentemente sobre TCP;
- Modbus TCP;
- função 03 (Holding Registers);
- leitura somente.

### GenMon
É clonado em `vendor/genmon`. O sistema lê, em runtime, os perfis `ComAp.json` e `Deepsea_controller.json` para descobrir parte dos registradores. Não copiamos esses perfis para nosso repositório.

### Rapid SCADA
É instalado como plataforma industrial paralela. A próxima etapa de campo é transformar os pontos validados em Device Templates/Channels do Rapid SCADA. Não dependemos dessa automação para validar a comunicação reversa.

### Interface RC
Cadastro multi-gerador, portas TCP, status, telemetria e eventos. Depois recebe alarmes, histórico, usuários, manutenção e comandos.

## Regra de segurança

Escritas/comandos Modbus estão deliberadamente desabilitados na primeira fase. Start/Stop/Reset só entram depois de validação em bancada, permissões e auditoria.
