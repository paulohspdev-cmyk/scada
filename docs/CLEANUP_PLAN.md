# Limpeza do repositório

A arquitetura oficial do RC Geradores é:

```text
modem TCP Client
  -> RC Reverse Bridge
  -> Rapid SCADA Communicator
  -> Rapid SCADA Server
  -> painel RC
```

Branches de segurança criados durante a limpeza:

```text
checkpoint/pre-cleanup-rapid-20260827
checkpoint/pre-profile-cleanup-20260827
```

## Núcleo definitivo

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

## Limpezas concluídas

Foram removidos do `main` os componentes do polling Python antigo e os scripts usados somente durante a migração:

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

Também foi removida a antiga camada de perfis/importação Modbus do backend:

```text
app/profiles.py
app/profile_importer.py
docs/COMAP_PROFILES.md
```

O SQLite de runtime também deixou de usar telemetria e perfis próprios. Bases antigas podem continuar contendo as tabelas `telemetry` e `generator_profiles`; elas são ignoradas e não precisam ser apagadas de forma destrutiva.

GenMon deixou de ser dependência de produção e não é mais clonado pelo instalador. Pode ser usado externamente durante pesquisa, sem participar do runtime.

## InteliCompact NT: manter temporariamente

```text
rapid/templates/DrvModbus_RC_ICNT_PROBE.xml
rapid/templates/DrvModbus_RC_ICNT.xml
scripts/rapid_stage4_icnt.sh
```

Depois da validação de campo:

- `DrvModbus_RC_ICNT.xml` permanece somente se o mapa for confirmado;
- `DrvModbus_RC_ICNT_PROBE.xml` é removido;
- `rapid_stage4_icnt.sh` é removido ou substituído por provisionamento genérico.

## Estrutura alvo atual

```text
scada/
├── app/
│   ├── controller_catalog.py
│   ├── db.py
│   ├── rapid_bridge.py
│   ├── rapid_scada.py
│   ├── web.py
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
│   ├── rapid_stage4_icnt.sh   # temporário
│   └── status.sh
├── systemd/
│   ├── rc-scada-web.service
│   └── rc-scada-rapid-bridge.service
├── docs/
├── nginx/
├── install.sh
└── requirements.txt
```

## Próxima decisão de limpeza

A próxima remoção só deve acontecer depois da InteliCompact NT ser concluída ou formalmente descartada. Até lá, os três artefatos de ICNT permanecem isolados e identificados como temporários.
