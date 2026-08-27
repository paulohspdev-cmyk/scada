# Biblioteca de perfis ComAp

## Regra do RC SCADA

O cadastro usa **Fabricante + Modelo** para escolher a estratégia de comunicação. O sistema nunca faz varredura de escrita e nunca ativa comandos remotos ao importar um mapa.

Estados de perfil:

- `PERFIL RC VALIDADO`: pontos já validados em campo e carregados automaticamente;
- `IMPORTAR MAPA`: controladora com mapa configurável por aplicação; exportar do InteliConfig;
- `MAPA LEGADO`: importar mapa do LiteEdit/GenConfig ou mapa confirmado no Communication Guide;
- `REFERÊNCIA`: perfil externo de referência que ainda exige validação de campo.

Um mapa importado é armazenado por gerador porque a aplicação/firmware pode alterar o mapeamento. O gateway aceita somente funções Modbus de **leitura 03 e 04**. Pontos de escrita nunca são executados pelo importador.

## Importação

Formatos aceitos: `.csv`, `.txt`, `.tsv` e `.json`.

O importador reconhece variações comuns de colunas como:

- Address / Register / Offset / Endereço;
- Name / Parameter / Description / Nome;
- Data Type / Tipo de dado;
- Access / R/W / Acesso;
- Function / FC / Função;
- Scale / Resolution / Factor / Fator;
- Unit / Unidade;
- Count / Length / Registros.

Endereços documentais `4xxxx` são convertidos para offset zero-based de Holding Register e `3xxxx` para Input Register. Linhas de faixa agregada devem ser exportadas como pontos individuais para evitar ambiguidade.

O RC SCADA ativa automaticamente apenas telemetria reconhecida (RPM, tensões, frequência, correntes, bateria, óleo, temperatura, combustível, potência, horas e estados). Outros objetos ficam armazenados para revisão, mas não entram no polling automático.

## Perfil validado no projeto

### InteliGen 200

Pontos atualmente homologados em campo:

| Grandeza | Endereço | FC | Escala |
|---|---:|---:|---:|
| RPM | 1000 | 03 | 1 |
| Tensão L1-N | 1036 | 03 | 1 |
| Tensão L2-N | 1037 | 03 | 1 |
| Tensão L3-N | 1038 | 03 | 1 |
| Tensão L1-L2 | 1039 | 03 | 1 |
| Tensão L2-L3 | 1040 | 03 | 1 |
| Tensão L3-L1 | 1041 | 03 | 1 |
| Frequência | 1045 | 03 | 0.01 |

## Referência fornecida para biblioteca

A planilha de referência usada no projeto contém, entre outros, os seguintes endereços documentais ComAp. Eles são **referência**, não perfil ativo automático, porque o mapa pode variar por família/aplicação:

| Registro documental | Offset informado | Descrição |
|---|---:|---|
| 40003 | 40002 | Entradas binárias |
| 40012 | 40011 | Saídas binárias |
| 40013 | 40012 | Tensão da bateria |
| 40014 | 40013 | Temperatura da CPU |
| 40051 | 40050 | Tensão da bateria alternativa IL-NT |
| 40054 | 40053 | Pressão do óleo |
| 40055 | 40054 | Temperatura do motor |
| 40056 | 40055 | Nível de combustível |
| 40060-40062 | 40059-40061 | Tensões de fase |
| 40063-40065 | 40062-40064 | Correntes de fase |
| 40066 | 40065 | Frequência do gerador |
| 40070 | 40069 | Potência ativa |
| 40072 | 40071 | Fator de potência |
| 40080-40081 | 40079-40080 | Energia ativa acumulada |
| 40090 | 40089 | Horas de operação |

Esses endereços não são usados automaticamente pela InteliCompact NT ou InteliLite NT até o mapa do equipamento ser confirmado/importado.

## Fontes oficiais para manutenção do catálogo

- Catálogo ComAp Controllers: https://www.comap-control.com/products/controllers/
- InteliLite 4 AMF 25 (Global Guide + InteliConfig): https://www.comap-control.com/products/controllers/single-gen-set-controllers/intelilite/intelilite-4-amf-25/
- InteliGen 200 (Global Guide + InteliConfig): https://www.comap-control.com/products/controllers/paralleling-gen-set-controllers/inteligen/inteligen-200/
- InteliGen4 200: https://www.comap-control.com/products/controllers/paralleling-gen-set-controllers/inteligen/inteligen4-200/
- InteliCompact NT MINT (inclui `IL-NT IA-NT IC-NT Communication Guide`): https://www.comap-control.com/products/controllers/paralleling-gen-set-controllers/intelicompact/intelicompact-nt-mint/

## Segurança

Esta biblioteca é somente leitura. Start, Stop, Reset, transferência de carga, alteração de setpoints e qualquer FC de escrita ficam fora do importador e só poderão ser implementados em um módulo separado com permissões, intertravamentos, confirmação e auditoria.
