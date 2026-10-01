const paginaVoo = document.querySelector('.voo-pagina');
const botaoReproduzir = document.getElementById('reproduzir-graficos');
const controleTempo = document.getElementById('tempo-graficos');
const estadoGraficos = document.getElementById('estado-graficos');
const graficosVoo = [];
const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

let serieVoo = [];
let duracaoVoo = 0;
let progressoVoo = 0;
let reproduzindo = false;
let quadroPendente = 0;
let inicioReproducao = 0;
let baseReproducao = 0;
let ultimoDesenho = 0;

function coresGraficos() {
  const escuro = document.documentElement.dataset.theme === 'dark';
  return {
    texto: escuro ? '#cbd5e1' : '#5f6f89',
    grade: escuro ? '#405168' : '#dbe3ef',
    altura: escuro ? '#83beff' : '#003f91',
    velocidade: escuro ? '#d1e5ff' : '#0b5fc0',
  };
}

function criarGrafico(id, nome, unidade, dados, minimo, maximo) {
  const cores = coresGraficos();
  const cor = cores[nome];
  const grafico = new Chart(document.getElementById(id), {
    type: 'line',
    data: { datasets: [
      { label: nome === 'altura' ? 'Altura' : 'Velocidade vertical', data: [], parsing: false, borderColor: cor, backgroundColor: `${cor}22`, borderWidth: 3, pointRadius: 0, tension: 0, fill: nome === 'altura' },
      { label: 'Instante atual', data: [], parsing: false, borderColor: cor, backgroundColor: cor, pointRadius: 5, pointHoverRadius: 6, showLine: false },
    ] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: item => `${item.dataset.label}: ${Number(item.parsed.y).toFixed(1)} ${unidade}` } } },
      scales: {
        x: { type: 'linear', min: 0, max: duracaoVoo, title: { display: true, text: 'Tempo (s)', color: cores.texto }, ticks: { color: cores.texto, maxTicksLimit: 7 }, grid: { color: cores.grade } },
        y: { min: minimo, max: maximo, title: { display: true, text: `${nome === 'altura' ? 'Altura' : 'Velocidade'} (${unidade})`, color: cores.texto }, ticks: { color: cores.texto, maxTicksLimit: 7 }, grid: { color: cores.grade } },
      },
    },
  });
  graficosVoo.push({ grafico, nome, dados });
  return grafico;
}

function atualizarTemaGraficos() {
  const cores = coresGraficos();
  for (const { grafico, nome } of graficosVoo) {
    const cor = cores[nome];
    grafico.data.datasets[0].borderColor = cor;
    grafico.data.datasets[0].backgroundColor = `${cor}22`;
    grafico.data.datasets[1].borderColor = cor;
    grafico.data.datasets[1].backgroundColor = cor;
    for (const escala of Object.values(grafico.options.scales)) {
      escala.title.color = cores.texto;
      escala.ticks.color = cores.texto;
      escala.grid.color = cores.grade;
    }
    grafico.update('none');
  }
}

function pontosIlustrativos(tentativa) {
  const apogeu = Math.max(0, Number(tentativa.apogeu_m) || 0);
  const tempoPico = Math.max(.1, Number(tentativa.tempo_apogeu_s) || 7);
  const duracao = Math.max(tempoPico + .1, Number(tentativa.duracao_s) || tempoPico * 1.5);
  return Array.from({ length: 121 }, (_, indice) => {
    const tempo = indice * duracao / 120;
    const subida = tempo <= tempoPico;
    const intervalo = subida ? tempoPico : duracao - tempoPico;
    const fracao = (tempo - tempoPico) / intervalo;
    return {
      tempo, altura: apogeu * Math.max(0, 1 - fracao * fracao),
      velocidade: -2 * apogeu * fracao / intervalo,
    };
  });
}

function indiceAte(tempo) {
  let inicio = 0;
  let fim = serieVoo.length;
  while (inicio < fim) {
    const meio = (inicio + fim) >> 1;
    if (serieVoo[meio].tempo <= tempo) inicio = meio + 1;
    else fim = meio;
  }
  return inicio;
}

function amostraNoTempo(tempo, indice) {
  if (indice === 0) return serieVoo[0];
  if (indice >= serieVoo.length) return serieVoo.at(-1);
  const anterior = serieVoo[indice - 1];
  const seguinte = serieVoo[indice];
  const fator = (tempo - anterior.tempo) / (seguinte.tempo - anterior.tempo);
  return {
    tempo,
    altura: anterior.altura + (seguinte.altura - anterior.altura) * fator,
    velocidade: anterior.velocidade == null || seguinte.velocidade == null
      ? null : anterior.velocidade + (seguinte.velocidade - anterior.velocidade) * fator,
  };
}

