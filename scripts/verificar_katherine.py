"""Verifica a página educativa em Chromium: python -m scripts.verificar_katherine."""

import logging
import math
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import criar_app


def verificar():
    with tempfile.TemporaryDirectory() as temporario:
        app = criar_app({'TESTING': True, 'DATABASE': str(Path(temporario) / 'katherine.sqlite3')})
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        servidor = make_server('127.0.0.1', 0, app, threaded=True)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        origem = f'http://127.0.0.1:{servidor.server_port}'
        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch(headless=True)
                contexto = navegador.new_context(reduced_motion='reduce')
                pagina = contexto.new_page()
                erros = []
                pagina.on('pageerror', lambda erro: erros.append(str(erro)))
                for largura in (320, 390, 768, 1121, 1192, 1366):
                    pagina.set_viewport_size({'width': largura, 'height': 900})
                    pagina.goto(origem + '/katherine', wait_until='networkidle')
                    assert pagina.get_by_role('heading', name='Katherine Johnson').is_visible()
                    assert pagina.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), largura
                    if largura >= 1121:
                        assert pagina.locator('.nav-principal').evaluate(
                            '(nav) => nav.getBoundingClientRect().right < document.querySelector(".logo-cefet").getBoundingClientRect().left'
                        ), largura
                    assert pagina.locator('#k-trajetoria-linha').get_attribute('d').startswith('M')
                    assert pagina.locator('#k-altura').inner_text() == '107,7 m'
                    pagina.locator('.k-legado img').scroll_into_view_if_needed()
                    pagina.wait_for_function("() => document.querySelector('.k-legado img').complete && document.querySelector('.k-legado img').naturalWidth > 0")
                    pagina.locator('.k-retrato img').scroll_into_view_if_needed()
                    pagina.wait_for_function("() => document.querySelector('.k-retrato img').complete && document.querySelector('.k-retrato img').naturalWidth > 0")
                    pagina.evaluate('scrollTo(0, 0)')
                    if largura == 390:
                        pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-katherine-mobile.png'), full_page=True)
                        pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-katherine-mobile-hero.png'))
                    if largura == 1366:
                        pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-katherine-desktop.png'), full_page=True)
                        pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-katherine-desktop-hero.png'))

                pagina.locator('#k-velocidade').evaluate("el => { el.value = '80'; el.dispatchEvent(new Event('input', { bubbles: true })); }")
                pagina.locator('#k-angulo').evaluate("el => { el.value = '30'; el.dispatchEvent(new Event('input', { bubbles: true })); }")
                altura = 80 ** 2 * math.sin(math.radians(30)) ** 2 / (2 * 9.81)
                assert pagina.locator('#k-altura').inner_text() == f'{altura:.1f}'.replace('.', ',') + ' m'
                pagina.locator('#k-reiniciar').click()
                assert pagina.locator('#k-velocidade').input_value() == '65'
                assert pagina.locator('#k-angulo').input_value() == '45'

                for resposta in (1, 0, 2):
                    pagina.locator(f'.k-quiz-opcao input[value="{resposta}"]').check()
                    pagina.get_by_role('button', name='Confirmar resposta').click()
                    assert pagina.get_by_text('Resposta correta!', exact=False).is_visible()
                    pagina.get_by_role('button', name='Ver resultado' if resposta == 2 else 'Próxima pergunta').click()
                assert pagina.get_by_text('3 / 3').is_visible()
                pagina.get_by_role('button', name='Refazer quiz').click()
                assert pagina.get_by_text('PERGUNTA 1 DE 3').is_visible()
                pagina.locator('.k-quiz-opcao input[value="0"]').check()
                pagina.get_by_role('button', name='Confirmar resposta').click()
                assert pagina.get_by_text('Ainda não.', exact=False).is_visible()
                assert pagina.locator('.k-quiz-opcao.correta').count() == 1

                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-katherine-dark.png'), full_page=True)
                assert pagina.locator('.k-hero-foto img').evaluate('(img) => img.complete && img.naturalWidth > 0')
                pagina.goto(origem, wait_until='networkidle')
                pagina.get_by_role('link', name='Conheça Katherine').click()
                assert pagina.url.endswith('/katherine')
                assert not erros, erros
                navegador.close()
                print('Katherine: 6 larguras, navegação, cálculo balístico, reinício, quiz, fotos e tema escuro OK')
        finally:
            servidor.shutdown()
            thread.join(timeout=5)


if __name__ == '__main__':
    verificar()
