const dados = JSON.parse(document.getElementById('dados-dashboard').textContent);
const graficos = [];
const histogramas = {};

function numero(valor) { return valor == null ? '—' : valor.toFixed(1); }

for (const chave of ['apogeu', 'velocidade']) {
  const hist = dados.distribuicoes[chave];
  document.getElementById(`stats-${chave}`).textContent = `Média: ${numero(hist.media)} · Mediana: ${numero(hist.mediana)} · Desvio padrão: ${numero(hist.desvio_padrao)}`;
  const grafico = new Chart(document.getElementById(`grafico-${chave}`), {
    type: 'bar',
    data: {
      labels: hist.intervalos,
      datasets: [
        { label: 'Tentativas', data: hist.contagens },
        { label: 'Normal teórica (referência)', data: hist.normal_teorica, type: 'line', hidden: true, tension: .35, pointRadius: 0, borderDash: [5, 5] },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: chave === 'apogeu' ? 'Intervalos de apogeu (m)' : 'Intervalos de velocidade (m/s)' } },
        y: { beginAtZero: true, title: { display: true, text: 'Quantidade de tentativas' } },
      },
    },
  });
  histogramas[chave] = grafico;
  graficos.push({ grafico, tipo: 'histograma' });
}

document.querySelectorAll('.curva').forEach(controle => controle.addEventListener('change', () => {
  const grafico = histogramas[controle.dataset.grafico];
  grafico.data.datasets[1].hidden = !controle.checked;
  grafico.update();
}));

const grupos = [['coifas', 'Coifas'], ['aletas', 'Aletas'], ['quantidade_aletas', 'Quantidade de aletas'], ['secoes', 'Seções do corpo']];
for (const [chave, titulo] of grupos) {
  const painel = document.createElement('div');
  const subtitulo = document.createElement('h3');
  subtitulo.textContent = titulo;
  const area = document.createElement('div');
  area.className = 'grafico';
  const canvas = document.createElement('canvas');
  area.append(canvas);
  painel.append(subtitulo, area);
  document.getElementById('graficos-grupos').append(painel);
  const valores = dados.resumo[chave];
  const grafico = new Chart(canvas, {
    type: 'bar',
    data: { labels: valores.map(item => item.opcao), datasets: [{ label: 'Apogeu médio (m)', data: valores.map(item => item.apogeu_medio_m) }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } },
  });
  graficos.push({ grafico, tipo: 'grupo' });
}

const tempo = dados.resumo.tentativas_ao_longo_do_tempo;
const graficoTempo = new Chart(document.getElementById('grafico-tempo'), {
  type: 'line',
  data: { labels: tempo.map(item => item.data), datasets: [{ label: 'Tentativas', data: tempo.map(item => item.tentativas), tension: .3 }] },
  options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
});
graficos.push({ grafico: graficoTempo, tipo: 'tempo' });

function atualizarTemaGraficos() {
  const escuro = document.documentElement.dataset.theme === 'dark';
  const texto = escuro ? '#cbd5e1' : '#5f6f89';
  const grade = escuro ? '#405168' : '#dbe3ef';
  const azul = escuro ? '#83beff' : '#0b5fc0';
  const azulSecundario = escuro ? '#d1e5ff' : '#003f91';
  for (const { grafico, tipo } of graficos) {
    grafico.options.plugins.legend.labels.color = texto;
    for (const escala of Object.values(grafico.options.scales)) {
      escala.ticks.color = texto;
      escala.grid.color = grade;
      escala.title.color = texto;
    }
    grafico.data.datasets[0].backgroundColor = tipo === 'tempo' ? `${azul}33` : azul;
    grafico.data.datasets[0].borderColor = azul;
    if (tipo === 'histograma') grafico.data.datasets[1].borderColor = azulSecundario;
    grafico.update();
  }
}

atualizarTemaGraficos();
document.addEventListener('sepex:themechange', atualizarTemaGraficos);
