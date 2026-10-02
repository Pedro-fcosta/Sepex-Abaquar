(() => {
  const raiz = document.getElementById('ranking-pagina');
  if (!raiz) return;
  const $ = (seletor) => raiz.querySelector(seletor);
  const telao = raiz.dataset.telao === '1';
  const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)');
  const formatoInteiro = new Intl.NumberFormat('pt-BR');
  const formatoDecimal = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const formatoHorario = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const inicial = JSON.parse(document.getElementById('ranking-dados-iniciais').textContent);
  const parametros = new URLSearchParams(location.search);
  let linhas = Array.isArray(inicial.linhas) ? inicial.linhas : [];
  let assinatura = JSON.stringify(linhas);
  let melhor = raiz.dataset.melhor === '1';
  let pagina = 1;
  let totalPaginas = 1;
  let consultando = false;
  let pausaAte = 0;
  let animacoesLinhas = new Map();
  let recordeTimer;
  const busca = $('#ranking-busca');
  const configuracao = $('#ranking-configuracao');
  const origem = $('#ranking-origem');
  const mostrarTodos = $('#ranking-mostrar-todos');
  const conexao = $('.ranking-ao-vivo');

  busca.value = parametros.get('busca') || '';
  origem.value = parametros.get('origem') === 'incluir' ? 'incluir' : 'oficiais';

  function numero(valor, unidade = '') {
    return valor == null ? '—' : `${formatoDecimal.format(valor)}${unidade ? ` ${unidade}` : ''}`;
  }
  function escapar(valor) {
    return String(valor ?? '').replace(/[&<>"']/g, (caractere) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[caractere]);
  }
  function normalizar(valor) {
    return String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
  }
  function horarioAtual() {
    $('#ranking-relogio').textContent = formatoHorario.format(new Date());
  }
  function estadoConexao(estado, horario) {
    conexao.dataset.estado = estado;
    $('#ranking-conexao').textContent = estado === 'erro' ? 'Conexão temporariamente indisponível' : estado === 'atualizando' ? 'Atualizando' : 'Atualização ao vivo';
    if (horario) $('#ranking-atualizado').textContent = `Atualizado às ${formatoHorario.format(new Date(horario))}`;
  }
  function atualizarUrl() {
    const url = new URL(location.href);
    if (melhor) url.searchParams.set('melhor', '1'); else url.searchParams.delete('melhor');
    const texto = busca.value.trim();
    if (texto) url.searchParams.set('busca', texto); else url.searchParams.delete('busca');
    if (configuracao.value) url.searchParams.set('config', configuracao.value); else url.searchParams.delete('config');
    if (origem.value === 'incluir') url.searchParams.set('origem', 'incluir'); else url.searchParams.delete('origem');
    history.replaceState(null, '', url);
    const alternar = telao ? $('#ranking-sair-telao') : $('#ranking-entrar-telao');
    if (alternar) {
      const destino = new URL(alternar.href);
      destino.searchParams.delete('display');
      destino.searchParams.delete('modo');
      for (const chave of ['melhor', 'busca', 'config', 'origem']) {
        destino.searchParams.delete(chave);
        if (url.searchParams.has(chave)) destino.searchParams.set(chave, url.searchParams.get(chave));
      }
      if (!telao) destino.searchParams.set('display', '1');
      alternar.href = destino;
    }
  }
  function preencherConfiguracoes() {
    const selecionada = configuracao.value || parametros.get('config') || '';
    const codigos = [...new Set(linhas.map((linha) => linha.configuracao_codigo))].sort();
    configuracao.replaceChildren(new Option('Todas as configurações', ''), ...codigos.map((codigo) => new Option(codigo, codigo)));
    configuracao.value = codigos.includes(selecionada) ? selecionada : '';
  }
  function filtrar() {
    const termo = normalizar(busca.value.trim());
    const codigo = configuracao.value;
    const corresponde = (linha) => (!termo || normalizar(linha.nome).includes(termo)) && (!codigo || linha.configuracao_codigo === codigo);
    const oficiaisFiltrados = linhas.filter((linha) => !linha.demonstrativo && corresponde(linha));
    const vistos = new Set();
    const oficiais = melhor ? oficiaisFiltrados.filter((linha) => {
      if (vistos.has(linha.participante_id)) return false;
      vistos.add(linha.participante_id);
      return true;
    }) : oficiaisFiltrados;
    let demonstracoes = origem.value === 'incluir' ? linhas.filter((linha) => linha.demonstrativo && corresponde(linha)) : [];
    if (melhor) {
      const participantes = new Set(oficiais.map((linha) => linha.participante_id));
      demonstracoes = demonstracoes.filter((linha) => {
        if (participantes.has(linha.participante_id)) return false;
        participantes.add(linha.participante_id);
        return true;
      });
    }
    return { oficiaisFiltrados, oficiais, demonstracoes };
  }
  function contar(elemento, valor, unidade = '') {
    const alvo = $(elemento);
    const anterior = Number(alvo.dataset.valor);
    alvo.dataset.valor = String(valor);
    if (!Number.isFinite(valor)) { alvo.textContent = '—'; return; }
    const formatar = (n) => unidade ? numero(n, unidade) : formatoInteiro.format(Math.round(n));
    if (movimentoReduzido.matches || !Number.isFinite(anterior) || anterior === valor) { alvo.textContent = formatar(valor); return; }
    const inicio = performance.now();
    const duracao = 650;
    function quadro(agora) {
      if (Number(alvo.dataset.valor) !== valor) return;
      const progresso = Math.min(1, (agora - inicio) / duracao);
      const suave = 1 - (1 - progresso) ** 3;
      alvo.textContent = formatar(anterior + (valor - anterior) * suave);
      if (progresso < 1) requestAnimationFrame(quadro);
    }
    requestAnimationFrame(quadro);
  }
  function renderizarIndicadores(oficiais) {
    const velocidades = oficiais.map((linha) => linha.velocidade_max_ms).filter((valor) => valor != null);
    contar('#ranking-kpi-lancamentos', oficiais.length);
    contar('#ranking-kpi-participantes', new Set(oficiais.map((linha) => linha.participante_id)).size);
    contar('#ranking-kpi-apogeu', oficiais.length ? Math.max(...oficiais.map((linha) => linha.apogeu_m)) : NaN, 'm');
    contar('#ranking-kpi-velocidade', velocidades.length ? Math.max(...velocidades) : NaN, 'm/s');
  }
  const medalha = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 2 5 7 5-7M5 4l7 9 7-9M12 11a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11Z"/><path d="m12 14 1 2.2 2.4.3-1.7 1.6.4 2.4-2.1-1.1-2.1 1.1.4-2.4-1.7-1.6 2.4-.3Z"/></svg>';
  function cartao(linha, posicao, lider) {
    if (!linha) return `<article class="ranking-podio-cartao placeholder" data-posicao="${posicao}"><span class="ranking-medalha">${medalha} ${posicao}º lugar</span><strong>Espaço reservado para um novo voo</strong><span>O próximo resultado oficial pode ocupar esta posição.</span></article>`;
    const velocidade = numero(linha.velocidade_max_ms, 'm/s');
    const diferenca = posicao === 1 ? 'Líder da classificação' : `−${numero(lider.apogeu_m - linha.apogeu_m, 'm')} do líder`;
    return `<article class="ranking-podio-cartao" data-posicao="${posicao}" data-id="${linha.id}"><span class="ranking-medalha">${medalha} ${posicao}º lugar</span><h3 class="ranking-podio-nome">${escapar(linha.nome)}</h3><strong class="ranking-podio-apogeu">${formatoDecimal.format(linha.apogeu_m)} <small>m</small></strong><div class="ranking-podio-dados"><code>${escapar(linha.configuracao_codigo)}</code><span>${velocidade}</span></div><div class="ranking-podio-rodape"><span class="ranking-badge ranking-badge-oficial">OpenRocket</span><span>${diferenca}</span></div></article>`;
  }
  function renderizarPodio(oficiais) {
    const podio = $('#ranking-podio');
    const vazio = $('#ranking-vazio');
    const totalOficiais = linhas.filter((linha) => !linha.demonstrativo).length;
    if (!oficiais.length) {
      podio.hidden = true;
      vazio.hidden = false;
      if (totalOficiais) {
        vazio.querySelector('h2').textContent = 'Nenhum voo oficial corresponde aos filtros';
        vazio.querySelector('p').textContent = 'Ajuste a busca ou limpe os filtros para ver a classificação.';
      } else {
        vazio.querySelector('h2').textContent = 'O ranking está pronto para o primeiro lançamento';
        vazio.querySelector('p').textContent = 'Monte uma configuração e registre o primeiro resultado da SEPEX 2026.';
      }
      return;
    }
    vazio.hidden = true;
    podio.hidden = false;
    podio.innerHTML = [2, 1, 3].map((posicao) => cartao(oficiais[posicao - 1], posicao, oficiais[0])).join('');
  }
  function linhaTabela(linha, posicao, lider) {
    const demo = Boolean(linha.demonstrativo);
    const classe = animacoesLinhas.get(linha.id) || '';
    const diferenca = demo || !lider ? '—' : posicao === 1 ? 'Líder' : `−${numero(lider.apogeu_m - linha.apogeu_m, 'm')} do líder`;
    const origemHtml = demo ? '<span class="ranking-badge ranking-badge-demo">DEMO</span><span class="ranking-demo-nota">Resultado demonstrativo — não participa da classificação oficial</span>' : '<span class="ranking-badge ranking-badge-oficial">OpenRocket</span>';
    return `<tr class="${demo ? 'demo ' : ''}${classe}" data-id="${linha.id}"><td><span class="ranking-posicao ${posicao && posicao <= 3 ? `podio podio-${posicao}` : ''}">${demo ? '—' : `#${posicao}`}</span></td><td>${escapar(linha.nome)}</td><td><code class="ranking-config-chip">${escapar(linha.configuracao_codigo)}</code></td><td class="ranking-apogeu">${numero(linha.apogeu_m, 'm')}</td><td>${numero(linha.velocidade_max_ms, 'm/s')}</td><td>${origemHtml}</td><td class="ranking-diferenca">${diferenca}</td></tr>`;
  }
  function renderizarTabela(oficiais, demonstracoes) {
    const lider = oficiais[0];
    const classificados = mostrarTodos.checked
      ? oficiais.map((linha, indice) => ({ linha, posicao: indice + 1 }))
      : oficiais.slice(3).map((linha, indice) => ({ linha, posicao: indice + 4 }));
    const itens = [...classificados, ...demonstracoes.map((linha) => ({ linha, posicao: null }))];
    const porPagina = telao ? (innerHeight < 750 && demonstracoes.length ? 1 : innerHeight < 850 ? 2 : innerHeight < 950 ? 4 : 6) : 20;
    totalPaginas = Math.max(1, Math.ceil(itens.length / porPagina));
    pagina = Math.min(pagina, totalPaginas);
    const visiveis = itens.slice((pagina - 1) * porPagina, pagina * porPagina);
    $('#ranking-tabela-corpo').innerHTML = visiveis.length ? visiveis.map(({ linha, posicao }) => linhaTabela(linha, posicao, lider)).join('') : '<tr><td colspan="7" class="ranking-tabela-vazia">Nenhuma posição adicional para exibir nesta seleção.</td></tr>';
    $('#ranking-contagem').textContent = `${formatoInteiro.format(oficiais.length)} ${oficiais.length === 1 ? 'resultado oficial' : 'resultados oficiais'}${demonstracoes.length ? ` · ${formatoInteiro.format(demonstracoes.length)} demonstração${demonstracoes.length === 1 ? '' : 'ões'}` : ''}`;
    $('#ranking-lista-titulo').textContent = mostrarTodos.checked ? 'Todas as posições' : 'Demais posições';
    const paginacao = $('#ranking-paginacao');
    paginacao.hidden = !itens.length || (!telao && totalPaginas === 1);
    $('#ranking-pagina-atual').textContent = `Página ${pagina} de ${totalPaginas}`;
    $('#ranking-anterior').disabled = pagina <= 1;
    $('#ranking-proxima').disabled = pagina >= totalPaginas;
  }
  function renderizar() {
    const { oficiaisFiltrados, oficiais, demonstracoes } = filtrar();
    renderizarIndicadores(oficiaisFiltrados);
    renderizarPodio(oficiais);
    renderizarTabela(oficiais, demonstracoes);
    raiz.querySelectorAll('[data-modo]').forEach((botao) => botao.setAttribute('aria-pressed', String((botao.dataset.modo === 'melhor') === melhor)));
  }
  function interacao() { pausaAte = Date.now() + 25000; }
  function atualizarFiltros() { pagina = 1; interacao(); atualizarUrl(); renderizar(); }

  raiz.addEventListener('pointerdown', interacao);
  raiz.addEventListener('keydown', interacao);
  raiz.addEventListener('wheel', interacao, { passive: true });
  window.addEventListener('resize', () => { if (telao) renderizar(); });

  raiz.querySelectorAll('[data-modo]').forEach((botao) => botao.addEventListener('click', () => { melhor = botao.dataset.modo === 'melhor'; atualizarFiltros(); }));
  busca.addEventListener('input', atualizarFiltros);
  configuracao.addEventListener('change', atualizarFiltros);
  origem.addEventListener('change', atualizarFiltros);
  mostrarTodos.addEventListener('change', atualizarFiltros);
  $('#ranking-limpar').addEventListener('click', () => { busca.value = ''; configuracao.value = ''; origem.value = 'oficiais'; atualizarFiltros(); });
  $('#ranking-anterior').addEventListener('click', () => { pagina = Math.max(1, pagina - 1); interacao(); renderizar(); });
  $('#ranking-proxima').addEventListener('click', () => { pagina = Math.min(totalPaginas, pagina + 1); interacao(); renderizar(); });
  $('#ranking-filtros-botao').addEventListener('click', () => { const aberto = $('.ranking-controles').classList.toggle('filtros-abertos'); $('#ranking-filtros-botao').setAttribute('aria-expanded', String(aberto)); interacao(); });

  const fullscreen = $('#ranking-fullscreen');
  if (fullscreen) {
    fullscreen.addEventListener('click', async () => {
      interacao();
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
        else throw new Error('Fullscreen sem suporte');
      } catch (_) {
        fullscreen.textContent = 'Tela cheia indisponível';
        setTimeout(() => { fullscreen.textContent = 'Tela cheia'; }, 3000);
      }
    });
    document.addEventListener('fullscreenchange', () => { fullscreen.textContent = document.fullscreenElement ? 'Sair da tela cheia' : 'Tela cheia'; });
  }

  function anunciarRecorde(novo, antigo) {
    if (novo == null || antigo == null || novo <= antigo + 0.0001 || movimentoReduzido.matches) return;
    const lider = linhas.find((linha) => !linha.demonstrativo);
    if (!lider) return;
    const chave = `${lider.id}:${lider.apogeu_m}`;
    try {
      if (sessionStorage.getItem('sepex-recorde-anunciado') === chave) return;
      sessionStorage.setItem('sepex-recorde-anunciado', chave);
    } catch (_) { /* A sessão pode estar indisponível. */ }
    const faixa = $('#ranking-recorde');
    faixa.hidden = false;
    $('#ranking-podio .ranking-podio-cartao[data-posicao="1"]')?.classList.add('recorde-ativo');
    clearTimeout(recordeTimer);
    recordeTimer = setTimeout(() => { faixa.hidden = true; $('#ranking-podio .ranking-podio-cartao[data-posicao="1"]')?.classList.remove('recorde-ativo'); }, 5000);
  }
  async function consultar() {
    if (consultando || document.hidden) return;
    consultando = true;
    estadoConexao('atualizando');
    const controlador = new AbortController();
    const limite = setTimeout(() => controlador.abort(), 8000);
    try {
      const resposta = await fetch(raiz.dataset.api, { cache: 'no-store', signal: controlador.signal, headers: { Accept: 'application/json' } });
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const novos = await resposta.json();
      if (!Array.isArray(novos.linhas)) throw new Error('Dados inválidos');
      const novaAssinatura = JSON.stringify(novos.linhas);
      if (novaAssinatura !== assinatura) {
        const antigosOficiais = linhas.filter((linha) => !linha.demonstrativo);
        const novoRecorde = novos.linhas.find((linha) => !linha.demonstrativo)?.apogeu_m ?? null;
        const antigoRecorde = antigosOficiais[0]?.apogeu_m ?? null;
        const posicoes = new Map(antigosOficiais.map((linha, indice) => [linha.id, indice + 1]));
        animacoesLinhas = new Map(novos.linhas.filter((linha) => !linha.demonstrativo).map((linha, indice) => [linha.id, !posicoes.has(linha.id) ? 'novo' : posicoes.get(linha.id) > indice + 1 ? 'subiu' : posicoes.get(linha.id) < indice + 1 ? 'desceu' : '']));
        linhas = novos.linhas;
        assinatura = novaAssinatura;
        preencherConfiguracoes();
        renderizar();
        anunciarRecorde(novoRecorde, antigoRecorde);
        setTimeout(() => { animacoesLinhas.clear(); }, 3000);
      }
      estadoConexao('ok', novos.gerado_em);
    } catch (_) {
      estadoConexao('erro');
    } finally {
      clearTimeout(limite);
      consultando = false;
    }
  }

  preencherConfiguracoes();
  atualizarUrl();
  renderizar();
  estadoConexao('ok', inicial.gerado_em);
  if (telao) {
    horarioAtual();
    setInterval(horarioAtual, 1000);
    setInterval(() => { if (!document.hidden && Date.now() > pausaAte && totalPaginas > 1) { pagina = pagina % totalPaginas + 1; renderizar(); } }, 12000);
    setInterval(() => { if (!document.hidden && !movimentoReduzido.matches) { const foguete = $('.ranking-foguete'); foguete.classList.remove('voar'); void foguete.offsetWidth; foguete.classList.add('voar'); } }, 45000);
  }
  setInterval(consultar, 12000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) consultar(); });
})();
