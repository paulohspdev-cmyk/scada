# Deploy na VM

Recomendado: Ubuntu 24.04 LTS, VM com IP estável e acesso administrativo.

## Instalação

```bash
curl -fsSL https://raw.githubusercontent.com/paulohspdev-cmyk/scada/main/install.sh | sudo bash
```

Depois abra:

```text
http://IP_DA_VM/
```

## O que a instalação ativa

A instalação atual prepara:

- Rapid SCADA Server, Communicator, Webstation e Agent quando disponíveis;
- RC Reverse TCP Bridge;
- painel RC Geradores;
- Nginx;
- banco SQLite de cadastro/eventos do produto;
- cliente `ScadaClient` usado pelo painel para ler o Rapid SCADA Server.

Não instala nem ativa o antigo `rc-scada-gateway`. GenMon também não é dependência de produção e não é clonado pelo instalador.

## Fluxo de comunicação

```text
Controladora -> modem TCP Client -> porta pública da VM
            -> RC Reverse Bridge -> localhost:porta+10000
            -> Rapid SCADA Communicator -> Rapid SCADA Server
            -> painel RC
```

Exemplo já validado:

```text
modem -> :15001 -> bridge -> 127.0.0.1:25001 -> Rapid SCADA
```

## Cadastro e provisionamento

O cadastro do gerador no painel define porta e Unit ID.

A compatibilidade técnica não é determinada pelo cadastro. Para cada modelo é necessário:

1. validar comunicação somente leitura;
2. criar/validar o Device Template em `rapid/templates/`;
3. criar/vincular canais no Rapid SCADA Server;
4. adicionar o binding do painel em `rapid/bindings.json`.

Não trate um modelo como compatível apenas porque a conexão TCP abriu.

## Diagnóstico

```bash
sudo /opt/rc-scada/scripts/status.sh
sudo /opt/rc-scada/scripts/rapid_probe.sh
```

Logs principais:

```bash
sudo journalctl -u rc-scada-rapid-bridge -f
sudo journalctl -u scadacomm6 -f
sudo journalctl -u scadaserver6 -f
sudo journalctl -u rc-scada-web -f
```

Para uma linha específica do Rapid SCADA:

```bash
sudo tail -f /var/log/scada/ScadaComm/Log/line100.log
```

## Controle remoto

O caminho normal do Rapid SCADA é somente leitura. Controle remoto é instalado separadamente:

```bash
sudo /opt/rc-scada/scripts/rapid_control_install.sh
```

Comandos do modelo já validado:

```bash
sudo /opt/rc-scada/bin/rc-generator start --device 200 --confirm
sudo /opt/rc-scada/bin/rc-generator stop  --device 200 --confirm
```

A habilitação do controle é propositalmente opt-in e não deve ser generalizada para novos modelos sem validação.

## Atualização de uma VM existente

```bash
cd /opt/rc-scada
sudo git pull --ff-only
sudo systemctl restart rc-scada-web rc-scada-rapid-bridge
```

Não use `git reset --hard` em uma VM com alterações locais sem antes revisar/stashar essas mudanças.

## Limpeza de instalações antigas

Se a VM foi criada antes da remoção do gateway legado:

```bash
sudo systemctl disable --now rc-scada-gateway.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/rc-scada-gateway.service
sudo systemctl daemon-reload
```

Se existir `/opt/rc-scada/vendor/genmon` de uma instalação antiga, ele pode ser removido depois de atualizar para o `main` atual, porque o runtime não o utiliza mais:

```bash
sudo rm -rf /opt/rc-scada/vendor/genmon
```

## Segurança e recuperação

Branches de recuperação criados durante a reorganização:

```text
checkpoint/pre-cleanup-rapid-20260827
checkpoint/pre-profile-cleanup-20260827
```

As decisões de limpeza estão documentadas em `docs/CLEANUP_PLAN.md` e `docs/PROFILE_CLEANUP_DECISION.md`.
