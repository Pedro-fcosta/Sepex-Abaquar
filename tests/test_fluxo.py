from app.db import conexao
from app.estatisticas import ranking,resumo,distribuicoes
from app.simulacoes import importar,revisar
from app.tentativas import registrar
from app.web import csv_tentativas


def simular(app,codigo,apogeu,velocidade):
    with app.app_context():
        conteudo=f'Apogee (m),Maximum velocity (m/s),Maximum acceleration (m/s2)\n{apogeu},{velocidade},70\n'.encode()
        id_sim,_=importar(conteudo,f'{codigo}.csv',codigo)
        revisar(id_sim,'approved')


def test_bloqueio_idempotencia_snapshot_e_paginas(app,cliente):
    dados={'nome':'Ana','codigo':'C2-A3-F4-S2','identificador_sessao':'sessaoana123456'}
    assert cliente.post('/api/tentativas',json=dados).status_code==422
    simular(app,dados['codigo'],120,42)
    resposta=cliente.post('/api/tentativas',json=dados)
    assert resposta.status_code==201
    id_tentativa=resposta.json['id']
    assert cliente.post('/api/tentativas',json=dados).json['id']==id_tentativa
    assert cliente.get(f'/voo/{id_tentativa}').status_code==200
    assert cliente.get(f'/resultado/{id_tentativa}').status_code==200
    assert cliente.get('/ranking').status_code==200
    assert cliente.get('/dashboard').status_code==200
    with app.app_context():
        simular(app,dados['codigo'],200,50)
        assert conexao().execute('SELECT apogeu_m FROM tentativas WHERE id=?',(id_tentativa,)).fetchone()[0]==120
        assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0]==1


def test_ranking_desempate_melhor_e_estatisticas(app,cliente):
    codigos=['C1-A1-F3-S1','C1-A1-F3-S2','C1-A1-F3-S3']
    for codigo,vel in zip(codigos,[30,50,50]): simular(app,codigo,100,vel)
    with app.app_context():
        registrar('Ana',codigos[0],'sessaoana000001')
        registrar('Bia',codigos[1],'sessaobia000001')
        registrar('Ana',codigos[2],'sessaoana000002')
        todas=ranking()
        assert [r['nome'] for r in todas]==['Bia','Ana','Ana'] or [r['nome'] for r in todas]==['Ana','Bia','Ana']
        assert todas[-1]['velocidade_max_ms']==30
        assert len(ranking(True))==2
        stats=resumo()
        assert stats['total_tentativas']==3
        assert stats['participantes_unicos']==2
        assert stats['apogeu_medio_m']==100
        assert stats['apogeu_mediana_m']==100
        assert stats['apogeu_desvio_padrao_m']==0
        assert sum(distribuicoes()['apogeu']['contagens'])==3
        csv=csv_tentativas()
        assert 'Ana' in csv and 'Bia' in csv and csv.count('\n')==4
    assert cliente.get('/api/ranking?melhor=1').status_code==200
    assert cliente.get('/api/dashboard/resumo').json['participantes_unicos']==2
    assert cliente.get('/api/dashboard/distribuicoes').status_code==200
    assert cliente.get('/admin/exportar',headers={'X-Admin-Token':'token-teste'}).status_code==200


def test_desempate_por_horario_e_id(app):
    codigo='C1-A1-F3-S1'
    simular(app,codigo,100,40)
    with app.app_context():
        primeiro,_=registrar('Ana',codigo,'empateana000001')
        segundo,_=registrar('Bia',codigo,'empatebia000001')
        db=conexao()
        with db:
            db.execute("UPDATE tentativas SET horario='2026-09-28 10:00:00' WHERE id=?",(primeiro,))
            db.execute("UPDATE tentativas SET horario='2026-09-28 09:00:00' WHERE id=?",(segundo,))
        assert [r['id'] for r in ranking()]==[segundo,primeiro]
        with db:
            db.execute("UPDATE tentativas SET horario='2026-09-28 09:00:00' WHERE id=?",(primeiro,))
        assert [r['id'] for r in ranking()]==[primeiro,segundo]
