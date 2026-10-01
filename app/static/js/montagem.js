const formulario = document.getElementById('form-montagem');
const paineis = [...document.querySelectorAll('.etapa')];
const passos = [...document.querySelectorAll('.progresso-etapa')];
const botaoVoltar = document.getElementById('voltar');
const botaoContinuar = document.getElementById('continuar');
const botaoConfirmar = document.getElementById('confirmar');
const mensagemErro = document.getElementById('erro');
const linkPrevia = document.getElementById('link-previa');
const namespaceSvg = 'http://www.w3.org/2000/svg';
const blueprint = document.getElementById('preview-foguete');
const medidasBlueprint = JSON.parse(blueprint.dataset.medidas);

const nomesCoifa = { C1: 'cônica', C2: 'ogival', C3: 'elipsoidal' };
const nomesAleta = { A1: 'trapezoidal reta', A2: 'trapezoidal enflechada', A3: 'elíptica' };

let etapaAtual = 0;
let etapaLiberada = 0;
let codigoAtual = '';
let situacao = 'consultando';
let enviando = false;
let consultaAtual = null;
let numeroConsulta = 0;
let comprimentoCorpoAtual = null;
let dadosTecnicos = null;

function escolha(nome) {
  return formulario.querySelector(`input[name="${nome}"]:checked`)?.value || null;
}

function criarSvg(nome, atributos) {
  const elemento = document.createElementNS(namespaceSvg, nome);
  Object.entries(atributos).forEach(([chave, valor]) => elemento.setAttribute(chave, String(valor)));
  return elemento;
}

function linhaSvg(grupo, x1, y1, x2, y2, classe, extras = {}) {
  grupo.append(criarSvg('line', { x1, y1, x2, y2, class: classe, ...extras }));
}

function textoSvg(grupo, x, y, conteudo, classe, extras = {}) {
  const elemento = criarSvg('text', { x, y, class: classe, ...extras });
  elemento.textContent = conteudo;
  grupo.append(elemento);
  return elemento;
}

function cotaSvg(grupo, inicio, fim, y, origem, rotulo) {
  linhaSvg(grupo, inicio, origem, inicio, y + (y < origem ? -8 : 8), 'blueprint-linha-auxiliar');
  linhaSvg(grupo, fim, origem, fim, y + (y < origem ? -8 : 8), 'blueprint-linha-auxiliar');
  linhaSvg(grupo, inicio, y, fim, y, 'blueprint-cota', {
    'marker-start': 'url(#blueprint-seta)', 'marker-end': 'url(#blueprint-seta)',
  });
  textoSvg(grupo, (inicio + fim) / 2, y - 9, rotulo, 'blueprint-cota-texto', { 'text-anchor': 'middle' });
}

function caminhoCoifa(coifa, ponta, base, topo, fundo, centro) {
  if (coifa === 'C1') return `M${ponta} ${centro} L${base} ${topo} L${base} ${fundo} Z`;
  if (coifa === 'C2') return `M${ponta} ${centro} Q${ponta + (base - ponta) * .48} ${topo} ${base} ${topo} L${base} ${fundo} Q${ponta + (base - ponta) * .48} ${fundo} ${ponta} ${centro} Z`;
  return `M${ponta} ${centro} C${ponta} ${topo + 2} ${ponta + (base - ponta) * .54} ${topo} ${base} ${topo} L${base} ${fundo} C${ponta + (base - ponta) * .54} ${fundo} ${ponta} ${fundo - 2} ${ponta} ${centro} Z`;
}

function caminhoAleta(formato, inicio, fim, base, envergadura, direcao) {
  const ponta = base + direcao * envergadura;
  const raiz = fim - inicio;
  if (formato === 'A1') return `M${inicio} ${base} L${inicio + raiz * .18} ${ponta} L${inicio + raiz * .68} ${ponta} L${fim} ${base} Z`;
  if (formato === 'A2') return `M${inicio} ${base} L${inicio + raiz * .47} ${ponta} L${inicio + raiz * .88} ${ponta} L${fim} ${base} Z`;
  return `M${inicio} ${base} C${inicio + raiz * .08} ${ponta} ${inicio + raiz * .72} ${ponta} ${fim} ${base} Z`;
}

