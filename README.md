# ABAQUAR · SEPEX 2026

Experiência local de montagem digital de foguetes modulares para a SEPEX 2026. O visitante escolhe peças, acompanha a animação do voo de uma simulação **previamente importada e aprovada** e entra no ranking. O programa não executa OpenRocket durante o atendimento e funciona sem internet.

## Começo rápido

Requer Python 3.12. No Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SEPEX_ADMIN_TOKEN = 'defina-um-token-longo'
$env:SEPEX_SECRET_KEY = 'defina-outra-chave-longa'
python -m flask --app run init-db
python -m flask --app run seed-configuracoes
python -m flask --app run demo-criar
python run.py
```

Abra `http://127.0.0.1:5000`. A demonstração usa **números fictícios** em `C2-A3-F4-S2`, claramente marcados. Para usar somente resultados reais, execute `python -m flask --app run demo-limpar` antes do evento. Sem simulação aprovada, a interface impede o lançamento daquela configuração.

No Linux/macOS, substitua `py -3.12` por `python3.12`, ative com `source .venv/bin/activate` e defina variáveis com `export`.

## Configurações e dados

São 3 coifas (`C1` cônica, `C2` ogival, `C3` elipsoidal) × 3 formas de aleta (`A1` trapezoidal reta, `A2` enflechada, `A3` elíptica) × 3 quantidades (3–5) × 4 seções (1–4) = **108** combinações. `C2-A3-F4-S2` tem quatro aletas e corpo de 40 cm. `seed-configuracoes` é idempotente. O comprimento do corpo é `seções × 200 mm`; a coifa fica separada dessa medida.

Os valores de partida são configuráveis pelas variáveis `SEPEX_*` de [.env.example](.env.example), antes do seed. Todos os parâmetros iniciais estão marcados `pending_review` no catálogo. Alterar parâmetros após o seed requer atualizar as linhas existentes ou recriar um banco vazio; o seed preserva registros existentes. Massas, CG, CP, motor, atmosfera, vento, estabilidade e demais condições reais continuam pendentes de medição e revisão. Consulte [pendências técnicas](docs/PENDENCIAS-TECNICAS.md).

## Comandos

```powershell
python -m flask --app run init-db
python -m flask --app run seed-configuracoes
python -m flask --app run importar-csv C2-A3-F4-S2 caminho\voo.csv --condicao "Condição SEPEX 2026"
python -m flask --app run pendentes
python -m flask --app run revisar 1 approved
python -m flask --app run revisar 1 rejected
python -m flask --app run condicao-configurar "Condição SEPEX 2026" --motor "motor validado" --temperatura-c 25 --pressao-pa 101325
python -m flask --app run verificar-cobertura
python -m flask --app run demo-criar
python -m flask --app run demo-limpar
python -m flask --app run exportar-tentativas data\exports\tentativas.csv
python -m flask --app run backup-db data\exports\backup.sqlite3
python -m pytest -q
```

Também há interface administrativa em `/admin/entrar` com o token de `SEPEX_ADMIN_TOKEN`. As rotas de escrita e exportação administrativas exigem esse token. Sem token configurado, elas ficam bloqueadas. O login web usa sessão assinada e token de formulário. Configure `SEPEX_SECRET_KEY` estável para preservar sessões entre reinicializações. Não exponha o servidor à internet pública.

O CSV importado fica `pending_review`. Revise o arquivo, parâmetros físicos e indicadores antes de aprovar. Uma aprovação substitui a aprovação anterior da mesma configuração; tentativas antigas preservam os números registrados. O hash SHA-256 do arquivo e a configuração tornam a importação idempotente. O importador lê cabeçalhos comuns em português/inglês, CSV de resumo ou série temporal, converte unidades para SI e salva as unidades originais. Consulte [guia do OpenRocket](docs/OPENROCKET.md). Os CSV em `data/examples` são **exemplos artificiais de formato**, não simulações reais.

O lote em `Foguete Modular - Banco/.ork` e `Foguete Modular - Banco/.csv` contém 21 pares de modelo e série temporal para teste. Depois de `init-db` e `seed-configuracoes`, importe os CSVs com `python -m flask --app run importar-lote "Foguete Modular - Banco/.csv"`. O comando é idempotente e deixa as simulações pendentes. Ao selecionar no configurador uma dessas combinações, use **Testar prévia da animação** para reproduzir a série sem registrar tentativa nem alterar o ranking. Por exemplo, `C1-A1-F3-S1` tem uma série completa. Cinco séries terminam antes do pouso; a página de prévia mostra esse aviso. Todos os CSVs informam ausência de dispositivo de recuperação e exigem revisão antes de aprovação.

## Operação e classificação

O ranking ordena por apogeu decrescente, velocidade máxima decrescente, horário mais antigo e ID crescente. Todas as tentativas são preservadas; a visualização opcional mostra só a melhor de cada participante. Apelidos iguais após normalização de caixa contam como um participante. O dashboard distingue participantes únicos de tentativas, usa histogramas e oferece curva normal teórica apenas como referência. Dados de demonstração entram no ranking enquanto ativos e aparecem marcados `DEMO`; limpe-os para a operação real.

SQLite usa WAL, chaves estrangeiras e backup pela API do próprio SQLite. O log de erros fica em `instance/sepex.log`. `/diagnostico` mostra contagens e `PRAGMA integrity_check`. Ver [operação](docs/OPERACAO-SEPEX.md) para rede local, quiosque, backup e recuperação.

O frontend inclui as imagens fornecidas para as peças em `app/static/img/componentes` como `coifa_c1.png`, `coifa_c2.png`, `coifa_c3.png`, `corpo.png`, `aleta_a1.png`, `aleta_a2.png` e `aleta_a3.png`. A página inicial exibe a ilustração de Katherine Johnson em `app/static/img/katherine johnson home/Katherine Johnson.png`. A montagem guiada tem quatro etapas: coifa, aletas, corpo e confirmação. A pré-visualização em SVG mostra o perfil lateral, as seções do corpo e uma vista traseira com a quantidade de aletas. A logo em `app/static/Logo/Logo ABAQUAR.png` aparece no cabeçalho. O tema claro é inicial; a escolha entre claro e escuro fica salva no navegador. Chart.js 4.5.0 está armazenado em `app/static/vendor` com sua licença. Nenhum CDN é chamado em produção.

Para conferir a interface em Chromium nas resoluções de 1920 × 1080, 1366 × 768, 1024 × 768, 768 × 1024 e 390 × 844, instale opcionalmente Playwright (`python -m pip install playwright` e `python -m playwright install chromium`) e execute `python -m scripts.verificar_interface`. As capturas ficam em `data/exports/qa`.

Arquitetura: `app/db.py` contém o esquema e conexão; `app/catalogo.py` gera as combinações; `app/simulacoes.py` importa e revisa CSV; `app/tentativas.py` registra participações; `app/estatisticas.py` calcula ranking e dashboard; `app/web.py` fornece páginas e API; `app/cli.py` contém os comandos. Consulte [arquitetura](docs/ARQUITETURA.md) e [fluxo](docs/FLUXO.md).

**Limites atuais:** importação de cabeçalhos conhecidos (novos formatos podem exigir mapeamento), revisão científica manual, sem migrações de esquema e sem controle de contas individuais de operadores. Antes da SEPEX, a equipe deve validar medidas e resultados reais das 108 configurações, as regras de estabilidade e a política de nomes duplicados.
