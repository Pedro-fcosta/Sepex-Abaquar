const formulario = document.getElementById('form-montagem');
const paineis = [...document.querySelectorAll('.etapa')];
const passos = [...document.querySelectorAll('.progresso-etapa')];
const botaoVoltar = document.getElementById('voltar');
const botaoContinuar = document.getElementById('continuar');
const botaoConfirmar = document.getElementById('confirmar');
const mensagemErro = document.getElementById('erro');
const linkPrevia = document.getElementById('link-previa');
const namespaceSvg = 'http://www.w3.org/2000/svg';

const nomesCoifa = { C1: 'cônica', C2: 'ogival', C3: 'elipsoidal' };
const nomesAleta = { A1: 'trapezoidal reta', A2: 'trapezoidal enflechada', A3: 'elíptica' };
const formasCoifa = {
  C1: 'M44 110 L160 82 L160 138 Z',
  C2: 'M44 110 Q76 82 160 82 L160 138 Q76 138 44 110 Z',
  C3: 'M44 110 C44 83 98 76 160 82 L160 138 C98 144 44 137 44 110 Z',
};

let etapaAtual = 0;
let etapaLiberada = 0;
let codigoAtual = '';
let situacao = 'consultando';
let enviando = false;
let consultaAtual = null;
let numeroConsulta = 0;

function escolha(nome) {
  return formulario.querySelector(`input[name="${nome}"]:checked`)?.value || null;
}

function criarSvg(nome, atributos) {
  const elemento = document.createElementNS(namespaceSvg, nome);
  Object.entries(atributos).forEach(([chave, valor]) => elemento.setAttribute(chave, String(valor)));
  return elemento;
}

function caminhoAleta(formato, ponta) {
  if (formato === 'A1') return `M${ponta - 86} 82 L${ponta - 70} 50 L${ponta - 25} 50 L${ponta - 8} 82 Z`;
  if (formato === 'A2') return `M${ponta - 86} 82 L${ponta - 42} 50 L${ponta - 4} 50 L${ponta - 20} 82 Z`;
  return `M${ponta - 86} 82 C${ponta - 74} 57 ${ponta - 28} 53 ${ponta - 6} 82 Z`;
}

function desenharFoguete(coifa, aleta, quantidade, secoes) {
  const grupoCorpo = document.getElementById('preview-corpo-svg');
  const grupoAletas = document.getElementById('preview-aletas-svg');
  const caminhoCoifa = document.getElementById('preview-coifa-svg');
  const ponta = 160 + secoes * 86;
  const larguraVista = 340 + secoes * 60;
  const deslocamento = (larguraVista - (ponta + 14 - 44)) / 2 - 44;
  document.getElementById('preview-foguete').setAttribute('viewBox', `0 0 ${larguraVista} 220`);

  grupoCorpo.replaceChildren();
  grupoAletas.replaceChildren();
  for (let indice = 0; indice < secoes; indice += 1) {
    grupoCorpo.append(criarSvg('rect', { x: 160 + indice * 86, y: 82, width: 86, height: 56, class: 'svg-corpo' }));
    if (indice > 0) grupoCorpo.append(criarSvg('line', { x1: 160 + indice * 86, y1: 84, x2: 160 + indice * 86, y2: 136, class: 'svg-junta' }));
  }
  grupoCorpo.append(criarSvg('rect', { x: ponta, y: 91, width: 13, height: 38, rx: 3, class: 'svg-bocal' }));
  const forma = caminhoAleta(aleta, ponta);
  grupoAletas.append(criarSvg('path', { d: forma, class: 'svg-aleta' }));
  grupoCorpo.setAttribute('transform', `translate(${deslocamento} 0)`);
  grupoAletas.setAttribute('transform', `translate(${deslocamento} 0)`);
  caminhoCoifa.setAttribute('d', formasCoifa[coifa]);
  caminhoCoifa.setAttribute('transform', `translate(${deslocamento} 0)`);

  const traseiras = document.getElementById('aletas-traseiras');
  traseiras.replaceChildren();
  for (let indice = 0; indice < quantidade; indice += 1) {
    traseiras.append(criarSvg('path', {
      d: 'M55 43 L55 19 Q60 13 65 19 L65 43 Z',
      class: 'traseira-aleta',
      transform: `rotate(${indice * 360 / quantidade} 60 60)`,
    }));
  }
  document.getElementById('preview-foguete').setAttribute('aria-label', `Perfil lateral do foguete com coifa ${nomesCoifa[coifa]}, uma aleta ${nomesAleta[aleta]} visível e ${secoes} ${secoes === 1 ? 'seção' : 'seções'} de corpo`);
  document.getElementById('vista-traseira').setAttribute('aria-label', `Vista traseira com ${quantidade} aletas distribuídas`);
  document.getElementById('quantidade-texto').textContent = `${quantidade} aletas distribuídas`;
}

function atualizarBotaoConfirmar() {
  botaoConfirmar.disabled = enviando || !['disponivel', 'demonstracao'].includes(situacao);
}

function mostrarSituacao(tipo, texto) {
  situacao = tipo;
  for (const id of ['disponibilidade', 'disponibilidade-final']) {
    const elemento = document.getElementById(id);
    elemento.className = `estado estado-${tipo}`;
    elemento.textContent = texto;
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
  document.getElementById('codigo').textContent = codigo;
  document.getElementById('descricao').textContent = `Coifa ${nomesCoifa[coifa]} · Aleta ${nomesAleta[aleta]} · ${quantidade} aletas · ${secoes * 20} cm de corpo`;
  document.getElementById('confirmacao-coifa').textContent = nomesCoifa[coifa];
  document.getElementById('confirmacao-aletas').textContent = `${nomesAleta[aleta]} · ${quantidade} aletas`;
  document.getElementById('confirmacao-corpo').textContent = `${secoes} ${secoes === 1 ? 'seção' : 'seções'} · ${secoes * 20} cm`;
  document.getElementById('confirmacao-codigo').textContent = codigo;
  desenharFoguete(coifa, aleta, quantidade, secoes);

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
    if (!dados.disponivel && dados.url_previa) {
      mostrarSituacao('indisponivel', 'Simulação importada para prévia; aguardando revisão técnica.');
      linkPrevia.href = dados.url_previa;
      linkPrevia.hidden = false;
    }
    else if (!dados.disponivel) mostrarSituacao('indisponivel', 'Esta configuração ainda não possui simulação aprovada.');
    else if (dados.demonstrativo) mostrarSituacao('demonstracao', 'Demonstração com dados fictícios');
    else mostrarSituacao('disponivel', 'Simulação disponível');
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
