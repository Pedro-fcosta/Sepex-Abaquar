"""Teste opcional do acesso HTTP por IP e das telas móveis: pip install playwright; playwright install chromium."""

import logging
import socket
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import criar_app
from app.catalogo import gerar_configuracoes


LOTE = Path(__file__).resolve().parents[1] / 'Foguete Modular - Banco' / 'gerados' / 'csv'
ROTAS = ('/', '/montagem', '/ranking', '/dashboard', '/previa/C2-A3-F4-S2')


def ip_local():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conexao:
        conexao.connect(('192.0.2.1', 80))
        return conexao.getsockname()[0]


def verificar():
    with tempfile.TemporaryDirectory() as temporario:
        app = criar_app({'TESTING': True, 'DATABASE': str(Path(temporario) / 'mobile.sqlite3')})
        with app.app_context():
            gerar_configuracoes()
        importacao = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
        assert importacao.exit_code == 0 and '108 importadas' in importacao.output, importacao.output
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        servidor = make_server('0.0.0.0', 0, app, threaded=True)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        origem = f'http://{ip_local()}:{servidor.server_port}'
        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch(headless=True)
                contexto = navegador.new_context(viewport={'width': 360, 'height': 800}, is_mobile=True, has_touch=True, device_scale_factor=2, reduced_motion='reduce')
                pagina = contexto.new_page()
                erros = []
                pagina.on('pageerror', lambda erro: erros.append(str(erro)))
                for largura in (320, 360, 390, 430, 768):
                    pagina.set_viewport_size({'width': largura, 'height': 800})
                    for rota in ROTAS:
                        pagina.goto(origem + rota, wait_until='networkidle')
                        medidas = pagina.evaluate('''() => ({ largura: document.documentElement.scrollWidth, janela: innerWidth })''')
                        assert medidas['largura'] <= medidas['janela'] + 1, (largura, rota, medidas)
                    pagina.locator('#menu-toggle').click()
                    assert pagina.locator('#nav-principal').is_visible()
                    pagina.locator('#nav-principal a[href="/montagem"]').click()
                    assert pagina.url.endswith('/montagem')

                assert pagina.evaluate('!isSecureContext && typeof crypto.randomUUID === "undefined"')
                assert pagina.evaluate('typeof crypto.getRandomValues === "function"')
                for nome in ('Visitante Mobile', 'Outro Visitante'):
                    pagina.locator('input[name="coifa"][value="C1"]').check()
                    pagina.locator('#continuar').click()
                    pagina.locator('input[name="aleta"][value="A1"]').check()
                    pagina.locator('#continuar').click()
                    pagina.locator('input[name="secoes"][value="3"]').check()
                    pagina.locator('#continuar').click()
                    pagina.locator('#nome').fill(nome)
                    pagina.locator('#confirmar').click()
                    pagina.wait_for_url('**/voo/*')
                    pagina.wait_for_function("() => !!Chart.getChart(document.getElementById('grafico-altura'))")
                    assert pagina.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    dados = contexto.request.get(origem + pagina.locator('.voo-pagina').get_attribute('data-url')).json()
                    altura_maxima = max(ponto['altitude_m'] for ponto in dados['pontos'])
                    assert pagina.locator('#kpi-apogeu').inner_text() == f'{altura_maxima:.1f}'.replace('.', ',') + ' m'
                    pagina.evaluate('''() => { const controle = document.getElementById('tempo-graficos'); controle.value = '0'; controle.dispatchEvent(new Event('input', { bubbles: true })); }''')
                    assert pagina.locator('#marco-apogeu').is_hidden()
                    pagina.evaluate('''() => { const controle = document.getElementById('tempo-graficos'); controle.value = '1000'; controle.dispatchEvent(new Event('input', { bubbles: true })); }''')
                    assert pagina.locator('#marco-apogeu').is_visible()
                    assert pagina.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[2].data.length') == 1
                    if nome == 'Visitante Mobile':
                        pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-apogeu-mobile.png'), full_page=True)
                    pagina.locator('#ver-resultado').click()
                    assert nome in pagina.locator('h1').inner_text()
                    pagina.get_by_role('link', name='Nova participação').click()

                animada = navegador.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='no-preference')
                animada.goto(origem + '/previa/C3-A1-F5-S1', wait_until='domcontentloaded')
                animada.locator('#estado-graficos').get_by_text('Analisando a segurança do voo').wait_for()
                assert animada.locator('#aviso-aborto').is_hidden()
                animada.locator('#aviso-aborto').wait_for(state='visible', timeout=5000)
                assert animada.locator('#marco-apogeu').is_hidden()
                assert animada.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.length') > 1
                assert animada.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).options.scales.x.max') < 2
                animada.close()

                abortada = contexto.request.post(origem + '/api/tentativas', data={
                    'nome': 'Visitante Abortado', 'codigo': 'C3-A1-F5-S1',
                    'identificador_sessao': 'mobile-abortado-12345',
                })
                assert abortada.status == 201
                pagina.goto(origem + f'/resultado/{abortada.json()["id"]}', wait_until='networkidle')
                assert pagina.get_by_text('Voo não classificado').is_visible()
                assert pagina.get_by_text('Posição atual no ranking').count() == 0

                pagina.set_viewport_size({'width': 360, 'height': 800})
                pagina.goto(origem + '/dashboard', wait_until='networkidle')
                assert pagina.locator('.dashboard-metrica').first.locator('strong').inner_text() == '3'
                assert pagina.locator('.dashboard-metrica-aborto strong').inner_text() == '1'
                assert pagina.locator('#grafico-missoes').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.join(",")') == '2,1'
                assert pagina.locator('#grafico-apogeu').evaluate('(canvas) => !!Chart.getChart(canvas)')
                assert pagina.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-dashboard-mobile.png'), full_page=True)
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                assert pagina.locator('#grafico-missoes').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].backgroundColor') == ['#55d68a', '#ff7770']
                pagina.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-dashboard-mobile-dark.png'), full_page=True)
                desktop = navegador.new_page(viewport={'width': 1366, 'height': 900})
                desktop.goto(origem + '/dashboard', wait_until='networkidle')
                desktop.screenshot(path=str(Path(tempfile.gettempdir()) / 'sepex-dashboard-desktop.png'), full_page=True)
                assert not erros, erros
                navegador.close()
                print('Mobile HTTP por IP: 5 larguras, 5 rotas, 3 participações, abortagem, apogeu e dashboard OK')
        finally:
            servidor.shutdown()
            thread.join(timeout=5)


if __name__ == '__main__':
    verificar()
