# RC Geradores SCADA

Plataforma central para monitoramento e controle supervisionado de grupos geradores **ComAp** e, progressivamente, **Deep Sea Electronics (DSE)** conectados por modems configurados como **TCP Client**.

## Arquitetura oficial

O Rapid SCADA é o SCADA principal. O Python próprio não executa polling industrial de telemetria.

```text
Controladora ComAp / DSE
        |
      RS485
        |
      Modem
   TCP Client
        |
        v
RC Reverse TCP Bridge
        |
        v
Rapid SCADA Communicator
   Modbus / polling
        |
        v
Rapid SCADA Server
 canais / estado / histórico / alarmes
        |
        +-------------------+
        |                   |
        v                   v
Painel RC Geradores   Controle autorizado
                      por ação específica
```

### Responsabilidades

- **RC Reverse TCP Bridge**: recebe a conexão iniciada pelo modem e entrega a sessão ao Rapid SCADA em localhost. Também serializa o acesso quando vários Unit IDs compartilham a mesma sessão física.
- **Rapid SCADA Communicator**: é o mestre Modbus e executa o polling das controladoras homologadas.
- **Rapid SCADA Server**: é a fonte oficial dos dados atuais e das funções industriais.
- **Painel RC Geradores**: cadastro, visualização, status e operação.
- **Controle remoto**: separado do caminho normal de polling. Escritas genéricas continuam bloqueadas; somente comandos específicos, implementados e validados podem ser habilitados.

## Fonte dos mapas e métricas

O backend Python não possui mais uma camada própria de perfis Modbus.

- mapas homologados ficam em `rapid/templates/`;
- canais usados pelo painel ficam em `rapid/bindings.json`;
- novos modelos só entram no runtime depois de validação no Rapid SCADA;
- GenMon não é dependência de produção nem é clonado pelo instalador. Pode ser consultado externamente apenas como material de pesquisa quando necessário.

## Estado validado em campo

### ComAp InteliGen 200

- reverse TCP pelo modem;
- Modbus Unit ID 2;
- polling pelo Rapid SCADA;
- canais atuais lidos pelo Rapid SCADA Server;
- painel RC consumindo o Rapid SCADA Server;
- START/STOP remoto implementado por caminho privilegiado e restrito;
- caminho TCP do Rapid SCADA limitado a leitura FC03/FC04.

### ComAp InteliCompact NT

Integração ainda em validação. Os arquivos de probe e o script de etapa 4 permanecem temporariamente até a validação de campo ser concluída.

## Instalação

Ubuntu 24.04 LTS ou Debian compatível:

```bash
curl -fsSL https://raw.githubusercontent.com/paulohspdev-cmyk/scada/main/install.sh | sudo bash
```

Depois:

```text
http://IP_DA_VM/
```

A instalação nova ativa **Rapid SCADA + RC Reverse Bridge + painel web**. O antigo `rc-scada-gateway` não faz mais parte do repositório nem do instalador.

## Diagnóstico

```bash
sudo /opt/rc-scada/scripts/status.sh
sudo /opt/rc-scada/scripts/rapid_probe.sh
```

## Controle remoto da InteliGen 200

O controle é opt-in. Primeiro:

```bash
sudo /opt/rc-scada/scripts/rapid_control_install.sh
```

Depois, somente quando a operação remota estiver autorizada e as condições locais forem seguras:

```bash
sudo /opt/rc-scada/bin/rc-generator start --device 200 --confirm
sudo /opt/rc-scada/bin/rc-generator stop  --device 200 --confirm
```

Não libere FC06/FC16 genericamente na porta usada pelo Rapid SCADA.

## Organização do repositório

```text
app/        bridge, integração Rapid SCADA, backend e interface
bin/        comandos administrativos/operacionais restritos
rapid/      bindings, templates e cliente do Rapid SCADA Server
scripts/    instalação, diagnóstico e provisionamento ainda necessário
systemd/    serviços atuais
docs/       arquitetura, deploy e decisões técnicas
```

Branches de recuperação criados durante a limpeza:

```text
checkpoint/pre-cleanup-rapid-20260827
checkpoint/pre-profile-cleanup-20260827
```

Veja também:

- `docs/ARCHITECTURE.md`
- `docs/DEPLOY.md`
- `docs/CLEANUP_PLAN.md`
- `docs/PROFILE_CLEANUP_DECISION.md`
