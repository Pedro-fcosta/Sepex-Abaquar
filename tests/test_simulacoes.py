import io
from app.db import conexao
from app.simulacoes import importar, ler_csv, revisar

PORTUGUES='''# Simulation 1 (Up to date)
# Tempo (s),Altitude (m),Velocidade total (m/s),Aceleração total (m/s²),Localização do CP (cm),Localização do CG (cm),Calibres da margem de estabilidade (cal)
0,0,0,0,20,15,1.25
1,100,40,50,20,15,1.25
2,120,0,-10,20,15,1.25
'''.encode()
INGLES='''Time (s),Altitude (ft),Total velocity (mph),Total acceleration (g),CG location (cm),CP location (cm),Stability margin (calibers)
0,0,0,0,15,20,1.25
1,328.08399,89.4775,2,15,20,1.25
'''.encode()


def test_csv_portugues_serie_e_idempotencia(app):
    with app.app_context():
        id1,criada=importar(PORTUGUES,'pt.csv','C2-A3-F4-S2')
        assert criada
        id2,criada2=importar(PORTUGUES,'pt.csv','C2-A3-F4-S2')
        assert (id1,criada2)==(id2,False)
        sim=conexao().execute('SELECT * FROM simulacoes WHERE id=?',(id1,)).fetchone()
        assert sim['status']=='pending_review'
        assert sim['apogeu_m']==120
        assert sim['cp_m']==.2
        assert sim['cg_m']==.15
        assert sim['tempo_apogeu_s']==2
        assert conexao().execute('SELECT count(*) FROM pontos').fetchone()[0]==3
        assert 'cm' in sim['unidades_originais_json']


def test_csv_ingles_unidades(app):
    with app.app_context():
        sim_id,_=importar(INGLES,'en.csv','C1-A1-F3-S1')
        sim=conexao().execute('SELECT * FROM simulacoes WHERE id=?',(sim_id,)).fetchone()
        assert abs(sim['apogeu_m']-100)<.01
        assert abs(sim['velocidade_max_ms']-40)<.01
        assert abs(sim['aceleracao_max_ms2']-19.6133)<.01


def test_cabecalho_openrocket_com_margem_de_unidade_invisivel():
    csv_realista='''# Simulation 1 (Up to date)
# Tempo (s),Altitude (m),Velocidade total (m/s),Aceleração total (m/s²),Localização do CP (cm),Localização do CG (cm),Calibres da margem de estabilidade (\u200b)
0,0,0,0,20,15,1.25
1,50,20,30,20,15,1.25
'''.encode()
    resumo,pontos,_=ler_csv(csv_realista)
    assert resumo['margem']==1.25
    assert len(pontos)==2


def test_csv_resumo_revisao_e_admin(app,cliente):
    resumo='Apogee (m),Maximum velocity (m/s),Maximum acceleration (m/s²),Time to apogee (s),Stability warning\n90,35,51,6,Review stability\n'.encode()
    with app.app_context():
        sim_id,_=importar(resumo,'resumo.csv','C1-A1-F3-S1')
        assert conexao().execute('SELECT count(*) FROM pontos').fetchone()[0]==0
        revisar(sim_id,'approved')
        assert conexao().execute('SELECT status FROM simulacoes WHERE id=?',(sim_id,)).fetchone()[0]=='approved'
        revisar(sim_id,'rejected')
        assert conexao().execute('SELECT status FROM simulacoes WHERE id=?',(sim_id,)).fetchone()[0]=='rejected'
    assert cliente.post('/admin/importar').status_code==403
    resposta=cliente.post('/admin/importar',headers={'X-Admin-Token':'token-teste'},data={'codigo':'C2-A3-F4-S2','arquivo':(io.BytesIO(PORTUGUES),'pt.csv')})
    assert resposta.status_code==201
    assert cliente.post(f'/admin/simulacoes/{resposta.json["id"]}/aprovar',headers={'X-Admin-Token':'token-teste'}).status_code==200