function renderRocketBlueprint(estado) {
  const { coifa, aleta, quantidade, secoes, codigo } = estado;
  const vistaMovel = window.matchMedia('(max-width: 600px)').matches;
  blueprint.setAttribute('viewBox', vistaMovel ? '0 0 500 535' : '0 0 500 700');
  if (!medidasBlueprint.coifas?.[coifa] || !medidasBlueprint.aletas?.[aleta] || !medidasBlueprint.secao_mm || !medidasBlueprint.diametro_mm) {
    const chamadas = document.getElementById('rocket-callouts');
    chamadas.replaceChildren();
    textoSvg(chamadas, 250, 210, 'CATÁLOGO DE MEDIDAS NÃO INICIALIZADO', 'blueprint-cota-texto', { 'text-anchor': 'middle' });
    blueprint.setAttribute('aria-label', 'Prancheta indisponível: catálogo de medidas não inicializado');
    return;
  }
  const diametroMm = Number(medidasBlueprint.diametro_mm);
  const narizMm = Number(medidasBlueprint.coifas[coifa]);
  const corpoMm = comprimentoCorpoAtual ?? secoes * Number(medidasBlueprint.secao_mm);
  const secaoMm = corpoMm / secoes;
  const raizMm = Number(medidasBlueprint.aletas[aleta].corda_raiz_mm);
  const envergaduraMm = Number(medidasBlueprint.aletas[aleta].envergadura_mm);
  const totalMm = narizMm + corpoMm;
  const escala = Math.min(.85, 360 / totalMm);
  const comprimento = totalMm * escala;
  const ponta = (500 - comprimento) / 2;
  const base = ponta + narizMm * escala;
  const final = ponta + comprimento;
  const centro = 205;
  const topo = centro - diametroMm * escala / 2;
  const fundo = centro + diametroMm * escala / 2;
  const grupoCorpo = document.getElementById('preview-corpo-svg');
  const grupoAletas = document.getElementById('preview-aletas-svg');
  const centros = document.getElementById('rocket-centerlines');
  const cotas = document.getElementById('rocket-dimensions');
  const chamadas = document.getElementById('rocket-callouts');
  const traseira = document.getElementById('aletas-traseiras');
  const vistaTraseira = document.getElementById('rocket-rear-view');
  const selo = document.getElementById('rocket-title-block');
  const equilibrio = document.getElementById('rocket-cg-cp');
  grupoCorpo.replaceChildren();
  grupoAletas.replaceChildren();
  centros.replaceChildren();
  cotas.replaceChildren();
  chamadas.replaceChildren();
  traseira.replaceChildren();
  [...vistaTraseira.querySelectorAll(':scope > text')].forEach(elemento => elemento.remove());
  selo.replaceChildren();
  if (vistaMovel) selo.setAttribute('hidden', '');
  else selo.removeAttribute('hidden');
  equilibrio.replaceChildren();
  equilibrio.setAttribute('hidden', '');

  const coifaSvg = document.getElementById('preview-coifa-svg');
  coifaSvg.setAttribute('d', caminhoCoifa(coifa, ponta, base, topo, fundo, centro));
  const modulo = corpoMm * escala / secoes;
  for (let indice = 0; indice < secoes; indice += 1) {
    const x = base + indice * modulo;
    grupoCorpo.append(criarSvg('rect', { x, y: topo, width: modulo, height: fundo - topo, class: 'svg-corpo' }));
    if (indice > 0) linhaSvg(grupoCorpo, x, topo, x, fundo, 'svg-junta');
  }
  grupoCorpo.append(criarSvg('rect', { x: final - 5, y: topo - 2, width: 5, height: fundo - topo + 4, class: 'blueprint-anel' }));
  const fimAleta = final - Math.max(5, 7 * escala);
  const inicioAleta = fimAleta - raizMm * escala;
  for (const direcao of [-1, 1]) {
    grupoAletas.append(criarSvg('path', {
      d: caminhoAleta(aleta, inicioAleta, fimAleta, direcao < 0 ? topo : fundo, envergaduraMm * escala, direcao),
      class: 'svg-aleta',
    }));
  }

  textoSvg(chamadas, 17, 28, 'VISTA LATERAL · PERFIL', 'blueprint-rotulo');
  cotaSvg(cotas, ponta, final, 76, topo - envergaduraMm * escala, `COMPRIMENTO TOTAL: ${totalMm} mm`);
  linhaSvg(centros, ponta - 15, centro, final + 15, centro, 'blueprint-centro');
  cotaSvg(cotas, base, final, 320, fundo + envergaduraMm * escala, `CORPO: ${corpoMm} mm`);
  textoSvg(chamadas, 17, 124, `COIFA — ${coifa} ${nomesCoifa[coifa].toUpperCase()}`, 'blueprint-chamada');
  linhaSvg(chamadas, 142, 130, ponta + (base - ponta) * .55, topo - 5, 'blueprint-linha-auxiliar');
  if (aleta === 'A2') {
    textoSvg(chamadas, 267, 117, 'ALETA — A2 TRAPEZOIDAL', 'blueprint-chamada');
    textoSvg(chamadas, 267, 132, 'ENFLECHADA', 'blueprint-chamada');
  } else {
    textoSvg(chamadas, 267, 124, `ALETA — ${aleta} ${nomesAleta[aleta].toUpperCase()}`, 'blueprint-chamada');
  }
  linhaSvg(chamadas, 338, 139, inicioAleta + raizMm * escala * .5, topo - envergaduraMm * escala, 'blueprint-linha-auxiliar');
  textoSvg(chamadas, 17, 283, `Ø ${diametroMm} mm`, 'blueprint-chamada');
  linhaSvg(chamadas, 82, 278, base + 12, fundo + 3, 'blueprint-linha-auxiliar');
  textoSvg(chamadas, 270, 283, `ANEL DE ALETAS — F${quantidade}`, 'blueprint-chamada');
  linhaSvg(chamadas, 343, 277, final - 3, fundo + 3, 'blueprint-linha-auxiliar');

  textoSvg(vistaTraseira, 20, 354, 'VISTA TRASEIRA · F-F', 'blueprint-rotulo');
  for (let indice = 0; indice < quantidade; indice += 1) {
    traseira.append(criarSvg('path', {
      d: 'M74 45 L70 9 L90 9 L86 45 Z', class: 'traseira-aleta',
      transform: `rotate(${indice * 360 / quantidade} 80 70)`,
    }));
  }
  textoSvg(vistaTraseira, 105, 513, `${quantidade} × ${360 / quantidade}°`, 'blueprint-valor', { 'text-anchor': 'middle' });
  document.getElementById('vista-traseira').setAttribute('aria-label', `Vista traseira com ${quantidade} aletas espaçadas em ${360 / quantidade} graus`);
  textoSvg(chamadas, 232, 389, `COIFA · ${coifa} ${nomesCoifa[coifa].toUpperCase()}`, 'blueprint-dado');
  textoSvg(chamadas, 232, 417, `CORPO MODULAR · ${secoes} × ${secaoMm} mm`, 'blueprint-dado');
  textoSvg(chamadas, 232, 445, `ALETA · ${aleta} ${nomesAleta[aleta].toUpperCase()}`, 'blueprint-dado');
  textoSvg(chamadas, 232, 473, `DISTRIBUIÇÃO · ${quantidade} × ${360 / quantidade}°`, 'blueprint-dado');

  if (dadosTecnicos) {
    const pontos = [
      { chave: 'cg_m', sigla: 'CG', classe: 'blueprint-cg', posicao: topo - 30, legenda: 499 },
      { chave: 'cp_m', sigla: 'CP', classe: 'blueprint-cp', posicao: fundo + 30, legenda: 519 },
    ];
    let visiveis = 0;
    for (const ponto of pontos) {
      const valor = dadosTecnicos[ponto.chave];
      if (typeof valor !== 'number' || !Number.isFinite(valor)) continue;
      const milimetros = valor * 1000;
      if (milimetros < 0 || milimetros > totalMm) continue;
      const x = ponta + milimetros * escala;
      linhaSvg(equilibrio, x, ponto.sigla === 'CG' ? topo - 24 : fundo + 24, x, centro, ponto.classe);
      textoSvg(equilibrio, x, ponto.posicao, ponto.sigla, ponto.classe, { 'text-anchor': 'middle' });
      textoSvg(equilibrio, 232, ponto.legenda, `${ponto.sigla}: ${milimetros.toFixed(1).replace('.', ',')} mm`, ponto.classe);
      visiveis += 1;
    }
    if (visiveis) equilibrio.removeAttribute('hidden');
    if (typeof dadosTecnicos.cg_m === 'number' && typeof dadosTecnicos.cp_m === 'number') {
      const distancia = Math.abs(dadosTecnicos.cp_m - dadosTecnicos.cg_m) * 1000;
      textoSvg(equilibrio, 343, 499, `ΔCG–CP: ${distancia.toFixed(1).replace('.', ',')} mm`, 'blueprint-valor');
    }
    if (typeof dadosTecnicos.margem_calibres === 'number') {
      textoSvg(equilibrio, 343, 519, `ESTAB.: ${dadosTecnicos.margem_calibres.toFixed(2).replace('.', ',')} cal`, 'blueprint-valor');
      equilibrio.removeAttribute('hidden');
    }
  }

  selo.append(criarSvg('rect', { x: 14, y: 542, width: 472, height: 136, class: 'blueprint-selo-moldura' }));
  for (const y of [576, 610, 644]) linhaSvg(selo, 14, y, 486, y, 'blueprint-selo-linha');
  for (const [x, y1, y2] of [[249, 542, 644], [167, 644, 678], [344, 644, 678]]) linhaSvg(selo, x, y1, x, y2, 'blueprint-selo-linha');
  const campo = (x, y, rotulo, valor, classe = 'blueprint-selo-valor') => {
    textoSvg(selo, x, y + 11, rotulo, 'blueprint-selo-rotulo');
    return textoSvg(selo, x, y + 28, valor, classe);
  };
  campo(22, 542, 'PROJETO', 'ABAQUAR — SEPEX 2026');
  campo(257, 542, 'DESCRIÇÃO', 'FOGUETE MODULAR');
  const codigoSvg = campo(22, 576, 'CONFIGURAÇÃO', codigo, 'blueprint-selo-codigo');
  codigoSvg.id = 'codigo';
  campo(257, 576, 'CORPO', `${corpoMm} mm · ${secoes} SEÇÕES`);
  campo(22, 610, 'COIFA', `${coifa} ${nomesCoifa[coifa].toUpperCase()}`);
  campo(257, 610, 'ALETA', `${aleta} ${nomesAleta[aleta].toUpperCase()}`);
  campo(22, 644, 'QUANTIDADE', `${quantidade} ALETAS`);
  campo(175, 644, 'ESCALA', 'ESQUEMÁTICA');
  campo(352, 644, 'REVISÃO', 'REV. 00');
  textoSvg(selo, 250, 692, 'REPRESENTAÇÃO TÉCNICA ESQUEMÁTICA · NÃO UTILIZAR PARA FABRICAÇÃO', 'blueprint-rodape', { 'text-anchor': 'middle' });
  document.getElementById('blueprint-codigo-movel').textContent = codigo;
  document.getElementById('blueprint-corpo-movel').textContent = `${corpoMm} mm · ${secoes} SEÇÕES`;
  document.getElementById('blueprint-coifa-movel').textContent = `${coifa} ${nomesCoifa[coifa].toUpperCase()}`;
  document.getElementById('blueprint-aleta-movel').textContent = `${aleta} ${nomesAleta[aleta].toUpperCase()}`;
  document.getElementById('blueprint-quantidade-movel').textContent = `${quantidade} ALETAS`;

  const posicoes = dadosTecnicos && typeof dadosTecnicos.cg_m === 'number' && typeof dadosTecnicos.cp_m === 'number'
    ? `, CG ${Math.round(dadosTecnicos.cg_m * 1000)} milímetros, CP ${Math.round(dadosTecnicos.cp_m * 1000)} milímetros`
    : '';
  blueprint.setAttribute('aria-label', `Prancheta técnica ${codigo}: coifa ${nomesCoifa[coifa]}, aleta ${nomesAleta[aleta]}, ${quantidade} aletas, corpo de ${corpoMm} milímetros e diâmetro de ${diametroMm} milímetros${posicoes}`);
  blueprint.classList.remove('blueprint-atualizado');
  void blueprint.getBoundingClientRect();
  blueprint.classList.add('blueprint-atualizado');
}

