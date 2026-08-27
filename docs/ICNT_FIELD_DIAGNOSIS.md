# Diagnóstico de campo — ComAp InteliCompact NT

Data: 2026-08-27

## Situação atual

A InteliGen 200 no mesmo modem/barramento está estável no Rapid SCADA como Device 200 / Modbus Unit ID 2.

A InteliCompact NT ainda não foi homologada no Rapid SCADA.

## Testes realizados

### Unit ID 1

Probe somente leitura FC03 no offset 57 (registro 40058 conforme mapa provisório): sem resposta.

Resultado observado na bridge: timeout do Unit 1 e retorno Modbus 0x0B ao cliente local.

### Unit ID 4

Probe isolado e seguro, com o Rapid SCADA Communicator parado durante a requisição: sem resposta.

Resultado: a bridge retornou exceção 0x0B após timeout.

Após o probe, o Communicator foi religado e a InteliGen 200 voltou a `Normal`.

## Conclusão

Não existe evidência de que a InteliCompact NT esteja nos Unit IDs 1 ou 4.

Não deve ser feita varredura cega de Unit IDs nem escrita Modbus para descobrir endereço.

Antes de qualquer novo probe é necessário confirmar no equipamento/configuração:

- endereço Modbus/Controller Address da InteliCompact NT;
- protocolo Modbus RTU habilitado na porta usada;
- baud rate;
- paridade;
- stop bits;
- ligação física A/B e referência comum quando aplicável;
- se a porta serial usada pela InteliCompact é a mesma efetivamente conectada ao modem/barramento;
- se o modelo/firmware corresponde ao mapa de registradores provisório usado no probe.

## Regra para próxima etapa

Quando o Unit ID e os parâmetros seriais forem confirmados, usar `scripts/rapid_icnt_probe_unit.sh <unit_id>` para um único probe FC03 somente leitura.

Somente após uma resposta válida:

1. atualizar `scripts/rapid_stage4_icnt.sh` com o Unit ID confirmado;
2. validar o mapa completo somente leitura;
3. criar Device 201 e canais no Rapid SCADA;
4. validar os canais pelo Rapid SCADA Server;
5. só então considerar qualquer comando remoto específico do modelo.
