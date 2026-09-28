import pytest
from app import criar_app
from app.catalogo import gerar_configuracoes


@pytest.fixture
def app(tmp_path):
    aplicacao=criar_app({'TESTING':True,'DATABASE':str(tmp_path/'teste.sqlite3'),'ADMIN_TOKEN':'token-teste','SECRET_KEY':'teste'})
    with aplicacao.app_context(): gerar_configuracoes()
    return aplicacao


@pytest.fixture
def cliente(app):
    return app.test_client()