function atualizarBotaoConfirmar() {
  botaoConfirmar.disabled = enviando || !['disponivel', 'demonstracao'].includes(situacao);
}

function mostrarSituacao(tipo, texto) {
  situacao = tipo;
  for (const id of ['disponibilidade', 'disponibilidade-final']) {
    const elemento = document.getElementById(id);
    elemento.className = `estado estado-${tipo}${id === 'disponibilidade' ? ' blueprint-status' : ''}`;
    elemento.textContent = id === 'disponibilidade-final' && tipo === 'disponivel' ? 'Simulação disponível' : texto;
  }
  atualizarBotaoConfirmar();
}

function atualizarResumo() {
  const coifa = escolha('coifa');
  const aleta = escolha('aleta');
  const quantidade = Number(escolha('aletas'));
  const secoes = Number(escolha('secoes'));
  if (!coifa || !aleta || !quantidade || !secoes) return;

  const codigo = `${coifa}-${aleta}-F${quantidade}-S${secoes}`;
  if (codigo !== codigoAtual) {
    comprimentoCorpoAtual = null;
    dadosTecnicos = null;
  }
  document.getElementById('confirmacao-coifa').textContent = nomesCoifa[coifa];
  document.getElementById('confirmacao-aletas').textContent = `${nomesAleta[aleta]} · ${quantidade} aletas`;
  const comprimentoInicial = medidasBlueprint.secao_mm ? `${secoes * Number(medidasBlueprint.secao_mm) / 10} cm` : '—';
  document.getElementById('confirmacao-corpo').textContent = `${secoes} ${secoes === 1 ? 'seção' : 'seções'} · ${comprimentoInicial}`;
  document.getElementById('confirmacao-codigo').textContent = codigo;
  renderRocketBlueprint({ coifa, aleta, quantidade, secoes, codigo });

  if (codigo === codigoAtual) return;
  codigoAtual = codigo;
  linkPrevia.hidden = true;
  linkPrevia.removeAttribute('href');
  consultarDisponibilidade(codigo);
}

