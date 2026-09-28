const botaoTema = document.getElementById('tema');
const menuToggle = document.getElementById('menu-toggle');
const navPrincipal = document.getElementById('nav-principal');
const logoAbaquar = document.getElementById('logo-abaquar');

function atualizarBotaoTema() {
  const escuro = document.documentElement.dataset.theme === 'dark';
  botaoTema.querySelector('.tema-icone').textContent = escuro ? '☀️' : '🌙';
  botaoTema.querySelector('.tema-texto').textContent = escuro ? 'Tema claro' : 'Tema escuro';
  botaoTema.setAttribute('aria-label', escuro ? 'Ativar tema claro' : 'Ativar tema escuro');
}

function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  try { localStorage.setItem('sepex-theme', tema); } catch (_) { /* Modo privado. */ }
  atualizarBotaoTema();
  document.dispatchEvent(new CustomEvent('sepex:themechange', { detail: { tema } }));
}

atualizarBotaoTema();
botaoTema.addEventListener('click', () => {
  aplicarTema(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
});

function fecharMenu() {
  navPrincipal.classList.remove('aberta');
  menuToggle.setAttribute('aria-expanded', 'false');
  menuToggle.setAttribute('aria-label', 'Abrir menu');
}

menuToggle.addEventListener('click', () => {
  const aberto = menuToggle.getAttribute('aria-expanded') === 'true';
  navPrincipal.classList.toggle('aberta', !aberto);
  menuToggle.setAttribute('aria-expanded', String(!aberto));
  menuToggle.setAttribute('aria-label', aberto ? 'Abrir menu' : 'Fechar menu');
});
navPrincipal.querySelectorAll('a').forEach(link => link.addEventListener('click', fecharMenu));
document.addEventListener('keydown', evento => { if (evento.key === 'Escape') fecharMenu(); });

function ocultarLogoAusente() {
  logoAbaquar.closest('.marca-logo').classList.add('sem-logo');
}
logoAbaquar.addEventListener('error', ocultarLogoAusente);
if (logoAbaquar.complete && !logoAbaquar.naturalWidth) ocultarLogoAusente();
