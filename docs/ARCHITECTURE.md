# Arquitetura oficial

## Objetivo

Centralizar controladoras ComAp e DSE conectadas por modems que iniciam sessões TCP para a VM, mantendo o Rapid SCADA como motor industrial de aquisição, canais, estado, histórico e alarmística.

```text
ComAp / DSE
    |
 RS485 / Ethernet
    |
 Modem TCP Client
    |
 Internet
    |
    v
+-----------------------------+
| VM RC Geradores             |
|                             |
| RC Reverse TCP Bridge       |
|        |                    |
|        v                    |
| Rapid SCADA Communicator    |
|        |                    |
|        v                    |
| Rapid SCADA Server          |
|        |                    |
|   +----+----------------+   |
|   |                     |   |
|   v                     v   |
| RC Web             Controle |
|                    restrito |
+-----------------------------+
```

## RC Reverse TCP Bridge

A ponte existe porque o modem inicia a sessão TCP a partir do campo, enquanto o Rapid SCADA normalmente atua como cliente/mestre Modbus.

Responsabilidades da ponte:

- aceitar a conexão reversa do modem na porta pública cadastrada;
- expor a sessão ao Rapid SCADA em localhost, usando o deslocamento de porta configurado;
- preservar uma única sessão física quando vários Unit IDs compartilham o mesmo modem/barramento;
- serializar requisições e respostas;
- reescrever Transaction IDs Modbus TCP sem perder alinhamento do stream;
- manter o caminho normal do Rapid SCADA somente leitura, atualmente FC03/FC04.

A ponte **não é o SCADA** e não deve voltar a executar polling de telemetria por conta própria.

## Rapid SCADA Communicator

É o mestre Modbus da arquitetura. Cada controladora validada recebe Device Template e configuração de polling no Rapid SCADA.

A primeira integração validada é a ComAp InteliGen 200 no Unit ID 2. Outras controladoras entram somente após validação de mapa/modelo/firmware.

## Rapid SCADA Server

É a fonte oficial de dados atuais para o produto RC. O backend lê os canais pelo cliente oficial `ScadaClient` e traduz os números de canais para as métricas exibidas no painel.

Histórico, alarmística e demais funções industriais devem permanecer no Rapid SCADA sempre que possível, evitando duplicar um segundo motor SCADA em Python.

## Painel RC Geradores

O painel é a camada de produto e operação. Ele mantém cadastro e identidade RC, mas a telemetria de equipamentos vinculados vem do Rapid SCADA Server.

O SQLite próprio continua útil para cadastro, metadados do produto e eventos da aplicação. Ele não deve se tornar novamente o historiador industrial principal.

## Controle remoto

O caminho TCP entregue ao Rapid SCADA continua bloqueando escritas Modbus genéricas.

Comandos remotos são implementados separadamente e somente quando:

- a sequência é específica do modelo e foi validada;
- existe confirmação explícita;
- existem intertravamentos pré-comando;
- o retorno da controladora é verificado;
- a ação é registrada para auditoria.

A InteliGen 200 possui START/STOP implementado dessa forma pelo socket Unix local privilegiado. A liberação genérica de FC06/FC16 na porta do Rapid SCADA não faz parte da arquitetura.

## GenMon

O GenMon é mantido como dependência externa de referência para perfis, nomenclatura e pesquisa de controladoras quando aplicável. Ele não participa como mestre Modbus concorrente no fluxo normal.

## Componentes legados

`app/gateway.py` e `systemd/rc-scada-gateway.service` pertencem à arquitetura anterior, quando o Python fazia polling Modbus. Eles permanecem temporariamente apenas para uma última fase de limpeza e recuperação histórica.

Os scripts de migração `rapid_stage1_*`, `rapid_stage2_*` e `rapid_stage3_*` também são históricos. O plano de remoção está documentado em `docs/CLEANUP_PLAN.md`.

## Regra de evolução

Para cada nova controladora:

1. validar comunicação e mapa somente leitura;
2. criar Device Template do Rapid SCADA;
3. criar/vincular canais no Rapid SCADA Server;
4. adicionar binding do painel;
5. validar histórico/alarmes;
6. somente depois considerar comandos remotos específicos do modelo.
