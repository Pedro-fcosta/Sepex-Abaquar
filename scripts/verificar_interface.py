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
                        assert pagina.locator('#logo-cefet').evaluate('(img) => img.naturalWidth > 0')
                        assert pagina.locator('.marca-logo').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgba(0, 0, 0, 0)'
                        if largura > 1120:
                            topo = pagina.evaluate('''() => {
                                const abas = document.querySelector('.nav-principal').getBoundingClientRect();
                                const tema = document.querySelector('.tema').getBoundingClientRect();
                                return {
                                    abas: abas.top,
                                    tema: tema.top,
                                    semSobreposicao: abas.bottom <= tema.top,
                                    centralizados: [abas, tema].every(item => Math.abs((item.left + item.right) / 2 - innerWidth / 2) <= 1),
                                };
                            }''')
                            assert topo['abas'] < 70 and topo['tema'] < 105 and topo['semSobreposicao'] and topo['centralizados'], (largura, topo)
                        if rota == '/':
                            assert pagina.locator('.inicio-ilustracao img').evaluate('(img) => img.naturalWidth > 0 && getComputedStyle(img).objectFit === "contain"')
                            assert pagina.locator('.inicio-indicadores strong').all_inner_texts() == ['108', '3', '3', '4']
                            assert pagina.get_by_text('O ranking será preenchido durante a SEPEX.').is_visible()
                            assert pagina.locator('.inicio-sequencia li').count() == 5
                            assert pagina.locator('.inicio-linha-tempo li').count() == 3
                            assert pagina.locator('.topo').evaluate('(el) => getComputedStyle(el).position') == 'sticky'
                            assert pagina.locator('.rodape-marca img').evaluate('(img) => img.naturalWidth > 0')
                        if rota == '/montagem':
                            assert pagina.locator('.opcao img').evaluate_all('(imgs) => imgs.every(img => img.naturalWidth > 0)')
                            assert pagina.locator('.opcao img').first.evaluate('(img) => getComputedStyle(img).objectFit') == 'contain'
                            assert pagina.locator('#preview-foguete').evaluate('(svg) => svg.querySelectorAll("#rocket-title-block text").length > 0')
                            if largura == 390:
                                assert pagina.locator('.blueprint-ficha-movel').is_visible()
                                assert pagina.locator('#blueprint-codigo-movel').inner_text() == 'C2-A3-F4-S2'
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
                assert pagina.locator('#codigo').text_content() == 'C2-A3-F4-S2'
                assert 'dados fictícios' in pagina.locator('#disponibilidade').inner_text()
                assert 'blueprint-status' in pagina.locator('#disponibilidade').get_attribute('class')
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                pagina.reload(wait_until='networkidle')
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                assert 'Tema claro' in pagina.locator('#tema').inner_text()
                pagina.screenshot(path=str(CAPTURAS / 'montagem-escuro-1366.png'), full_page=True)
                pagina.goto(origem, wait_until='networkidle')
                pagina.screenshot(path=str(CAPTURAS / 'inicio-escuro-1366.png'), full_page=True)
                assert pagina.locator('.inicio-ilustracao img').evaluate('(img) => img.naturalWidth > 0')
                pagina.goto(origem + '/dashboard', wait_until='networkidle')
                assert pagina.locator('#grafico-apogeu').evaluate('(canvas) => !!Chart.getChart(canvas)')
                pagina.screenshot(path=str(CAPTURAS / 'dashboard-escuro-1366.png'), full_page=True)
                for rota in ('/', '/ranking', '/diagnostico'):
                    pagina.goto(origem + rota, wait_until='networkidle')
                    assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                    assert pagina.locator('body').evaluate('(body) => getComputedStyle(body).backgroundColor') == 'rgb(8, 20, 38)'
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'light'
                pagina.goto(origem, wait_until='networkidle')
                pagina.locator('.inicio-acoes a[href="#como-funciona"]').click()
                assert pagina.evaluate('location.hash') == '#como-funciona'
                pagina.locator('.inicio-acoes a').first.click()
                assert pagina.url.endswith('/montagem')
                pagina.goto(origem, wait_until='networkidle')
                pagina.get_by_role('link', name='Ver ranking completo').click()
                assert pagina.url.endswith('/ranking')

                pagina.goto(origem + '/montagem', wait_until='networkidle')
                assert pagina.locator('#rocket-cg-cp').get_attribute('hidden') is not None
                ogival = pagina.locator('#preview-coifa-svg').get_attribute('d')
                pagina.locator('input[name="coifa"][value="C1"]').check()
                conica = pagina.locator('#preview-coifa-svg').get_attribute('d')
                pagina.locator('input[name="coifa"][value="C3"]').check()
                elipsoidal = pagina.locator('#preview-coifa-svg').get_attribute('d')
                assert len({ogival, conica, elipsoidal}) == 3
                pagina.locator('input[name="coifa"][value="C2"]').check()
                pagina.locator('#continuar').click()
                eliptica = pagina.locator('#preview-aletas-svg path').first.get_attribute('d')
                pagina.locator('input[name="aleta"][value="A1"]').check()
                reta = pagina.locator('#preview-aletas-svg path').first.get_attribute('d')
                pagina.locator('input[name="aleta"][value="A2"]').check()
                enflechada = pagina.locator('#preview-aletas-svg path').first.get_attribute('d')
                assert len({eliptica, reta, enflechada}) == 3
                pagina.locator('input[name="aletas"][value="5"]').check()
                assert pagina.locator('#aletas-traseiras path').count() == 5
                assert '5 × 72°' in pagina.locator('#rocket-rear-view').text_content()
                pagina.locator('#continuar').click()
                pagina.locator('input[name="secoes"][value="1"]').check()
                assert pagina.locator('#preview-corpo-svg rect.svg-corpo').count() == 1
                assert 'CORPO: 200 mm' in pagina.locator('#rocket-dimensions').text_content()
                pagina.locator('input[name="secoes"][value="4"]').check()
                assert pagina.locator('#preview-corpo-svg rect.svg-corpo').count() == 4
                assert 'CORPO: 800 mm' in pagina.locator('#rocket-dimensions').text_content()

                pagina.goto(origem + '/montagem', wait_until='networkidle')
                pagina.locator('#continuar').click()
                assert pagina.locator('[data-step="1"]').is_visible()
                pagina.screenshot(path=str(CAPTURAS / 'aletas-1366.png'), full_page=True)
                pagina.locator('input[name="aleta"][value="A1"]').check()
                pagina.locator('input[name="aletas"][value="3"]').check()
                pagina.locator('#continuar').click()
                pagina.locator('input[name="secoes"][value="4"]').check()
                assert pagina.locator('#codigo').text_content() == 'C2-A1-F3-S4'
                assert pagina.locator('#preview-corpo-svg rect.svg-corpo').count() == 4
                assert pagina.locator('#aletas-traseiras path').count() == 3
                pagina.screenshot(path=str(CAPTURAS / 'corpo-1366.png'), full_page=True)
                pagina.locator('#continuar').click()
                assert pagina.locator('#confirmar').is_enabled()
                assert 'Simulação disponível' in pagina.locator('#disponibilidade-final').inner_text()
                assert pagina.locator('#rocket-cg-cp').get_attribute('hidden') is None
                assert 'CG:' in pagina.locator('#rocket-cg-cp').text_content()
                assert 'CP:' in pagina.locator('#rocket-cg-cp').text_content()
                assert pagina.locator('#link-previa').is_visible()
                pagina.locator('#nome').fill('Visitante OpenRocket')
                pagina.evaluate("() => { const botao = document.getElementById('confirmar'); botao.click(); botao.click(); }")
                pagina.wait_for_url('**/voo/*')
                pagina.wait_for_function("() => !!Chart.getChart(document.getElementById('grafico-altura'))")
                assert pagina.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.length') == 738
                assert 'série temporal importada do OpenRocket' in pagina.locator('#tipo-trajetoria').inner_text()
                pagina.locator('#ver-resultado').click()
                assert pagina.locator('h1').inner_text() == 'Voo de Visitante OpenRocket'
                pagina.goto(origem, wait_until='networkidle')
                assert pagina.locator('.inicio-ranking-lista li').count() == 1
                assert 'Visitante OpenRocket' in pagina.locator('.inicio-ranking-lista').inner_text()

                pagina.goto(origem + '/montagem', wait_until='networkidle')
                for _ in range(3):
                    pagina.locator('#continuar').click()
                pagina.locator('#disponibilidade-final').get_by_text('dados fictícios').wait_for()
                pagina.locator('#nome').fill('Visitante QA')
                pagina.evaluate("() => { const botao = document.getElementById('confirmar'); botao.click(); botao.click(); }")
                pagina.wait_for_url('**/voo/*')
                pagina.wait_for_function("() => !!Chart.getChart(document.getElementById('grafico-altura'))")
                assert pagina.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.length') == 121
                assert pagina.locator('#grafico-velocidade').evaluate('(canvas) => !!Chart.getChart(canvas)')
                assert 'ilustrativas' in pagina.locator('#tipo-trajetoria').inner_text()
                pagina.locator('#ver-resultado').click()
                assert pagina.locator('h1').inner_text() == 'Voo de Visitante QA'
                pagina.locator('#tema').click()
                assert pagina.locator('html').get_attribute('data-theme') == 'dark'
                pagina.wait_for_load_state('networkidle')
                cor_resultado = pagina.locator('.resultado-destaque strong').evaluate('(item) => getComputedStyle(item).color')
                assert cor_resultado == 'rgb(169, 205, 252)', cor_resultado
                with app.app_context():
                    assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0] == 2
                pagina.goto(origem, wait_until='networkidle')
                assert pagina.locator('.inicio-ranking-lista li').count() == 1
                assert 'Visitante QA' not in pagina.locator('.inicio-ranking-lista').inner_text()

                pagina.goto(origem + '/previa/C1-A1-F3-S1', wait_until='networkidle')
                assert pagina.get_by_text('não registra tentativa nem altera o ranking', exact=False).is_visible()
                assert pagina.get_by_text('Nenhum dispositivo de recuperação', exact=False).is_visible()
                assert pagina.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.length') == 974
                assert pagina.locator('#grafico-velocidade').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.length') == 974
                assert pagina.locator('#tempo-graficos').input_value() == '1000'
                assert 'série temporal importada do OpenRocket' in pagina.locator('#tipo-trajetoria').inner_text()
                assert pagina.locator('#foguete-voo').count() == 0
                assert pagina.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].borderColor') == '#83beff'
                pagina.locator('#tema').click()
                assert pagina.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].borderColor') == '#003f91'
                pagina.screenshot(path=str(CAPTURAS / 'previa-1366.png'), full_page=True)
                with app.app_context():
                    assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0] == 2

                pagina.set_viewport_size({'width': 390, 'height': 844})
                pagina.goto(origem + '/previa/C1-A1-F3-S1', wait_until='networkidle')
                assert pagina.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                pagina.screenshot(path=str(CAPTURAS / 'previa-390.png'), full_page=True)
                pagina.goto(origem, wait_until='networkidle')
                pagina.locator('#menu-toggle').click()
                assert pagina.locator('#nav-principal').is_visible()
                assert pagina.locator('#menu-toggle').get_attribute('aria-expanded') == 'true'
                pagina.locator('#nav-principal').get_by_role('link', name='Diagnóstico').click()
                assert pagina.url.endswith('/diagnostico')
                contextoAnimado = navegador.new_context(reduced_motion='no-preference', viewport={'width': 1366, 'height': 768})
                paginaAnimada = contextoAnimado.new_page()
                paginaAnimada.on('pageerror', lambda erro: falhas.append(str(erro)))
                paginaAnimada.goto(origem + '/previa/C1-A1-F3-S1', wait_until='networkidle')
                paginaAnimada.wait_for_function("() => Chart.getChart(document.getElementById('grafico-altura'))?.data.datasets[0].data.length > 4")
                pontosVisiveis = paginaAnimada.locator('#grafico-altura').evaluate('(canvas) => Chart.getChart(canvas).data.datasets[0].data.length')
                assert 4 < pontosVisiveis < 974, pontosVisiveis
                paginaAnimada.locator('#reproduzir-graficos').click()
                assert 'pausada' in paginaAnimada.locator('#estado-graficos').inner_text()
                paginaAnimada.evaluate("() => { const tempo = document.getElementById('tempo-graficos'); tempo.value = '500'; tempo.dispatchEvent(new Event('input', { bubbles: true })); }")
                assert paginaAnimada.locator('#tempo-graficos').input_value() == '500'
                contextoAnimado.close()
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
