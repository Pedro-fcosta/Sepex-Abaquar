import json
import pytest
from app.catalogo import codigo_configuracao, gerar_configuracoes
from app.db import conexao


def test_gera_108_codigos_unicos_e_comprimento(app):
    with app.app_context():
        assert gerar_configuracoes()==108
        linhas=conexao().execute('SELECT codigo,comprimento_corpo_mm FROM configuracoes').fetchall()
        assert len({r['codigo'] for r in linhas})==108
        assert conexao().execute("SELECT comprimento_corpo_mm FROM configuracoes WHERE codigo='C2-A3-F4-S2'").fetchone()[0]==400
        medidas = {r['codigo']: json.loads(r['propriedades_json']) for r in conexao().execute(
            "SELECT codigo, propriedades_json FROM componentes WHERE categoria='aleta'")}
        assert [(medidas[c]['espessura_mm'], medidas[c]['corda_raiz_mm'], medidas[c]['envergadura_mm'])
                for c in ('A1', 'A2', 'A3')] == [(3, 70, 30), (3, 70, 30), (3, 64, 30)]
        assert codigo_configuracao('C2','A3',4,2)=='C2-A3-F4-S2'
        with pytest.raises(ValueError): codigo_configuracao('C4','A3',4,2)


def test_api_configuracao(cliente):
    resposta=cliente.get('/api/configuracoes/C2-A3-F4-S2')
    assert resposta.status_code==200
    assert resposta.json['comprimento_corpo_mm']==400
    assert resposta.json['disponivel'] is False
    assert len(cliente.get('/api/configuracoes').json)==108
