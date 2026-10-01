try {
  if (localStorage.getItem('sepex-theme') === 'dark') {
    document.documentElement.dataset.theme = 'dark';
  }
} catch (_) {
  // O tema claro permanece disponível quando o armazenamento local está bloqueado.
}
