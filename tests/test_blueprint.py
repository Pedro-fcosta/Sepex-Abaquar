import html
import json
import re

from app import criar_app
from app.db import conexao
from app.simulacoes import importar


def test_blueprint_usa_medidas_do_catalogo_e_dados_reais(app, cliente):
    with app.app_context():
        db = conexao()
        corpo = json.loads(db.execute("SELECT propriedades_json FROM componentes WHERE codigo='CORPO'").fetchone()[0])
        corpo['diametro_externo_mm'] = 42
        with db:
            db.execute("UPDATE componentes SET propriedades_json=? WHERE codigo='CORPO'", (json.dumps(corpo),))
        csv = b'Time (s),Altitude (m),CG location (cm),CP location (cm),Stability margin (calibers)\n0,0,15,20,1.25\n1,80,15,20,1.25\n'
        importar(csv, 'voo.csv', 'C1-A1-F3-S1')

    pagina = cliente.get('/montagem')
    assert pagina.status_code == 200
    atributo = re.search(r'data-medidas="([^"]+)"', pagina.get_data(as_text=True)).group(1)
    medidas = json.loads(html.unescape(atributo))
    assert medidas['diametro_mm'] == 42
    assert medidas['secao_mm'] == 200
    assert medidas['aletas']['A1']['corda_raiz_mm'] == 60

    real = cliente.get('/api/configuracoes/C1-A1-F3-S1').json
    assert real['dados_tecnicos'] == {'cg_m': .15, 'cp_m': .2, 'margem_calibres': 1.25}
    assert real['comprimento_corpo_mm'] == 200
    resultado = app.test_cli_runner().invoke(args=['demo-criar'])
    assert resultado.exit_code == 0, resultado.output
    demonstracao = cliente.get('/api/configuracoes/C2-A3-F4-S2').json
    assert demonstracao['demonstrativo'] is True
    assert demonstracao['dados_tecnicos'] is None


def test_montagem_carrega_sem_catalogo_inicializado(tmp_path):
    app = criar_app({'TESTING': True, 'DATABASE': str(tmp_path / 'vazio.sqlite3')})
    assert app.test_client().get('/montagem').status_code == 200
