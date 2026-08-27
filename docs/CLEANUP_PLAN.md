# Limpeza do repositório

A arquitetura oficial do RC Geradores é:

```text
modem TCP Client
  -> RC Reverse Bridge
  -> Rapid SCADA Communicator
  -> Rapid SCADA Server
  -> painel RC
```

Antes da limpeza foi criado o branch de segurança:

```text
checkpoint/pre-cleanup-rapid-20260827
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

## Segunda limpeza concluída

Os componentes abaixo foram removidos do `main` porque pertenciam ao polling Python antigo ou eram scripts usados somente durante a migração para o Rapid SCADA:

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

O histórico continua preservado no Git e no branch de checkpoint.

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

## Revisar antes de remover

```text
app/profiles.py
app/profile_importer.py
docs/COMAP_PROFILES.md
```

Esses arquivos ainda são usados por partes do backend. A remoção exige primeiro retirar do painel/backend a camada antiga de perfil/importação e deixar templates/bindings do Rapid SCADA como fonte técnica dos pontos.

## GenMon

GenMon permanece fora deste Git, em `vendor/genmon`, como referência externa de perfis e nomenclatura. Ele não atua como mestre Modbus concorrente.

## Limpeza da VM

Após atualizar a VM para este `main`, o unit file legado pode continuar em `/etc/systemd/system` por ter sido instalado anteriormente. Remova somente o serviço legado com:

```bash
sudo systemctl disable --now rc-scada-gateway.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/rc-scada-gateway.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

Isso não afeta `rc-scada-rapid-bridge`, Rapid SCADA ou o painel.

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
