# ABAQUAR · SEPEX 2026

Experiência local de montagem digital de foguetes modulares para a SEPEX 2026. O visitante escolhe peças, acompanha gráficos animados de altura × tempo e velocidade × tempo de uma simulação importada e entra no ranking. O programa não executa OpenRocket durante o atendimento e funciona sem internet.

## Começo rápido

Requer Python 3.12. O repositório já inclui `instance/sepex.sqlite3` com as 108 configurações e os voos importados. No Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SEPEX_ADMIN_TOKEN = 'defina-um-token-longo'
$env:SEPEX_SECRET_KEY = 'defina-outra-chave-longa'
python run.py
```

Abra `http://127.0.0.1:5000`. O banco incluído já permite testar montagem, gráficos e resultado nas 108 combinações. Os 108 modelos `.ork` e CSVs gerados ficam em `Foguete Modular - Banco/gerados`; os 21 pares originais permanecem em `.ork` e `.csv`. O OpenRocket concluiu 106 voos e interrompeu 2. A estabilidade inferior a **0,15 calibre** aborta a missão após o começo dos gráficos, sem registrar apogeu válido ou posição no ranking. A tentativa continua no histórico e no total de participações do dashboard. O modelo não possui dispositivo de recuperação por decisão do projeto. Para começar com um banco vazio, remova `instance/sepex.sqlite3`, execute `init-db`, `seed-configuracoes` e importe `Foguete Modular - Banco/gerados/csv`.

O histórico dos ensaios anteriores está preservado em `data/exports/backup-antes-preparo-sepex-2026.sqlite3`; o banco ativo entregue para o evento está sem participantes e sem tentativas.

### Acesso pelos celulares durante a feira

No computador do evento, conectado à mesma rede Wi-Fi dos visitantes, execute `./iniciar-rede.ps1` no PowerShell após instalar as dependências. O script inicia o servidor para a rede local e mostra os endereços `http://IP:5000` que podem ser abertos no navegador dos celulares. Compartilhe o endereço da conexão usada pelos visitantes. Se não abrir, libere a porta 5000 no firewall do computador e desative o isolamento entre clientes da rede Wi-Fi. O acesso não depende de internet, mas os aparelhos precisam alcançar o computador na rede local. Cada visitante pode voltar a **Montagem** para fazer novas participações.

No Linux/macOS, substitua `py -3.12` por `python3.12`, ative com `source .venv/bin/activate` e defina variáveis com `export`. Para aceitar celulares na rede, execute `python servir.py` com `SEPEX_HOST=0.0.0.0` e compartilhe o IP local do computador.

### Acesso pela internet

Defina `SEPEX_ADMIN_TOKEN` e `SEPEX_SECRET_KEY` com valores fortes e execute `./iniciar-internet.ps1` no computador que hospeda o programa. O script usa Waitress, escuta em `0.0.0.0:5000` (ou `SEPEX_PORT`), mostra o IP público consultado e restringe a administração ao próprio computador. O endereço que os visitantes abrirão é `http://IP-PUBLICO:5000`. **O script sozinho não torna a porta pública**: o roteador precisa encaminhar a porta TCP ao IPv4 local do computador e o firewall deve permiti-la. Teste de um celular com Wi-Fi desligado, usando dados móveis. Redes de campus podem bloquear conexões de entrada ou usar CGNAT; nesse caso, solicite à TI um IP público alcançável e o encaminhamento ou um proxy/túnel gerenciado. Para uso aberto na internet, coloque HTTPS na frente do servidor. O endereço informado é uma possibilidade até ser testado externamente.

## Configurações e dados

São 3 coifas (`C1` cônica, `C2` ogival, `C3` elipsoidal) × 3 formas de aleta (`A1` trapezoidal reta, `A2` enflechada, `A3` elíptica) × 3 quantidades (3–5) × 4 seções (1–4) = **108** combinações. `C2-A3-F4-S2` tem quatro aletas e corpo de 40 cm. `seed-configuracoes` é idempotente. O comprimento do corpo é `seções × 200 mm`; a coifa fica separada dessa medida.

