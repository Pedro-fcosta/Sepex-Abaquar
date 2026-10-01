# Operação na SEPEX

## Antes de abrir

1. Instale dependências e defina `SEPEX_ADMIN_TOKEN` e `SEPEX_SECRET_KEY` no ambiente do processo. Não coloque segredos em arquivos versionados.
2. Execute `init-db`, `seed-configuracoes`, `importar-lote "Foguete Modular - Banco/.csv"`, `verificar-cobertura` e os testes. Os 21 CSVs existentes ficam disponíveis. Importe as outras configurações quando os respectivos CSVs estiverem prontos. Execute `demo-limpar` se quiser operar somente com resultados do OpenRocket.
3. Abra `/diagnostico`: configurações 108, integridade `ok`, quantidade de simulações disponíveis esperada.
4. Faça backup inicial. Abra montagem, voo, resultado, ranking e dashboard no navegador do evento.

## Servidor e quiosque

Por padrão `python run.py` escuta apenas em `127.0.0.1:5000`. Para outros dispositivos na rede local, defina `SEPEX_HOST=0.0.0.0` e libere a porta escolhida (`SEPEX_PORT`) no firewall da rede do evento. Use somente rede confiável; o servidor Flask embutido é adequado para esse MVP local com baixa concorrência, não para exposição pública. Para tela cheia, use F11 ou inicialize Chrome/Edge com `--kiosk http://127.0.0.1:5000`. Desative suspensão automática do computador e mantenha alimentação estável.

## Durante e após o evento

Execute backups periódicos: `python -m flask --app run backup-db data/exports/backup-AAAA-MM-DD-HHMM.sqlite3`. Copie o arquivo resultante para mídia separada. Não copie apenas o `.sqlite3` ativo enquanto WAL estiver em uso. Exporte `python -m flask --app run exportar-tentativas data/exports/tentativas.csv` ou use `/admin/exportar`. O CSV contém somente apelido, configuração, horários e indicadores, sem dados pessoais adicionais. Proteja o backup e elimine-o conforme a política da equipe.

Se houver reinicialização, execute novamente `python run.py`; tentativas confirmadas permanecem no SQLite. Uma solicitação repetida com o mesmo identificador de sessão devolve a tentativa existente. Em falhas, consulte `instance/sepex.log` e `/diagnostico`; restaure o último backup apenas após preservar uma cópia do banco problemático.
