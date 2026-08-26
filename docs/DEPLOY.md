# Deploy na VM

Recomendado: Ubuntu 24.04 LTS ou Debian atual, VM com IP estável.

## Instalação com um comando

```bash
curl -fsSL https://raw.githubusercontent.com/paulohspdev-cmyk/scada/main/install.sh | sudo bash
```

Depois abra:

```text
http://IP_DA_VM/
```

## Primeiro gerador

1. Clique em **Adicionar gerador**.
2. Informe `COMAP` ou `DSE`.
3. Se deixar porta vazia, recebe `15001`, `15002`, etc.
4. Configure o modem em **TCP Client** apontando para `IP_DA_VM:PORTA`.
5. Se usar serial no lado da controladora, configure baud/paridade/stop bits no modem de acordo com a controladora.
6. Escolha no cadastro se o fluxo é `Modbus RTU sobre TCP` ou `Modbus TCP`.

## Diagnóstico

```bash
sudo /opt/rc-scada/scripts/status.sh
sudo journalctl -u rc-scada-gateway -f
sudo journalctl -u rc-scada-web -f
sudo journalctl -u scadacomm6 -f
```

Ver portas:

```bash
sudo ss -lntp
```

## Observação sobre Rapid SCADA

Rapid SCADA 6 no Linux executa Server, Communicator e Webstation, porém o Administrator nativo normalmente é usado a partir de Windows. O nosso produto evita exigir o Administrator para o cadastro diário; a automação de provisionamento de templates será adicionada após validar ComAp e DSE reais.