async function consultarDisponibilidade(codigo) {
  consultaAtual?.abort();
  consultaAtual = new AbortController();
  const pedido = ++numeroConsulta;
  mostrarSituacao('consultando', 'Consultando simulação...');
  try {
    const resposta = await fetch(`/api/configuracoes/${encodeURIComponent(codigo)}`, { signal: consultaAtual.signal });
    if (!resposta.ok) throw new Error('Não foi possível consultar esta configuração.');
    const dados = await resposta.json();
    if (pedido !== numeroConsulta) return;
    comprimentoCorpoAtual = dados.comprimento_corpo_mm;
    dadosTecnicos = dados.dados_tecnicos;
    document.getElementById('confirmacao-corpo').textContent = `${dados.secoes} ${dados.secoes === 1 ? 'seção' : 'seções'} · ${dados.comprimento_corpo_mm / 10} cm`;
    renderRocketBlueprint({ coifa: escolha('coifa'), aleta: escolha('aleta'), quantidade: Number(escolha('aletas')), secoes: Number(escolha('secoes')), codigo });
    if (dados.url_previa) {
      linkPrevia.href = dados.url_previa;
      linkPrevia.hidden = false;
    }
    if (!dados.disponivel) mostrarSituacao('indisponivel', 'Esta configuração ainda não possui dados de voo disponíveis.');
    else if (dados.demonstrativo) mostrarSituacao('demonstracao', 'Demonstração com dados fictícios');
    else mostrarSituacao('disponivel', 'Dados pré-simulados no OpenRocket');
  } catch (erro) {
    if (erro.name === 'AbortError' || pedido !== numeroConsulta) return;
    mostrarSituacao('erro', 'Falha na consulta. Verifique a conexão local e tente novamente.');
  }
}

