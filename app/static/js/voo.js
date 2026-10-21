const paginaVoo = document.querySelector('.voo-pagina');
const botaoReproduzir = document.getElementById('reproduzir-graficos');
const botaoReiniciar = document.getElementById('reiniciar-graficos');
const controleTempo = document.getElementById('tempo-graficos');
const estadoGraficos = document.getElementById('estado-graficos');
const graficosVoo = [];
const movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const avisoAborto = document.getElementById('aviso-aborto');
const margemMinima = Number(paginaVoo.dataset.margemMinima);

let serieVoo = [];
let duracaoVoo = 0;
let limiteVoo = 0;
let missaoAbortada = false;
let progressoVoo = 0;
let reproduzindo = false;
let quadroPendente = 0;
let inicioReproducao = 0;
let baseReproducao = 0;
let ultimoDesenho = 0;
let apogeuVoo = null;
let resultadoParcial = false;

function numero(valor, casas = 1) {
  return Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function indicador(valor) {
  return valor == null || !Number.isFinite(Number(valor)) ? null : Number(valor);
}

function textoBotao(rotulo, icone = 'play') {
  botaoReproduzir.querySelector('.voo-botao-texto').textContent = rotulo;
  botaoReproduzir.setAttribute('aria-label', `${rotulo} simulação`);
  document.getElementById('icone-reproducao').setAttribute('href', `#icone-${icone}`);
}

function preencherIndicadores(temSerie, tentativa) {
  const trecho = serieVoo.filter(ponto => ponto.tempo <= limiteVoo);
  if (missaoAbortada && trecho.at(-1)?.tempo < limiteVoo) trecho.push(amostraNoTempo(limiteVoo, indiceAte(limiteVoo)));
  const velocidades = (missaoAbortada ? trecho : serieVoo).map(ponto => ponto.velocidade).filter(Number.isFinite);
  const velocidadeMaxima = temSerie ? velocidades.length ? Math.max(...velocidades) : null : missaoAbortada ? null : indicador(tentativa.velocidade_max_ms);
  const apogeu = missaoAbortada ? null : temSerie ? indicador(apogeuVoo?.altura) : indicador(tentativa.apogeu_m);
  const tempoApogeu = missaoAbortada ? null : temSerie ? indicador(apogeuVoo?.tempo) : indicador(tentativa.tempo_apogeu_s);
  const duracao = missaoAbortada ? temSerie ? limiteVoo : null : temSerie ? duracaoVoo : indicador(tentativa.duracao_s);
  const rotuloAltura = missaoAbortada ? 'Altitude no aborto' : resultadoParcial ? 'Maior altura registrada' : 'Apogeu máximo';
  document.getElementById('rotulo-kpi-apogeu').textContent = rotuloAltura;
  document.getElementById('rotulo-max-altura').textContent = rotuloAltura;
  document.getElementById('rotulo-kpi-duracao').textContent = missaoAbortada ? 'Trecho exibido' : resultadoParcial ? 'Tempo registrado' : 'Tempo total do voo';
  document.getElementById('rotulo-kpi-tempo-apogeu').textContent = missaoAbortada ? 'Tempo até o apogeu' : resultadoParcial ? 'Tempo até maior altura' : 'Tempo até o apogeu';
  const alturaExibida = missaoAbortada ? temSerie ? trecho.at(-1)?.altura : null : apogeu;
  const textoAltura = Number.isFinite(alturaExibida) ? `${numero(alturaExibida)} m` : 'Indisponível';
  const textoVelocidade = Number.isFinite(velocidadeMaxima) ? `${numero(velocidadeMaxima)} m/s` : 'Indisponível';
  document.getElementById('kpi-apogeu').textContent = textoAltura;
  document.getElementById('altura-maxima').textContent = textoAltura;
  document.getElementById('kpi-velocidade').textContent = textoVelocidade;
  document.getElementById('velocidade-maxima').textContent = textoVelocidade;
  document.getElementById('kpi-duracao').textContent = Number.isFinite(duracao) ? `${numero(duracao)} s` : 'Indisponível';
  document.getElementById('kpi-tempo-apogeu').textContent = Number.isFinite(tempoApogeu) ? `${numero(tempoApogeu)} s` : missaoAbortada ? 'Não atingido' : 'Indisponível';
  document.getElementById('tempo-total').textContent = `${numero(limiteVoo)} s`;
  document.getElementById('insight-apogeu-titulo').textContent = missaoAbortada ? 'Operação abortada' : rotuloAltura;
  document.getElementById('insight-apogeu').textContent = missaoAbortada
    ? `Estabilidade abaixo de ${numero(margemMinima, 2)} cal`
    : tempoApogeu == null ? textoAltura : `${textoAltura} em ${numero(tempoApogeu)} s`;
  document.getElementById('insight-duracao-titulo').textContent = missaoAbortada ? 'Trecho inicial' : resultadoParcial ? 'Tempo registrado' : 'Duração da simulação';
  document.getElementById('insight-duracao').textContent = duracao == null ? 'Indisponível' : `${numero(duracao)} s`;
  document.getElementById('insight-dados').textContent = tentativa.demonstrativo ? 'Dados de demonstração' : temSerie ? 'Série temporal OpenRocket' : 'Curva ilustrativa';
}

function coresGraficos() {
  const escuro = document.documentElement.dataset.theme === 'dark';
  return {
    texto: escuro ? '#cbd5e1' : '#5f6f89',
    grade: escuro ? '#405168' : '#dbe3ef',
    altura: escuro ? '#83beff' : '#0866d9',
    velocidade: escuro ? '#a9d2ff' : '#0866d9',
    apogeu: escuro ? '#fbd38d' : '#df9a13',
  };
}

function criarGrafico(id, nome, unidade, dados, minimo, maximo) {
  const cores = coresGraficos();
  const cor = cores[nome];
  const grafico = new Chart(document.getElementById(id), {
    type: 'line',
    data: { datasets: [
      { label: nome === 'altura' ? 'Altitude' : 'Velocidade', data: [], parsing: false, borderColor: cor, backgroundColor: `${cor}20`, borderWidth: 2.7, pointRadius: 0, tension: 0, fill: true },
      { label: 'Instante atual', data: [], parsing: false, borderColor: cor, backgroundColor: cor, pointRadius: 5, pointHoverRadius: 6, showLine: false },
      ...(nome === 'altura' ? [
        { label: 'Apogeu', data: [], parsing: false, borderColor: cores.apogeu, backgroundColor: cores.apogeu, pointRadius: 7, pointHoverRadius: 9, pointStyle: 'triangle', showLine: false },
        { label: 'Instante do apogeu', data: [], parsing: false, borderColor: cores.apogeu, borderDash: [5, 5], borderWidth: 1.5, pointRadius: 0, fill: false },
      ] : []),
    ] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { intersect: false, mode: 'nearest' },
      plugins: { legend: { display: false }, tooltip: { backgroundColor: cores.texto === '#cbd5e1' ? '#0c182a' : '#082b5c', padding: 10, cornerRadius: 8, callbacks: { title: items => `Tempo: ${numero(items[0].parsed.x)} s`, label: item => `${item.dataset.label}: ${numero(item.parsed.y)} ${unidade}` } } },
      scales: {
        x: { type: 'linear', min: 0, max: limiteVoo, title: { display: true, text: 'Tempo (s)', color: cores.texto }, ticks: { color: cores.texto, maxTicksLimit: 7 }, grid: { color: cores.grade } },
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
    grafico.data.datasets[0].backgroundColor = `${cor}20`;
    grafico.data.datasets[1].borderColor = cor;
    grafico.data.datasets[1].backgroundColor = cor;
    if (nome === 'altura') {
      grafico.data.datasets[2].borderColor = cores.apogeu;
      grafico.data.datasets[2].backgroundColor = cores.apogeu;
      grafico.data.datasets[3].borderColor = cores.apogeu;
    }
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
  tempo = Math.min(tempo, limiteVoo);
  const indice = indiceAte(tempo);
  const atual = amostraNoTempo(tempo, indice);
  progressoVoo = limiteVoo ? tempo / limiteVoo : 1;
  controleTempo.value = String(Math.round(progressoVoo * 1000));
  document.getElementById('tempo-atual').textContent = `${numero(tempo)} s`;
  controleTempo.style.setProperty('--voo-progresso', `${progressoVoo * 100}%`);
  document.getElementById('altura-atual').textContent = `${numero(atual.altura)} m agora`;
  document.getElementById('velocidade-atual').textContent = atual.velocidade == null ? 'Sem dados agora' : `${numero(atual.velocidade)} m/s agora`;
  const apogeuAtingido = !missaoAbortada && apogeuVoo && tempo >= apogeuVoo.tempo;
  document.getElementById('marco-apogeu').hidden = !apogeuAtingido;
  for (const { grafico, nome, dados } of graficosVoo) {
    const valor = atual[nome];
    grafico.data.datasets[0].data = [...dados.slice(0, indice), ...(indice < dados.length && tempo > dados[Math.max(0, indice - 1)].x ? [{ x: tempo, y: valor }] : [])];
    grafico.data.datasets[1].data = valor == null ? [] : [{ x: tempo, y: valor }];
    if (nome === 'altura') {
      grafico.data.datasets[2].data = apogeuAtingido ? [{ x: apogeuVoo.tempo, y: apogeuVoo.altura }] : [];
      grafico.data.datasets[3].data = apogeuAtingido ? [{ x: apogeuVoo.tempo, y: 0 }, { x: apogeuVoo.tempo, y: apogeuVoo.altura }] : [];
    }
    grafico.update('none');
  }
}

function pausar() {
  if (quadroPendente) cancelAnimationFrame(quadroPendente);
  quadroPendente = 0;
  reproduzindo = false;
  textoBotao('Reproduzir');
  estadoGraficos.textContent = 'Animação pausada';
}

function finalizarAborto() {
  reproduzindo = false;
  quadroPendente = 0;
  avisoAborto.hidden = false;
  textoBotao('Rever início');
  estadoGraficos.textContent = `Missão abortada por estabilidade inferior a ${margemMinima.toFixed(2).replace('.', ',')} calibre`;
}

function reproduzir() {
  if (movimentoReduzido) {
    mostrarTempo(limiteVoo);
    if (missaoAbortada) finalizarAborto();
    else estadoGraficos.textContent = 'Gráficos completos';
    return;
  }
  if (progressoVoo >= 1) {
    mostrarTempo(0);
    if (missaoAbortada) avisoAborto.hidden = true;
  }
  baseReproducao = progressoVoo;
  inicioReproducao = performance.now();
  ultimoDesenho = 0;
  reproduzindo = true;
  textoBotao('Pausar', 'pausa');
  estadoGraficos.textContent = missaoAbortada ? 'Analisando a segurança do voo' : 'Reproduzindo gráficos';
  function animar(agora) {
    if (!reproduzindo) return;
    const progresso = Math.min(1, baseReproducao + (agora - inicioReproducao) / (missaoAbortada ? 1800 : 7000));
    if (agora - ultimoDesenho >= 50 || progresso === 1) {
      mostrarTempo(progresso * limiteVoo);
      ultimoDesenho = agora;
    }
    if (progresso < 1) quadroPendente = requestAnimationFrame(animar);
    else {
      if (missaoAbortada) finalizarAborto();
      else {
        reproduzindo = false;
        quadroPendente = 0;
        textoBotao('Reproduzir novamente');
        estadoGraficos.textContent = 'Gráficos completos';
      }
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
    apogeuVoo = serieVoo.reduce((pico, ponto) => ponto.altura > pico.altura ? ponto : pico, serieVoo[0]);
    missaoAbortada = Boolean(dados.tentativa.abortada);
    limiteVoo = missaoAbortada
      ? Math.max(.05, Math.min(1.5, apogeuVoo.tempo * .22, duracaoVoo * .1))
      : duracaoVoo;
    if (missaoAbortada) {
      document.getElementById('rotulo-tempo').textContent = 'Trecho inicial';
      controleTempo.setAttribute('aria-label', 'Posição no trecho inicial antes da abortagem');
    }
    resultadoParcial = temSerie && serieVoo.at(-1).altura > 0.5;
    const rotuloApogeu = resultadoParcial ? 'Maior altura registrada' : 'Apogeu atingido';
    document.getElementById('marco-apogeu-rotulo').textContent = rotuloApogeu;
    document.getElementById('marco-apogeu-valor').textContent = `${apogeuVoo.altura.toFixed(1).replace('.', ',')} m · ${apogeuVoo.tempo.toFixed(1).replace('.', ',')} s`;
    document.getElementById('tipo-trajetoria').textContent = temSerie
      ? 'Gráficos baseados na série temporal importada do OpenRocket.'
      : 'Curvas ilustrativas geradas apenas para visualização. Os indicadores registrados não foram alterados.';
    preencherIndicadores(temSerie, dados.tentativa);
    const pontosExibidos = missaoAbortada ? serieVoo.slice(0, indiceAte(limiteVoo) + 1) : serieVoo;
    const alturas = pontosExibidos.map(p => p.altura);
    const velocidades = pontosExibidos.map(p => p.velocidade).filter(Number.isFinite);
    const maxAltura = Math.ceil(Math.max(1, ...alturas) * 1.08 / 10) * 10;
    const minVelocidade = Math.floor(Math.min(0, ...velocidades) * 1.1 / 10) * 10;
    const maxVelocidade = Math.ceil(Math.max(1, ...velocidades) * 1.1 / 10) * 10;
    criarGrafico('grafico-altura', 'altura', 'm', serieVoo.map(p => ({ x: p.tempo, y: p.altura })), 0, maxAltura);
    graficosVoo[0].grafico.data.datasets[2].label = rotuloApogeu;
    criarGrafico('grafico-velocidade', 'velocidade', 'm/s', serieVoo.map(p => ({ x: p.tempo, y: p.velocidade })), minVelocidade, maxVelocidade);
    botaoReproduzir.disabled = false;
    botaoReiniciar.disabled = false;
    controleTempo.disabled = false;
    mostrarTempo(0);
    if (movimentoReduzido) {
      mostrarTempo(limiteVoo);
      if (missaoAbortada) finalizarAborto();
      else {
        textoBotao('Gráficos completos');
        estadoGraficos.textContent = 'Gráficos completos';
      }
      botaoReproduzir.disabled = true;
      botaoReiniciar.disabled = true;
    } else reproduzir();
  } catch (erro) {
    estadoGraficos.textContent = erro.message || 'Erro ao carregar os gráficos.';
    document.getElementById('tipo-trajetoria').textContent = 'Tente recarregar a página.';
  }
}

botaoReproduzir.addEventListener('click', () => reproduzindo ? pausar() : reproduzir());
botaoReiniciar.addEventListener('click', () => {
  if (reproduzindo) pausar();
  mostrarTempo(0);
  avisoAborto.hidden = true;
  textoBotao('Reproduzir');
  estadoGraficos.textContent = 'Pronto para reproduzir';
});
controleTempo.addEventListener('input', () => {
  if (reproduzindo) pausar();
  mostrarTempo(Number(controleTempo.value) / 1000 * limiteVoo);
  if (missaoAbortada && progressoVoo >= 1) finalizarAborto();
  else estadoGraficos.textContent = 'Posição ajustada na linha do tempo';
});
document.addEventListener('sepex:themechange', atualizarTemaGraficos);
iniciarGraficos();
