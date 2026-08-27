# RC Controller Library

A biblioteca de controladoras é a fonte organizada de conhecimento dos equipamentos suportados pelo RC Geradores.

## Separação

- `controllers/`: somente pacotes homologados para produção.
- `lab/controllers/`: modelos ainda em investigação ou validação.
- `transports/`: formas de conexão independentes do modelo da controladora.
- `rapid/`: templates, bindings e reader usados pelo Rapid SCADA.

## Controller Pack

Cada modelo recebe um `manifest.json` com fabricante, família, modelo, aliases, estado de homologação, transportes permitidos, capacidades liberadas, telemetria e referência ao template Rapid SCADA quando aplicável.

Estados sugeridos:

- `reference`
- `official_doc`
- `lab_validated`
- `field_validated`
- `production`
- `investigation`

Uma controladora pode existir no catálogo sem estar liberada para operação. O painel deve diferenciar claramente produção e laboratório.

## Fontes

Ordem de confiança para novos pacotes:

1. documentação oficial do fabricante;
2. validação em bancada/campo RC;
3. projetos open source como GenMon como referência auxiliar;
4. outras fontes técnicas, sempre marcadas como não homologadas.

GenMon não é dependência de runtime da VM. Pode ser usado como fonte de pesquisa/importação para acelerar a criação de packs, mas nenhum registrador ou comando vira produção sem validação.

## Transportes

O protocolo da controladora é separado do caminho físico/rede. O mesmo Controller Pack pode ser usado com:

- modem TCP Client / reverse TCP;
- Modbus TCP direto, normalmente porta 502;
- Modbus RTU sobre gateway TCP/RS485;
- serial RTU local;
- Modbus TCP por VPN.

A RC Reverse Bridge é usada apenas quando o campo inicia a sessão TCP. Conexões Modbus TCP diretas devem ser feitas nativamente pelo Rapid SCADA.

## Comandos

Capacidades de controle são opt-in por modelo. START, STOP, AUTO, MANUAL, TEST, MCB, GCB e paralelismo são liberados independentemente.

Botões no painel só podem executar comandos quando o Controller Pack estiver homologado e a camada de segurança tiver autenticação, autorização, confirmação, intertravamentos, validação do retorno e auditoria.