Os valores de partida são configuráveis pelas variáveis `SEPEX_*` de [.env.example](.env.example), antes do seed. As medidas padrão do catálogo acompanham os ORKs gerados: aletas de 3 mm de espessura, 30 mm de envergadura e corda de 70 mm em A1/A2 ou 64 mm em A3. Esses valores descrevem o modelo atual; as peças físicas e o local do evento ainda precisam ser medidos para comparar resultados simulados com lançamentos reais. Alterar parâmetros após o seed requer atualizar as linhas existentes ou recriar um banco vazio; o seed preserva registros existentes. Consulte [pendências técnicas](docs/PENDENCIAS-TECNICAS.md).

## Comandos

```powershell
python -m flask --app run init-db
python -m flask --app run seed-configuracoes
python -m flask --app run importar-csv C2-A3-F4-S2 caminho\voo.csv --condicao "Condição SEPEX 2026"
python -m flask --app run importar-lote "Foguete Modular - Banco/.csv"
python -m flask --app run importar-lote "Foguete Modular - Banco/gerados/csv" --condicao "OpenRocket 24.12 - lote automatizado preliminar"
python -m flask --app run pendentes
python -m flask --app run revisar 1 approved
python -m flask --app run revisar 1 rejected
python -m flask --app run condicao-configurar "Condição SEPEX 2026" --motor "motor validado" --temperatura-c 25 --pressao-pa 101325
python -m flask --app run verificar-cobertura
python -m flask --app run demo-criar
python -m flask --app run demo-limpar
python -m flask --app run preparar-evento data\exports\backup-antes-evento.sqlite3
python -m flask --app run verificar-prontidao
python -m flask --app run exportar-tentativas data\exports\tentativas.csv
python -m flask --app run backup-db data\exports\backup.sqlite3
python -m pytest -q
```

Também há interface administrativa em `/admin/entrar` com o token de `SEPEX_ADMIN_TOKEN`. As rotas de escrita e exportação administrativas exigem esse token. Sem token configurado, elas ficam bloqueadas. O login web usa sessão assinada e token de formulário. Configure `SEPEX_SECRET_KEY` estável para preservar sessões entre reinicializações. `iniciar-internet.ps1` ativa `SEPEX_ADMIN_LOCAL_ONLY=1`, bloqueando administração por IP remoto; acesse a administração em `http://127.0.0.1:5000` no computador do evento.

O CSV importado fica disponível imediatamente. Uma nova versão da mesma configuração substitui a versão ativa anterior; tentativas antigas preservam os números registrados. O hash SHA-256 do arquivo e a configuração tornam a importação idempotente. O importador lê cabeçalhos comuns em português/inglês, CSV de resumo ou série temporal, converte unidades para SI e salva as unidades originais. Consulte [guia do OpenRocket](docs/OPENROCKET.md). Os CSV em `data/examples` são **exemplos artificiais de formato**, não simulações reais.

