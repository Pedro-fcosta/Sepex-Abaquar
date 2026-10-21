import re


def test_identificador_sem_origem_segura(cliente):
    primeiro = cliente.get('/api/identificador')
    segundo = cliente.get('/api/identificador')
    assert primeiro.status_code == segundo.status_code == 200
    assert primeiro.headers['Cache-Control'] == 'no-store'
    assert re.fullmatch(r'[0-9a-f]{32}', primeiro.json['id'])
    assert primeiro.json['id'] != segundo.json['id']


def test_dashboard_vazio_tem_chamada_para_primeira_participacao(cliente):
    pagina = cliente.get('/dashboard').get_data(as_text=True)
    assert 'Aguardando o primeiro voo' in pagina
    assert 'Começar montagem' in pagina


def test_login_administrativo_nao_guarda_token_no_cookie(app, cliente):
    resposta = cliente.post('/admin/entrar', data={'token': 'token-teste'})
    assert resposta.status_code == 302
    with cliente.session_transaction() as sessao:
        assert sessao['admin_assinatura']
        assert 'admin_token' not in sessao
        assert sessao.get('csrf')
    assert cliente.get('/admin/simulacoes').status_code == 200
    assert cliente.post('/admin/simulacoes/1/aprovar', headers={'X-Admin-Token': 'invalido'}).status_code == 403
    app.config['ADMIN_TOKEN'] = 'token-substituido'
    assert cliente.get('/admin/simulacoes').status_code == 302
