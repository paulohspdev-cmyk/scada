# Plano de limpeza do repositório

Este documento separa o que pertence à arquitetura atual do que é legado de migração.

Antes desta reorganização foi criado o branch de segurança:

```text
checkpoint/pre-cleanup-rapid-20260827
```

Nenhum arquivo listado como histórico deve ser removido antes de concluir a validação da InteliCompact NT e revisar se existe dependência ativa na VM.

## Manter: núcleo definitivo

```text
app/__init__.py
app/controller_catalog.py
app/db.py
app/rapid_bridge.py
app/rapid_scada.py
app/web.py
app/static/
app/templates/

bin/rc-generator

rapid/bindings.json
rapid/reader/
rapid/templates/DrvModbus_RC_IG200.xml

scripts/init_db.py
scripts/rapid_control_install.sh
scripts/rapid_dat.py
scripts/rapid_probe.sh
scripts/status.sh

systemd/rc-scada-rapid-bridge.service
systemd/rc-scada-web.service

nginx/
requirements.txt
install.sh
README.md
docs/
```

Motivo: esses componentes formam a arquitetura atual:

```text
modem -> reverse bridge -> Rapid SCADA Communicator -> Rapid SCADA Server -> painel RC
```

## Manter temporariamente: InteliCompact NT em validação

```text
rapid/templates/DrvModbus_RC_ICNT_PROBE.xml
rapid/templates/DrvModbus_RC_ICNT.xml
scripts/rapid_stage4_icnt.sh
```

Depois da validação:

- `DrvModbus_RC_ICNT.xml` permanece somente se o mapa for confirmado em campo;
- `DrvModbus_RC_ICNT_PROBE.xml` pode ser removido;
- `rapid_stage4_icnt.sh` pode ser removido ou substituído por provisionamento genérico.

## Legado: remover na segunda limpeza

```text
app/gateway.py
systemd/rc-scada-gateway.service

scripts/rapid_stage1_prepare.sh
scripts/rapid_stage1_cutover.sh
scripts/rapid_stage1_rollback.sh
scripts/rapid_stage2_bind.sh
scripts/rapid_stage2_rollback.sh
scripts/rapid_stage3_panel.sh
```

Motivo:

- `app/gateway.py` pertence ao período em que Python fazia polling Modbus;
- `rc-scada-gateway.service` inicia esse motor antigo;
- etapas 1, 2 e 3 foram scripts de migração para chegar ao Rapid SCADA e não fazem parte do runtime normal.

O instalador atual já não habilita o gateway legado.

## Revisar antes de remover

```text
app/profiles.py
app/profile_importer.py
docs/COMAP_PROFILES.md
```

Esses arquivos ainda são referenciados por partes do backend e representam a camada antiga de perfil/importação no Python. A remoção correta exige primeiro simplificar `app/web.py` e o cadastro para que os templates/bindings do Rapid SCADA sejam a fonte técnica dos pontos.

## GenMon

O GenMon não é incorporado ao Git deste repositório; o instalador o clona em `vendor/genmon`.

Decisão atual: manter como referência externa para perfis, nomenclatura e pesquisa, sem executar polling concorrente com o Rapid SCADA.

Em uma revisão futura pode ser decidido remover essa dependência se os templates homologados do Rapid SCADA cobrirem todo o catálogo necessário.

## Regras para a próxima limpeza

Antes de deletar arquivos legados:

1. confirmar `rc-scada-gateway` inativo e desabilitado na VM;
2. confirmar `rc-scada-rapid-bridge`, `scadacomm6`, `scadaserver6` e `rc-scada-web` ativos;
3. confirmar painel lendo `telemetry_source=rapid_scada` para a IG200;
4. confirmar START e STOP da IG200 pelo caminho restrito;
5. concluir ou abortar formalmente a validação da InteliCompact NT;
6. procurar referências aos arquivos candidatos a remoção;
7. só então executar deletes em um commit dedicado.

## Estrutura alvo

```text
scada/
├── app/
│   ├── db.py
│   ├── rapid_bridge.py
│   ├── rapid_scada.py
│   ├── web.py
│   ├── controller_catalog.py
│   ├── static/
│   └── templates/
├── bin/
│   └── rc-generator
├── rapid/
│   ├── bindings.json
│   ├── reader/
│   └── templates/
├── scripts/
│   ├── init_db.py
│   ├── rapid_control_install.sh
│   ├── rapid_dat.py
│   ├── rapid_probe.sh
│   └── status.sh
├── systemd/
│   ├── rc-scada-web.service
│   └── rc-scada-rapid-bridge.service
├── docs/
├── nginx/
├── install.sh
└── requirements.txt
```
