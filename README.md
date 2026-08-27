# RC Geradores SCADA

Plataforma central para monitoramento e controle supervisionado de grupos geradores **ComAp** e, progressivamente, **Deep Sea Electronics (DSE)** conectados por modems configurados como **TCP Client**.

## Arquitetura oficial

O Rapid SCADA é o SCADA principal do sistema. O código Python próprio não atua mais como mestre Modbus de telemetria.

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
   somente transporte
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

- **RC Reverse TCP Bridge**: recebe a conexão TCP iniciada pelo modem e a entrega ao Rapid SCADA em uma porta local. Serializa o acesso quando vários Unit IDs compartilham a mesma sessão física.
- **Rapid SCADA Communicator**: executa o polling Modbus das controladoras.
- **Rapid SCADA Server**: mantém os canais e dados atuais; é a fonte de telemetria para o painel RC.
- **Painel RC Geradores**: cadastro, visualização, status e integração operacional.
- **Controle remoto**: separado do caminho normal de polling. Escritas Modbus genéricas continuam bloqueadas; somente comandos explicitamente implementados e validados podem ser habilitados.
- **GenMon**: permanece como referência externa de perfis e documentação de controladoras. Não é um segundo mestre Modbus concorrente.

## Estado validado em campo

### ComAp InteliGen 200

- reverse TCP pelo modem;
- Modbus Unit ID 2;
- polling pelo Rapid SCADA;
- canais atuais lidos pelo Rapid SCADA Server;
- painel RC consumindo o Rapid SCADA Server;
- START/STOP remoto implementado por caminho privilegiado e restrito;
- caminho TCP do Rapid SCADA continua limitado a leitura FC03/FC04.

### ComAp InteliCompact NT

Integração ainda em validação. Os arquivos de probe e o script de etapa 4 permanecem temporariamente no repositório até a validação de campo ser concluída.

## Instalação

Ubuntu 24.04 LTS ou Debian compatível:

```bash
curl -fsSL https://raw.githubusercontent.com/paulohspdev-cmyk/scada/main/install.sh | sudo bash
```

Depois:

```text
http://IP_DA_VM/
```

A instalação nova ativa a arquitetura atual: **Rapid SCADA + RC Reverse Bridge + painel web**. O antigo `rc-scada-gateway` não é mais habilitado pelo instalador.

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
scripts/    instalação, diagnóstico, provisionamento e migrações temporárias
systemd/    serviços atuais
docs/       arquitetura, deploy, perfis e plano de limpeza
```

Os scripts `rapid_stage1_*`, `rapid_stage2_*` e `rapid_stage3_*` são históricos da migração e estão marcados para remoção em uma segunda limpeza. Antes da reorganização foi criado o branch de segurança `checkpoint/pre-cleanup-rapid-20260827`.

Veja também:

- `docs/ARCHITECTURE.md`
- `docs/DEPLOY.md`
- `docs/CLEANUP_PLAN.md`
