const dados = JSON.parse(document.getElementById('dados-dashboard').textContent);
const graficos = [];

function numero(valor) { return valor == null ? '—' : valor.toFixed(1).replace('.', ','); }

for (const chave of ['apogeu', 'velocidade']) {
  const hist = dados.distribuicoes[chave];
  document.getElementById(`stats-${chave}`).textContent = `Média ${numero(hist.media)} · Mediana ${numero(hist.mediana)} · Desvio ${numero(hist.desvio_padrao)}`;
  const grafico = new Chart(document.getElementById(`grafico-${chave}`), {
    type: 'bar',
    data: {
      labels: hist.intervalos,
      datasets: [
        { label: 'Tentativas', data: hist.contagens },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { title: itens => `Faixa ${itens[0]?.label || ''}`, label: item => `${item.parsed.y} ${item.parsed.y === 1 ? 'participação' : 'participações'}` } } },
      scales: {
        x: { ticks: { maxRotation: 45, minRotation: 0, autoSkip: true, maxTicksLimit: 5 }, title: { display: true, text: chave === 'apogeu' ? 'Altura (m)' : 'Velocidade (m/s)' } },
        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Participações' } },
      },
    },
  });
  graficos.push({ grafico, tipo: 'histograma' });
}

const grupos = [['coifas', 'Coifas'], ['aletas', 'Aletas'], ['quantidade_aletas', 'Quantidade de aletas'], ['secoes', 'Seções do corpo']];
for (const [chave, titulo] of grupos) {
  const painel = document.createElement('article');
  painel.className = 'painel dashboard-grupo-card';
  const subtitulo = document.createElement('h3');
  subtitulo.textContent = titulo;
  const descricao = document.createElement('p');
  descricao.textContent = 'Apogeu médio (m) · número de escolhas ao passar o dedo ou cursor';
  const area = document.createElement('div');
  area.className = 'grafico';
  const canvas = document.createElement('canvas');
  area.append(canvas);
  painel.append(subtitulo, descricao, area);
  document.getElementById('graficos-grupos').append(painel);
  const valores = dados.resumo[chave];
  const grafico = new Chart(canvas, {
    type: 'bar',
    data: { labels: valores.map(item => item.opcao), datasets: [{ label: 'Apogeu médio (m)', data: valores.map(item => item.apogeu_medio_m) }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: item => `${numero(item.parsed.x)} m · ${valores[item.dataIndex].tentativas} ${valores[item.dataIndex].tentativas === 1 ? 'escolha' : 'escolhas'}` } } },
      scales: { x: { beginAtZero: true, title: { display: true, text: 'Apogeu médio (m)' } }, y: { grid: { display: false } } } },
  });
  graficos.push({ grafico, tipo: 'grupo' });
}

const tempo = dados.resumo.tentativas_ao_longo_do_tempo;
const graficoTempo = new Chart(document.getElementById('grafico-tempo'), {
  type: 'bar',
  data: { labels: tempo.map(item => { const [dia, hora] = item.data.split(' '); return `${dia.slice(8, 10)}/${dia.slice(5, 7)} ${hora.slice(0, 2)}h`; }), datasets: [{ label: 'Participações', data: tempo.map(item => item.tentativas), borderRadius: 5 }] },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 7 } }, y: { beginAtZero: true, ticks: { precision: 0 } } } },
});
graficos.push({ grafico: graficoTempo, tipo: 'tempo' });

function atualizarTemaGraficos() {
  const escuro = document.documentElement.dataset.theme === 'dark';
  const texto = escuro ? '#cbd5e1' : '#5f6f89';
  const grade = escuro ? '#405168' : '#dbe3ef';
  const azul = escuro ? '#83beff' : '#0b5fc0';
  for (const { grafico, tipo } of graficos) {
    grafico.options.plugins.legend.labels.color = texto;
    for (const escala of Object.values(grafico.options.scales)) {
      escala.ticks.color = texto;
      escala.grid.color = grade;
      escala.title.color = texto;
    }
    grafico.data.datasets[0].backgroundColor = tipo === 'tempo' ? `${azul}33` : azul;
    grafico.data.datasets[0].borderColor = azul;
    if (tipo === 'histograma') grafico.data.datasets[0].borderRadius = 5;
    grafico.update();
  }
}

atualizarTemaGraficos();
document.addEventListener('sepex:themechange', atualizarTemaGraficos);