function mostrarTempo(tempo) {
  const indice = indiceAte(tempo);
  const atual = amostraNoTempo(tempo, indice);
  progressoVoo = duracaoVoo ? tempo / duracaoVoo : 1;
  controleTempo.value = String(Math.round(progressoVoo * 1000));
  document.getElementById('tempo-atual').textContent = `${tempo.toFixed(1).replace('.', ',')} s`;
  document.getElementById('altura-atual').textContent = `${Math.round(atual.altura)} m`;
  document.getElementById('velocidade-atual').textContent = atual.velocidade == null ? 'Sem dados' : `${atual.velocidade.toFixed(1).replace('.', ',')} m/s`;
  for (const { grafico, nome, dados } of graficosVoo) {
    const valor = atual[nome];
    grafico.data.datasets[0].data = dados.slice(0, indice);
    grafico.data.datasets[1].data = valor == null ? [] : [{ x: tempo, y: valor }];
    grafico.update('none');
  }
}

function pausar() {
  if (quadroPendente) cancelAnimationFrame(quadroPendente);
  quadroPendente = 0;
  reproduzindo = false;
  botaoReproduzir.textContent = 'Reproduzir';
  estadoGraficos.textContent = 'Animação pausada';
}

function reproduzir() {
  if (movimentoReduzido) {
    mostrarTempo(duracaoVoo);
    estadoGraficos.textContent = 'Gráficos completos';
    return;
  }
  if (progressoVoo >= 1) mostrarTempo(0);
  baseReproducao = progressoVoo;
  inicioReproducao = performance.now();
  ultimoDesenho = 0;
  reproduzindo = true;
  botaoReproduzir.textContent = 'Pausar';
  estadoGraficos.textContent = 'Reproduzindo gráficos';
  function animar(agora) {
    if (!reproduzindo) return;
    const progresso = Math.min(1, baseReproducao + (agora - inicioReproducao) / 7000);
    if (agora - ultimoDesenho >= 50 || progresso === 1) {
      mostrarTempo(progresso * duracaoVoo);
      ultimoDesenho = agora;
    }
    if (progresso < 1) quadroPendente = requestAnimationFrame(animar);
    else {
      reproduzindo = false;
      quadroPendente = 0;
      botaoReproduzir.textContent = 'Reproduzir novamente';
      estadoGraficos.textContent = 'Gráficos completos';
    }
  }
  quadroPendente = requestAnimationFrame(animar);
}

async function iniciarGraficos() {
  try {
    const resposta = await fetch(paginaVoo.dataset.url);
    if (!resposta.ok) throw new Error('Não foi possível carregar os dados do voo.');
    const dados = await resposta.json();
    const temSerie = dados.pontos.length > 1;
    serieVoo = temSerie
      ? dados.pontos.map(p => ({ tempo: p.tempo_s, altura: p.altitude_m, velocidade: p.velocidade_ms }))
      : pontosIlustrativos(dados.tentativa);
    duracaoVoo = serieVoo.at(-1).tempo;
    document.getElementById('tipo-trajetoria').textContent = temSerie
      ? 'Gráficos baseados na série temporal importada do OpenRocket.'
      : 'Curvas ilustrativas geradas apenas para visualização. Os indicadores registrados não foram alterados.';
    const alturas = serieVoo.map(p => p.altura);
    const velocidades = serieVoo.map(p => p.velocidade).filter(Number.isFinite);
    const maxAltura = Math.ceil(Math.max(1, ...alturas) * 1.08 / 10) * 10;
    const minVelocidade = Math.floor(Math.min(0, ...velocidades) * 1.1 / 10) * 10;
    const maxVelocidade = Math.ceil(Math.max(1, ...velocidades) * 1.1 / 10) * 10;
    criarGrafico('grafico-altura', 'altura', 'm', serieVoo.map(p => ({ x: p.tempo, y: p.altura })), 0, maxAltura);
    criarGrafico('grafico-velocidade', 'velocidade', 'm/s', serieVoo.map(p => ({ x: p.tempo, y: p.velocidade })), minVelocidade, maxVelocidade);
    botaoReproduzir.disabled = false;
    controleTempo.disabled = false;
    mostrarTempo(0);
    if (movimentoReduzido) {
      mostrarTempo(duracaoVoo);
      botaoReproduzir.textContent = 'Gráficos completos';
      botaoReproduzir.disabled = true;
      estadoGraficos.textContent = 'Gráficos completos';
    } else reproduzir();
  } catch (erro) {
    estadoGraficos.textContent = erro.message || 'Erro ao carregar os gráficos.';
    document.getElementById('tipo-trajetoria').textContent = 'Tente recarregar a página.';
  }
}

botaoReproduzir.addEventListener('click', () => reproduzindo ? pausar() : reproduzir());
controleTempo.addEventListener('input', () => {
  if (reproduzindo) pausar();
  mostrarTempo(Number(controleTempo.value) / 1000 * duracaoVoo);
  estadoGraficos.textContent = 'Posição ajustada na linha do tempo';
});
document.addEventListener('sepex:themechange', atualizarTemaGraficos);
iniciarGraficos();