function validarEtapa(indice) {
  const grupos = [['coifa'], ['aleta', 'aletas'], ['secoes'], []][indice];
  for (const grupo of grupos) {
    if (!escolha(grupo)) {
      mensagemErro.textContent = 'Escolha uma opção para continuar.';
      formulario.querySelector(`input[name="${grupo}"]`)?.focus();
      return false;
    }
  }
  if (indice === 3) {
    const nome = document.getElementById('nome');
    if (!nome.checkValidity() || nome.value.trim().length < 2) {
      mensagemErro.textContent = 'Informe um nome ou apelido de 2 a 60 caracteres.';
      nome.focus();
      return false;
    }
  }
  mensagemErro.textContent = '';
  return true;
}

function mostrarEtapa(indice) {
  etapaAtual = indice;
  etapaLiberada = Math.max(etapaLiberada, indice);
  paineis.forEach((painel, posicao) => { painel.hidden = posicao !== indice; });
  passos.forEach((passo, posicao) => {
    passo.disabled = posicao > etapaLiberada;
    passo.classList.toggle('concluida', posicao < indice);
    if (posicao === indice) passo.setAttribute('aria-current', 'step');
    else passo.removeAttribute('aria-current');
  });
  botaoVoltar.hidden = indice === 0;
  botaoContinuar.hidden = indice === 3;
  botaoConfirmar.hidden = indice !== 3;
  mensagemErro.textContent = '';
}

