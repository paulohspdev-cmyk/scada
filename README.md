# RC Geradores SCADA

Plataforma central para monitorar grupos geradores **ComAp** e **Deep Sea Electronics (DSE)** através de modems configurados como **TCP Client**.

## O que já existe nesta base

- interface web RC Geradores;
- cadastro de vários geradores;
- porta TCP automática por equipamento (`15001+`);
- gateway TCP Server para conexões iniciadas pelos modems;
- Modbus RTU-over-TCP e Modbus TCP;
- polling somente leitura;
- SQLite para cadastro, telemetria e eventos;
- leitura em runtime dos perfis ComAp/DSE do GenMon;
- instalador automático da VM;
- instalação do Rapid SCADA Community;
- instalação separada do GenMon;
- serviços systemd e Nginx.

## Instalação na VM

Ubuntu/Debian:

```bash
curl -fsSL https://raw.githubusercontent.com/paulohspdev-cmyk/scada/main/install.sh | sudo bash
```

Depois:

```text
http://IP_DA_VM/
```

## Fluxo

```text
ComAp / DSE
    ↓
modem TCP Client
    ↓
IP público + porta individual
    ↓
RC Gateway
    ↓
telemetria / eventos
    ↓
Interface RC Geradores

Rapid SCADA fica instalado ao lado para assumir histórico, alarmística,
canais e funções industriais conforme os pontos reais forem validados.
```

## Importante

Esta é a **primeira versão funcional da fundação**, não a versão final de produção. Comandos de partida/parada estão propositalmente desativados. Antes de habilitar escrita em controladoras reais será necessário validar modelos, registradores, intertravamentos e auditoria.

O perfil DSE do GenMon declara teste com DSE 7320 MKII e contém itens ainda marcados como TODO; portanto DSE deve ser validado modelo a modelo.

Veja:
- `docs/ARCHITECTURE.md`
- `docs/DEPLOY.md`

## Projetos externos

Rapid SCADA e GenMon **não são incorporados ao código deste repositório**. O instalador baixa os projetos/pacotes oficiais separadamente para preservar a separação técnica e de licenças.
