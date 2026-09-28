# Arquitetura

Flask + Jinja2 + JavaScript sem compilação. SQLite é o único armazenamento persistente. O processo atende localmente; OpenRocket é usado apenas antes do evento.

`app/db.py` cria sete tabelas: `componentes`, `configuracoes`, `condicoes`, `simulacoes`, `pontos`, `participantes`, `tentativas`. Chaves estrangeiras impedem referências órfãs; `hash_arquivo` + configuração impedem duplicação de importação; `identificador_sessao` impede duplicação de envio. Conexões por requisição usam WAL, timeout e fechamento automático. O backup usa `sqlite3.Connection.backup` para incluir transações ainda no WAL.

`app/catalogo.py` define as opções, código determinístico e seed. `app/simulacoes.py` faz leitura, normalização SI e revisão. `app/tentativas.py` aceita apenas simulação aprovada e grava snapshot dos indicadores. `app/estatisticas.py` consulta exclusivamente tentativas registradas. `app/web.py` expõe páginas, APIs e administração; `app/cli.py` mantém tarefas de operação. Arquivos JS separam seleção, animação e gráficos.

Fluxo de dados: CSV → importação pendente → revisão → simulação aprovada → tentativa com snapshot → ranking/dashboard/exportação. A animação usa pontos temporais quando presentes; na ausência deles, gera apenas posições visuais no navegador. Ela nunca escreve resultados no banco.

O esquema é criado por `init-db`; mudanças futuras de estrutura devem receber migrações antes de atualizar um banco com dados da SEPEX. Nomes técnicos das colunas usam português com sufixos de unidade. `demonstrativo=1` marca simulações e tentativas sintéticas.