botaoContinuar.addEventListener('click', () => {
  if (validarEtapa(etapaAtual)) mostrarEtapa(etapaAtual + 1);
});
botaoVoltar.addEventListener('click', () => mostrarEtapa(etapaAtual - 1));
passos.forEach((passo, indice) => passo.addEventListener('click', () => {
  if (indice <= etapaLiberada) mostrarEtapa(indice);
}));
formulario.addEventListener('change', evento => {
  if (evento.target.matches('input[type="radio"]')) {
    mensagemErro.textContent = '';
    atualizarResumo();
  }
});

formulario.addEventListener('submit', async evento => {
  evento.preventDefault();
  if (etapaAtual !== 3 || enviando || !validarEtapa(3) || !['disponivel', 'demonstracao'].includes(situacao)) return;
  enviando = true;
  atualizarBotaoConfirmar();
  mensagemErro.textContent = '';
  const nome = document.getElementById('nome').value.trim();
  const chaveSessao = 'sepex-participacao';
  let pendente;
  try { pendente = JSON.parse(sessionStorage.getItem(chaveSessao)); } catch (_) { pendente = null; }
  if (!pendente || pendente.codigo !== codigoAtual || pendente.nome !== nome) {
    pendente = { codigo: codigoAtual, nome, id: crypto.randomUUID().replaceAll('-', '') };
    sessionStorage.setItem(chaveSessao, JSON.stringify(pendente));
  }
  try {
    const resposta = await fetch('/api/tentativas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome, codigo: codigoAtual, identificador_sessao: pendente.id }),
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.erro || 'Não foi possível registrar a tentativa.');
    sessionStorage.removeItem(chaveSessao);
    location.assign(dados.url_voo);
  } catch (erro) {
    mensagemErro.textContent = erro.message || 'Falha ao registrar. Tente novamente.';
    enviando = false;
    atualizarBotaoConfirmar();
  }
});

mostrarEtapa(0);
atualizarResumo();
window.matchMedia('(max-width: 600px)').addEventListener('change', atualizarResumo);
