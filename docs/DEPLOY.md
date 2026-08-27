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
- banco SQLite do produto;
- cliente `ScadaClient` usado pelo painel para ler o Rapid SCADA Server;
- GenMon como referência externa.

O instalador **não ativa o antigo `rc-scada-gateway`**. Esse serviço pertence à arquitetura anterior e permanece no Git apenas até a limpeza final.

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

O cadastro do gerador no painel define porta e Unit ID. A criação de Device Templates e canais do Rapid SCADA continua sendo feita por automação específica do modelo enquanto o provisionamento genérico não estiver concluído.

Não trate um modelo como compatível apenas porque a conexão TCP abriu. O mapa Modbus deve ser validado antes de criar canais definitivos.

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

O comando disponível para o modelo já validado é:

```bash
sudo /opt/rc-scada/bin/rc-generator start --device 200 --confirm
sudo /opt/rc-scada/bin/rc-generator stop  --device 200 --confirm
```

A habilitação do controle é propositalmente opt-in e não deve ser generalizada para novos modelos sem validação.

## Atualização de uma VM existente

```bash
cd /opt/rc-scada
sudo git pull --ff-only
sudo systemctl restart rc-scada-web
```

Não use `git reset --hard` em uma VM com alterações locais sem antes revisar/stashar essas mudanças.

## Segurança e recuperação

Antes desta reorganização foi criado o branch:

```text
checkpoint/pre-cleanup-rapid-20260827
```

Ele preserva o estado anterior à limpeza documental/estrutural. O plano de arquivos a manter e remover está em `docs/CLEANUP_PLAN.md`.
