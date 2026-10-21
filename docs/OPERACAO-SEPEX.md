# Operação na SEPEX

## Antes de abrir

1. Instale dependências e defina `SEPEX_ADMIN_TOKEN` e `SEPEX_SECRET_KEY` no ambiente do processo. Não coloque segredos em arquivos versionados.
2. A cópia do repositório já inclui o banco com 108 CSVs importados e placar vazio. Em um banco novo, execute `init-db`, `seed-configuracoes` e `importar-lote "Foguete Modular - Banco/gerados/csv" --condicao "OpenRocket 24.12 - lote automatizado preliminar"`; preencha a condição com `condicao-configurar`, usando os parâmetros documentados do modelo. Depois de ensaios no banco de operação, execute `preparar-evento data/exports/backup-antes-evento.sqlite3` com um nome de backup ainda não usado. O comando preserva os 108 voos e remove todas as tentativas e demonstrações, após guardar o histórico.
3. Execute `python -m flask --app run verificar-prontidao` com as variáveis de administração definidas. Abra `/diagnostico`: 108/108 voos com gráficos, integridade `ok`, zero referências órfãs e zero tentativas de demonstração. Não há dispositivo de recuperação no modelo por decisão do projeto. Configurações com estabilidade inferior a 0,10 calibre iniciam a animação, são abortadas e não entram no ranking.
4. Faça backup inicial. Abra montagem, voo, resultado, ranking e dashboard no navegador do evento.

## Servidor e quiosque

Por padrão `python run.py` escuta apenas em `127.0.0.1:5000`. No Windows, execute `./iniciar-rede.ps1` para aceitar celulares na rede local e mostrar os endereços de acesso. O script usa Waitress. Em outros sistemas, execute `python servir.py` com `SEPEX_HOST=0.0.0.0` e descubra o IPv4 local do computador. Conecte computador e celulares à mesma rede Wi-Fi; libere a porta escolhida (`SEPEX_PORT`) no firewall e verifique se a rede permite comunicação entre clientes. Teste no celular `http://IP-DO-COMPUTADOR:5000/montagem`, registre uma tentativa e abra o voo, resultado e ranking. O endereço `127.0.0.1` só funciona no próprio computador. Para tela cheia, use F11 ou inicialize Chrome/Edge com `--kiosk http://127.0.0.1:5000`. Desative suspensão automática do computador e mantenha alimentação estável.

Para visitantes fora do Wi-Fi, configure `SEPEX_ADMIN_TOKEN` e `SEPEX_SECRET_KEY` e execute `./iniciar-internet.ps1`. A administração será restrita a `127.0.0.1`. Descubra o IPv4 local com `Get-NetIPAddress -AddressFamily IPv4`. Na rede do evento, peça à TI para liberar a porta TCP escolhida no firewall e encaminhá-la do IP público ao IPv4 do computador. Se a máquina estiver atrás de CGNAT ou a rede do campus bloquear portas de entrada, acesso direto por IP público depende de configuração da TI ou de um proxy/túnel. Confirme com o Wi-Fi desligado em um celular: `http://IP-PUBLICO:5000`. O IP mostrado pelo script é apenas uma indicação, não prova de acesso externo. Para disponibilização aberta na internet, configure HTTPS na frente do serviço; HTTP transmite os dados sem criptografia.

## Durante e após o evento

Execute backups periódicos: `python -m flask --app run backup-db data/exports/backup-AAAA-MM-DD-HHMM.sqlite3`. Copie o arquivo resultante para mídia separada. Não copie apenas o `.sqlite3` ativo enquanto WAL estiver em uso. Exporte `python -m flask --app run exportar-tentativas data/exports/tentativas.csv` ou use `/admin/exportar`. O CSV contém somente apelido, configuração, horários e indicadores, sem dados pessoais adicionais. Proteja o backup e elimine-o conforme a política da equipe.

O CSV exportado identifica cada tentativa como `classificada` ou `abortada`; abortadas têm posição vazia. Se houver reinicialização, execute novamente o script usado para iniciar o servidor; tentativas confirmadas permanecem no SQLite. Uma solicitação repetida com o mesmo identificador de sessão devolve a tentativa existente. Em falhas, consulte `instance/sepex.log` e `/diagnostico`; restaure o último backup apenas após preservar uma cópia do banco problemático.
