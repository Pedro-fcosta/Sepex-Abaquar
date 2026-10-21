const velocidade = document.getElementById('k-velocidade');
const angulo = document.getElementById('k-angulo');
const gravidade = 9.81;
const formato = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function atualizarTrajetoria() {
  const v = Number(velocidade.value);
  const graus = Number(angulo.value);
  const theta = graus * Math.PI / 180;
  const tempoTotal = 2 * v * Math.sin(theta) / gravidade;
  const alcance = v * Math.cos(theta) * tempoTotal;
  const apogeu = v * v * Math.sin(theta) ** 2 / (2 * gravidade);
  const maxX = Math.max(500, alcance * 1.12);
  const maxY = Math.max(160, apogeu * 1.15);
  const plotX = x => 55 + x / maxX * 665;
  const plotY = y => 340 - y / maxY * 280;
  const pontos = Array.from({ length: 81 }, (_, i) => {
    const t = tempoTotal * i / 80;
    return [plotX(v * Math.cos(theta) * t), plotY(Math.max(0, v * Math.sin(theta) * t - .5 * gravidade * t * t))];
  });
  const curva = pontos.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)} ${y.toFixed(2)}`).join(' ');
  document.getElementById('k-trajetoria-linha').setAttribute('d', curva);
  document.getElementById('k-trajetoria-area').setAttribute('d', `${curva} L${plotX(alcance).toFixed(2)} 340 Z`);
  const picoX = plotX(alcance / 2);
  const picoY = plotY(apogeu);
  const guia = document.getElementById('k-apogeu-guia');
  guia.setAttribute('x1', picoX);
  guia.setAttribute('x2', picoX);
  guia.setAttribute('y1', picoY);
  document.getElementById('k-apogeu-ponto').setAttribute('cx', picoX);
  document.getElementById('k-apogeu-ponto').setAttribute('cy', picoY);
  const rotulo = document.getElementById('k-apogeu-label');
  rotulo.setAttribute('x', Math.min(picoX + 13, 640));
  rotulo.setAttribute('y', Math.max(picoY - 11, 35));
  document.getElementById('k-velocidade-valor').textContent = `${v} m/s`;
  document.getElementById('k-angulo-valor').textContent = `${graus}°`;
  document.getElementById('k-altura').textContent = `${formato.format(apogeu)} m`;
  document.getElementById('k-alcance').textContent = `${formato.format(alcance)} m`;
  document.getElementById('k-duracao').textContent = `${formato.format(tempoTotal)} s`;
  document.getElementById('k-grafico-descricao').textContent =
    `Para velocidade inicial de ${v} metros por segundo e ângulo de ${graus} graus, a altura máxima é ${formato.format(apogeu)} metros, o alcance é ${formato.format(alcance)} metros e o tempo de voo é ${formato.format(tempoTotal)} segundos.`;
}

velocidade.addEventListener('input', atualizarTrajetoria);
angulo.addEventListener('input', atualizarTrajetoria);
document.getElementById('k-reiniciar').addEventListener('click', () => {
  velocidade.value = 65;
  angulo.value = 45;
  atualizarTrajetoria();
});
atualizarTrajetoria();

const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if ('IntersectionObserver' in window && !movimentoReduzido) {
  const eventos = document.querySelectorAll('.k-timeline-item');
  const observador = new IntersectionObserver(entradas => {
    for (const entrada of entradas) {
      if (entrada.isIntersecting) {
        entrada.target.classList.add('k-visivel');
        observador.unobserve(entrada.target);
      }
    }
  }, { threshold: .12, rootMargin: '0px 0px 45px 0px' });
  eventos.forEach(evento => observador.observe(evento));
  document.querySelector('.katherine-pagina').classList.add('k-has-js');
}

const perguntas = [
  {
    texto: 'Qual era uma das funções das matemáticas conhecidas como “computadoras humanas”?',
    opcoes: ['Construir foguetes manualmente.', 'Realizar e verificar cálculos matemáticos.', 'Controlar satélites por rádio.'],
    correta: 1,
    explicacao: 'Elas realizavam e conferiam cálculos usados em pesquisas e missões.'
  },
  {
    texto: 'Por que John Glenn solicitou a conferência de Katherine Johnson?',
    opcoes: ['Para verificar cálculos relacionados à sua missão orbital.', 'Para escolher a cor do foguete.', 'Para construir o computador da nave.'],
    correta: 0,
    explicacao: 'Glenn pediu que Katherine verificasse os resultados dos computadores eletrônicos antes de sua missão orbital.'
  },
  {
    texto: 'O que a matemática permite estudar ao analisar uma trajetória?',
    opcoes: ['Somente a aparência do foguete.', 'Somente o combustível utilizado.', 'Posições, velocidades e condições de movimento.'],
    correta: 2,
    explicacao: 'Modelos matemáticos permitem estimar posições, velocidades e condições ao longo do movimento.'
  }
];
const quizConteudo = document.getElementById('k-quiz-conteudo');
let perguntaAtual = 0;
let acertos = 0;

function elemento(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto) el.textContent = texto;
  return el;
}

function renderizarQuiz() {
  quizConteudo.replaceChildren();
  document.getElementById('k-quiz-pontos').textContent = `${acertos} ${acertos === 1 ? 'ACERTO' : 'ACERTOS'}`;
  document.getElementById('k-quiz-barra-valor').style.width = `${Math.min(perguntaAtual + 1, perguntas.length) / perguntas.length * 100}%`;
  if (perguntaAtual >= perguntas.length) {
    document.getElementById('k-quiz-progresso').textContent = 'QUIZ CONCLUÍDO';
    const resultado = elemento('div', 'k-quiz-resultado');
    resultado.append(elemento('strong', '', `${acertos} / ${perguntas.length}`));
    resultado.append(elemento('p', '', acertos === perguntas.length
      ? 'Você acertou todas! Explore as fontes da NASA para conhecer mais dessa história.'
      : 'Continue explorando a história de Katherine e tente novamente quando quiser.'));
    const reiniciar = elemento('button', 'k-button k-button-blue', 'Refazer quiz');
    reiniciar.type = 'button';
    reiniciar.addEventListener('click', () => { perguntaAtual = 0; acertos = 0; renderizarQuiz(); });
    resultado.append(reiniciar);
    quizConteudo.append(resultado);
    return;
  }
  const pergunta = perguntas[perguntaAtual];
  document.getElementById('k-quiz-progresso').textContent = `PERGUNTA ${perguntaAtual + 1} DE ${perguntas.length}`;
  const titulo = elemento('h3', 'k-quiz-pergunta', pergunta.texto);
  titulo.tabIndex = -1;
  quizConteudo.append(titulo);
  const grupo = elemento('fieldset', 'k-quiz-opcoes');
  grupo.setAttribute('aria-label', 'Escolha uma alternativa');
  const opcoes = pergunta.opcoes.map((texto, indice) => {
    const label = elemento('label', 'k-quiz-opcao');
    const radio = elemento('input');
    radio.type = 'radio';
    radio.name = 'k-resposta';
    radio.value = String(indice);
    label.append(radio, elemento('span', '', texto));
    grupo.append(label);
    return { label, radio };
  });
  quizConteudo.append(grupo);
  const feedback = elemento('div', 'k-quiz-feedback');
  feedback.setAttribute('role', 'status');
  feedback.setAttribute('aria-live', 'polite');
  const botao = elemento('button', 'k-button k-button-blue', 'Confirmar resposta');
  botao.type = 'button';
  botao.disabled = true;
  grupo.addEventListener('change', () => { botao.disabled = false; });
  botao.addEventListener('click', () => {
    const selecionada = opcoes.findIndex(opcao => opcao.radio.checked);
    if (selecionada < 0) return;
    const acertou = selecionada === pergunta.correta;
    if (acertou) acertos++;
    opcoes.forEach((opcao, indice) => {
      opcao.radio.disabled = true;
      if (indice === pergunta.correta) opcao.label.classList.add('correta');
      else if (indice === selecionada) opcao.label.classList.add('incorreta');
    });
    feedback.classList.toggle('erro', !acertou);
    feedback.append(elemento('p', '', `${acertou ? 'Resposta correta!' : 'Ainda não.'} ${pergunta.explicacao}`));
    botao.textContent = perguntaAtual === perguntas.length - 1 ? 'Ver resultado' : 'Próxima pergunta';
    botao.onclick = () => { perguntaAtual++; renderizarQuiz(); quizConteudo.querySelector('h3')?.focus(); };
  }, { once: true });
  quizConteudo.append(feedback, botao);
}

renderizarQuiz();
