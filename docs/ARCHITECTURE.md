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

A ponte existe porque o modem inicia a sessão TCP a partir do campo, enquanto o Rapid SCADA atua como cliente/mestre Modbus.

Responsabilidades:

- aceitar a conexão reversa do modem na porta pública cadastrada;
- expor a sessão ao Rapid SCADA em localhost usando o deslocamento de porta configurado;
- preservar uma única sessão física quando vários Unit IDs compartilham o mesmo modem/barramento;
- serializar requisições e respostas;
- reescrever Transaction IDs Modbus TCP sem perder alinhamento do stream;
- manter o caminho normal do Rapid SCADA somente leitura, atualmente FC03/FC04.

A ponte **não é o SCADA** e não executa polling de telemetria por conta própria.

## Rapid SCADA Communicator

É o mestre Modbus da arquitetura. Cada controladora validada recebe Device Template e configuração de polling no Rapid SCADA.

A primeira integração validada é a ComAp InteliGen 200 no Unit ID 2. Outras controladoras entram somente após validação de mapa/modelo/firmware.

## Rapid SCADA Server

É a fonte oficial de dados atuais para o produto RC. O backend lê os canais pelo cliente oficial `ScadaClient` e traduz os números de canais para as métricas exibidas no painel.

Histórico, alarmística e demais funções industriais devem permanecer no Rapid SCADA sempre que possível, evitando duplicar um segundo motor SCADA em Python.

## Painel RC Geradores

O painel é a camada de produto e operação. O SQLite próprio mantém cadastro, metadados do produto e eventos da aplicação.

O SQLite não é fonte industrial de telemetria nem historiador. Equipamentos vinculados recebem seus dados em runtime a partir do Rapid SCADA Server.

## Mapas Modbus

Não existe mais uma camada de perfis Modbus executada pelo backend Python.

A fonte técnica de cada modelo é:

```text
rapid/templates/   -> mapa de registradores homologado
rapid/bindings.json -> canais do Rapid SCADA usados pelo painel
```

O catálogo de controladoras contém apenas fabricante, família, modelo e aliases para cadastro.

GenMon não participa do runtime e não é instalado na VM de produção. Quando útil, pode ser consultado externamente como referência durante pesquisa de um novo modelo, sem se tornar dependência do produto.

## Controle remoto

O caminho TCP entregue ao Rapid SCADA continua bloqueando escritas Modbus genéricas.

Comandos remotos são implementados separadamente e somente quando:

- a sequência é específica do modelo e foi validada;
- existe confirmação explícita;
- existem intertravamentos pré-comando;
- o retorno da controladora é verificado;
- a ação é registrada para auditoria.

A InteliGen 200 possui START/STOP implementado dessa forma pelo socket Unix local privilegiado. A liberação genérica de FC06/FC16 na porta do Rapid SCADA não faz parte da arquitetura.

## Componentes removidos

A arquitetura antiga foi encerrada. Foram removidos do `main`:

- `app/gateway.py` e o serviço `rc-scada-gateway`;
- scripts de migração das etapas 1, 2 e 3;
- `app/profiles.py`;
- `app/profile_importer.py`;
- a documentação da antiga camada de perfis.

Bases SQLite antigas podem continuar contendo tabelas `telemetry` e `generator_profiles`; elas não são mais usadas pelo runtime e não precisam ser apagadas de forma destrutiva.

## Regra de evolução

Para cada nova controladora:

1. validar comunicação e mapa somente leitura;
2. criar Device Template do Rapid SCADA;
3. criar/vincular canais no Rapid SCADA Server;
4. adicionar binding do painel;
5. validar histórico/alarmes;
6. somente depois considerar comandos remotos específicos do modelo.
