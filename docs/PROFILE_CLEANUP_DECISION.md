# Decisão de limpeza da camada de perfis Python

Data: 2026-08-27

A telemetria do produto não deve mais depender de perfis Modbus executados pelo backend Python.

## Decisão

- Rapid SCADA é a única fonte industrial de polling e canais.
- `rapid/templates/` contém os mapas de controladoras realmente homologados.
- `rapid/bindings.json` liga os canais do Rapid SCADA às métricas do painel RC.
- O catálogo do painel guarda somente fabricante, família, modelo e aliases.
- Importação de mapa Modbus pelo painel foi removida.
- GenMon deixa de ser dependência de runtime e de instalação. Pode continuar sendo consultado externamente durante pesquisa de novos modelos, mas não é clonado pela VM de produção.
- A tabela SQLite `generator_profiles`, quando existir em uma base antiga, pode permanecer fisicamente sem uso. Não é necessária migração destrutiva do banco para esta limpeza.

## Arquivos removidos

```text
app/profiles.py
app/profile_importer.py
docs/COMAP_PROFILES.md
```

## Resultado

O fluxo técnico de telemetria fica único e explícito:

```text
controladora -> modem -> RC Reverse Bridge -> Rapid SCADA -> painel RC
```

Novos modelos entram somente depois de um template do Rapid SCADA ser validado e seus canais serem vinculados.