O gerador `python -m scripts.gerar_108_openrocket --importar` cria os 108 modelos e CSVs, faz backup do banco e importa o lote. Requer [OpenRocket 24.12](https://openrocket.info/downloads.html?vers=latest) instalado; no Windows, usa automaticamente o Java que acompanha o instalador. Também aceita `OPENROCKET_JAR` e `OPENROCKET_JAVA` para caminhos personalizados. A geração usa os 21 `.ork` originais como modelos, 25 g de lastro na coifa e vento constante de 2 m/s, sem turbulência, para repetir os resultados. O lote usa motor Estes D12, haste de 1 m e atmosfera ISA, e registra esses dados na condição do banco. As coordenadas nos modelos são de referência e não representam um local medido no CEFET. A confirmação com as peças e condições reais é uma tarefa de medição, não um requisito para operar a experiência digital. O manifesto em `Foguete Modular - Banco/gerados/manifesto.json` registra a origem e o status de cada voo. Duas simulações foram interrompidas antes do pouso: `C2-A1-F3-S1` e `C3-A1-F3-S1`. Seus CSVs contêm somente a trajetória calculada até a interrupção. O link **Testar gráficos do voo** exibe qualquer combinação sem registrar uma tentativa.

## Operação e classificação

O ranking ordena as missões classificadas por apogeu decrescente, velocidade máxima decrescente, horário mais antigo e ID crescente. Abaixo de 0,15 calibre, os dois gráficos exibem apenas o trecho inicial e a operação é abortada antes do apogeu. O limite de 0,15 calibre é classificado. Todas as tentativas são preservadas; abortadas contam no histórico, nas escolhas e no movimento do dashboard, mas ficam fora do ranking e dos indicadores de desempenho. A visualização opcional do ranking mostra só a melhor de cada participante. Apelidos iguais após normalização de caixa contam como um participante. O gráfico de altura marca o apogeu apenas nas missões classificadas. Uma simulação interrompida antes do pouso só recebe a marcação de resultado parcial se também passar no limite de estabilidade. Depois de ensaios, `preparar-evento CAMINHO_DO_BACKUP` guarda o banco completo e zera as tentativas sem apagar os 108 voos. O comando recusa sobrescrever um backup existente.

SQLite usa WAL, chaves estrangeiras e backup pela API do próprio SQLite. O log de erros fica em `instance/sepex.log`. `/diagnostico` mostra cobertura, séries parciais, tentativas de demonstração e integridade. `verificar-prontidao` confere os 108 arquivos ORK/CSV, hashes importados, pontos dos gráficos, banco e variáveis de administração. Ver [operação](docs/OPERACAO-SEPEX.md) para rede local, quiosque, backup e recuperação.

O frontend inclui as imagens fornecidas para as peças em `app/static/img/componentes` como `coifa_c1.png`, `coifa_c2.png`, `coifa_c3.png`, `corpo.png`, `aleta_a1.png`, `aleta_a2.png` e `aleta_a3.png`. A página inicial exibe a ilustração de Katherine Johnson em `app/static/img/katherine johnson home/Katherine Johnson.png`. A montagem guiada tem quatro etapas: coifa, aletas, corpo e confirmação. A prancheta técnica em SVG mostra o perfil lateral, as seções, cotas, vista traseira e o selo da configuração. As medidas vêm do catálogo e da configuração; CG, CP e estabilidade só aparecem quando constam de uma simulação real. A representação é esquemática e não deve ser usada para fabricação. A logo em `app/static/Logo/Logo ABAQUAR.png` aparece no cabeçalho. O tema claro é inicial; a escolha entre claro e escuro fica salva no navegador. Chart.js 4.5.0 está armazenado em `app/static/vendor` com sua licença. Nenhum CDN é chamado em produção.

Para conferir a interface em Chromium nas resoluções de 1920 × 1080, 1366 × 768, 1024 × 768, 768 × 1024 e 390 × 844, instale opcionalmente Playwright (`python -m pip install playwright` e `python -m playwright install chromium`) e execute `python -m scripts.verificar_interface`. As capturas ficam em `data/exports/qa`. Com o computador conectado à rede local, `python -m scripts.verificar_mobile` testa o acesso HTTP por IP, cinco larguras de tela, duas participações seguidas, a marcação do apogeu e o dashboard.

Arquitetura: `app/db.py` contém o esquema e conexão; `app/catalogo.py` gera as combinações; `app/simulacoes.py` importa e revisa CSV; `app/tentativas.py` registra participações; `app/estatisticas.py` calcula ranking e dashboard; `app/web.py` fornece páginas e API; `app/cli.py` contém os comandos. Consulte [arquitetura](docs/ARQUITETURA.md) e [fluxo](docs/FLUXO.md).

**Limites atuais:** a experiência digital está preparada com o modelo OpenRocket de referência. Ela não certifica que as peças físicas, o motor e as condições do local correspondem ao modelo. A equipe deve medir esses itens antes de usar os números como previsão de um lançamento real. A importação reconhece cabeçalhos conhecidos; novos formatos podem exigir mapeamento. O sistema não inclui migrações de esquema nem contas individuais de operadores.
