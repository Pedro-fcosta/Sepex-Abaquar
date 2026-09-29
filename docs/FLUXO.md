# Fluxo do visitante

1. Início em `/` e montagem em `/montagem`.
2. A montagem segue quatro etapas: coifa; forma e quantidade de aletas; seções do corpo; nome ou apelido e confirmação. É possível voltar e ajustar as escolhas.
3. O perfil lateral, a vista traseira das aletas, o resumo e o código mudam imediatamente. `/api/configuracoes/<codigo>` informa se há simulação aprovada.
4. Confirmar cria uma tentativa por `POST /api/tentativas`. Um identificador guardado no navegador evita cliques duplos e permite repetir com segurança uma requisição cuja resposta se perdeu.
5. `/voo/<id>` anima dois gráficos sincronizados: altura × tempo e velocidade × tempo. Sem série temporal, mostra curvas apenas ilustrativas, identificadas como tal.
6. `/resultado/<id>` mostra os indicadores gravados no momento da tentativa e a posição atual. Depois o visitante pode recomeçar.

Se uma configuração não tem resultado aprovado, a confirmação fica indisponível. O endpoint valida isso novamente. Se uma simulação demonstrativa estiver ativa, todos os passos marcam seu caráter fictício. O ranking completo e a opção de melhor resultado por participante estão em `/ranking`; `/dashboard` mostra agregados do evento.
