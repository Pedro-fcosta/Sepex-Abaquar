"""Verificação opcional do frontend em Chromium: pip install playwright; playwright install chromium."""

import json
import logging
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import criar_app
from app.db import conexao


RESOLUCOES = [(1920, 1080), (1366, 768), (1024, 768), (768, 1024), (390, 844)]
CAPTURAS = Path('data/exports/qa')
LOTE = Path('Foguete Modular - Banco/.csv')


def verificar():
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporario:
        app = criar_app({'TESTING': True, 'DATABASE': str(Path(temporario) / 'interface.sqlite3')})
        resultado = app.test_cli_runner().invoke(args=['demo-criar'])
        assert resultado.exit_code == 0, resultado.output
        resultado = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
        assert resultado.exit_code == 0, resultado.output
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        servidor = make_server('127.0.0.1', 0, app, threaded=True)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        origem = f'http://127.0.0.1:{servidor.server_port}'
        falhas = []
        externas = []
        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch(headless=True)
                contexto = navegador.new_context(reduced_motion='reduce')
                pagina = contexto.new_page()
                pagina.on('pageerror', lambda erro: falhas.append(str(erro)))
                pagina.on('console', lambda mensagem: falhas.append(mensagem.text) if mensagem.type == 'error' else None)
                pagina.on('request', lambda req: externas.append(req.url) if not req.url.startswith(origem) else None)

                for largura, altura in RESOLUCOES:
                    pagina.set_viewport_size({'width': largura, 'height': altura})
                    for rota in ('/', '/montagem'):
                        pagina.goto(origem + rota, wait_until='networkidle')
                        assert pagina.locator('html').get_attribute('data-theme') == 'light'
                        medidas = pagina.evaluate('''() => ({
                            largura: document.documentElement.scrollWidth,
                            janela: innerWidth,
                            titulo: document.querySelector('h1').getBoundingClientRect().top,
                            cabecalho: document.querySelector('header').getBoundingClientRect().bottom,
                        })''')
                        assert medidas['largura'] <= medidas['janela'] + 1, (largura, rota, medidas)
                        assert medidas['titulo'] >= medidas['cabecalho'], (largura, rota, medidas)
                        assert pagina.locator('#logo-abaquar').evaluate('(img) => img.naturalWidth > 0')
                        if rota == '/':
                            assert pagina.locator('.inicio-ilustracao img').evaluate('(img) => img.naturalWidth > 0 && getComputedStyle(img).objectFit === "contain"')
                        if rota == '/montagem':
                            assert pagina.locator('.opcao img').evaluate_all('(imgs) => imgs.every(img => img.naturalWidth > 0)')
                            assert pagina.locator('.opcao img').first.evaluate('(img) => getComputedStyle(img).objectFit') == 'contain'
                            if largura in (1366, 390):
                                pagina.screenshot(path=str(CAPTURAS / f'montagem-{largura}.png'), full_page=True)
                            for etapa in range(4):
                                assert pagina.locator(f'[data-step="{etapa}"]').is_visible()
                                medidas_etapa = pagina.evaluate('''() => {
                                    const palco = document.querySelector('.palco-foguete').getBoundingClientRect();
                                    const foguete = document.querySelector('#preview-foguete').getBoundingClientRect();
                                    const grupos = [...document.querySelectorAll('.etapa:not([hidden]) .opcoes')];
                                    const sobreposicao = grupos.some(grupo => {
                                        const cards = [...grupo.querySelectorAll('.opcao')].map(card => card.getBoundingClientRect());
                                        return cards.some((a, i) => cards.slice(i + 1).some(b =>
                                            a.left < b.right - 1 && a.right > b.left + 1 &&
                                            a.top < b.bottom - 1 && a.bottom > b.top + 1));
                                    });
                                    return {
                                        largura: document.documentElement.scrollWidth,
                                        palco: foguete.left >= palco.left - 1 && foguete.right <= palco.right + 1,
                                        sobreposicao,
                                    };
                                }''')
                                assert medidas_etapa['largura'] <= largura + 1, (largura, etapa, medidas_etapa)
                                assert medidas_etapa['palco'] and not medidas_etapa['sobreposicao'], (largura, etapa, medidas_etapa)
                                if etapa < 3:
                                    pagina.locator('#continuar').click()
                    if largura in (1366, 390):
                        pagina.goto(origem, wait_until='networkidle')
                        pagina.screenshot(path=str(CAPTURAS / f'inicio-{largura}.png'), full_page=True)

                pagina.set_viewport_size({'width': 1366, 'height': 768})
                pagina.goto(origem + '/montagem', wait_until='networkidle')
                assert pagina.locator('#codigo').inner_text() == 'C2-A3-F4-S2'
                assert 'dados fictícios' in pagina.locator('#disponibilidade').inner_text()
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                pagina.reload(wait_until='networkidle')
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                assert 'Tema claro' in pagina.locator('#tema').inner_text()
                pagina.screenshot(path=str(CAPTURAS / 'montagem-escuro-1366.png'), full_page=True)
                pagina.goto(origem + '/dashboard', wait_until='networkidle')
                assert pagina.locator('#grafico-apogeu').evaluate('(canvas) => !!Chart.getChart(canvas)')
                pagina.screenshot(path=str(CAPTURAS / 'dashboard-escuro-1366.png'), full_page=True)
                for rota in ('/', '/ranking', '/diagnostico'):
                    pagina.goto(origem + rota, wait_until='networkidle')
                    assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                    assert pagina.locator('body').evaluate('(body) => getComputedStyle(body).backgroundColor') == 'rgb(17, 24, 39)'
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'light'

                pagina.goto(origem + '/montagem', wait_until='networkidle')
                pagina.locator('#continuar').click()
                assert pagina.locator('[data-step="1"]').is_visible()
                pagina.screenshot(path=str(CAPTURAS / 'aletas-1366.png'), full_page=True)
                pagina.locator('input[name="aleta"][value="A1"]').check()
                pagina.locator('input[name="aletas"][value="3"]').check()
                pagina.locator('#continuar').click()
                pagina.locator('input[name="secoes"][value="4"]').check()
                assert pagina.locator('#codigo').inner_text() == 'C2-A1-F3-S4'
                assert pagina.locator('#preview-corpo-svg rect.svg-corpo').count() == 4
                assert pagina.locator('#aletas-traseiras path').count() == 3
                pagina.screenshot(path=str(CAPTURAS / 'corpo-1366.png'), full_page=True)
                pagina.locator('#continuar').click()
                assert pagina.locator('#confirmar').is_disabled()
                assert 'aguardando revisão técnica' in pagina.locator('#disponibilidade-final').inner_text()
                assert pagina.locator('#link-previa').is_visible()
                pagina.locator('#voltar').click()
                assert pagina.locator('input[name="secoes"][value="4"]').is_checked()
                pagina.locator('[data-step-target="1"]').click()
                pagina.locator('input[name="aleta"][value="A3"]').check()
                pagina.locator('input[name="aletas"][value="4"]').check()
                pagina.locator('[data-step-target="2"]').click()
                pagina.locator('input[name="secoes"][value="2"]').check()
                pagina.locator('#continuar').click()
                pagina.locator('#disponibilidade-final').get_by_text('dados fictícios').wait_for()
                pagina.locator('#nome').fill('Visitante QA')
                pagina.evaluate("() => { const botao = document.getElementById('confirmar'); botao.click(); botao.click(); }")
                pagina.wait_for_url('**/voo/*')
                pagina.locator('#ver-resultado').wait_for(state='visible')
                pagina.locator('#ver-resultado').click()
                assert pagina.locator('h1').inner_text() == 'Voo de Visitante QA'
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                pagina.wait_for_load_state('networkidle')
                cor_resultado = pagina.locator('.resultado-destaque strong').evaluate('(item) => getComputedStyle(item).color')
                assert cor_resultado == 'rgb(169, 205, 252)', cor_resultado
                with app.app_context():
                    assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0] == 1

                pagina.goto(origem + '/previa/C1-A1-F3-S1', wait_until='networkidle')
                assert 'não aprovada' in pagina.locator('.aviso-demo').inner_text()
                assert pagina.get_by_text('Nenhum dispositivo de recuperação', exact=False).is_visible()
                pagina.locator('#ver-resultado').wait_for(state='visible')
                assert 'Prévia concluída' in pagina.locator('#titulo-voo').inner_text()
                assert 'série temporal importada do OpenRocket' in pagina.locator('#tipo-trajetoria').inner_text()
                pagina.screenshot(path=str(CAPTURAS / 'previa-1366.png'), full_page=True)
                with app.app_context():
                    assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0] == 1

                pagina.set_viewport_size({'width': 390, 'height': 844})
                pagina.goto(origem + '/previa/C1-A1-F3-S1', wait_until='networkidle')
                assert pagina.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                pagina.screenshot(path=str(CAPTURAS / 'previa-390.png'), full_page=True)
                pagina.goto(origem, wait_until='networkidle')
                pagina.locator('#menu-toggle').click()
                assert pagina.locator('#nav-principal').is_visible()
                assert pagina.locator('#menu-toggle').get_attribute('aria-expanded') == 'true'
                contexto.close()
                navegador.close()
            assert not falhas, falhas
            assert not externas, externas
            print(json.dumps({'resolucoes': RESOLUCOES, 'testes': 'ok', 'erros_console': falhas, 'requisicoes_externas': externas, 'capturas': str(CAPTURAS)}, ensure_ascii=False))
        finally:
            servidor.shutdown()
            thread.join(timeout=5)


if __name__ == '__main__':
    verificar()
