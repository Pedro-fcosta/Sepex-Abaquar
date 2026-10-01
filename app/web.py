import csv
import hmac
import io
import json
import sqlite3
import secrets
from functools import wraps
from flask import Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from .catalogo import ALETAS, COIFAS
from .db import conexao
from .estatisticas import distribuicoes, ranking, resumo
from .simulacoes import importar, revisar
from .tentativas import registrar

bp = Blueprint('web',__name__)


def admin_autorizado():
    token = current_app.config['ADMIN_TOKEN']
    recebido = request.headers.get('X-Admin-Token') or session.get('admin_token','')
    return bool(token) and hmac.compare_digest(token,recebido)


def exige_admin(funcao):
    @wraps(funcao)
    def interna(*args,**kwargs):
        if not admin_autorizado():
            if request.method == 'GET' and not request.path.startswith('/api/'):
                return redirect(url_for('web.admin_entrar'))
            return jsonify(erro='Acesso administrativo não autorizado'),403
        if request.method == 'POST' and not request.headers.get('X-Admin-Token'):
            if not session.get('csrf') or not hmac.compare_digest(session['csrf'],request.form.get('csrf','')):
                return jsonify(erro='Formulário expirado'),403
        return funcao(*args,**kwargs)
    return interna


@bp.get('/')
def inicio():
    db = conexao()
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='configuracoes'").fetchone():
        return render_template('inicio.html', destaques=[], configuracoes_carregadas=0)
    destaques = [linha for linha in ranking() if not linha['demonstrativo']][:3]
    return render_template('inicio.html', destaques=destaques,
                           configuracoes_carregadas=db.execute('SELECT count(*) FROM configuracoes').fetchone()[0])


@bp.get('/montagem')
def montagem():
    db = conexao()
    componentes = {}
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='componentes'").fetchone():
        componentes = {linha['codigo']: json.loads(linha['propriedades_json']) for linha in db.execute(
            "SELECT codigo,propriedades_json FROM componentes WHERE codigo='CORPO' OR categoria IN ('coifa','aleta')")}
    medidas = {}
    if {'CORPO', *COIFAS, *ALETAS} <= componentes.keys():
        medidas = {
            'diametro_mm': componentes['CORPO']['diametro_externo_mm'],
            'secao_mm': componentes['CORPO']['comprimento_secao_mm'],
            'coifas': {codigo: componentes[codigo]['comprimento_mm'] for codigo in COIFAS},
            'aletas': {codigo: {
                'corda_raiz_mm': componentes[codigo]['corda_raiz_mm'],
                'envergadura_mm': componentes[codigo]['envergadura_mm'],
            } for codigo in ALETAS},
        }
    return render_template('montagem.html',coifas=COIFAS,aletas=ALETAS,medidas_blueprint=medidas)


@bp.get('/api/configuracoes')
def configuracoes():
    return jsonify([dict(r) for r in conexao().execute('''SELECT c.*,
      EXISTS(SELECT 1 FROM simulacoes s WHERE s.configuracao_codigo=c.codigo AND s.status='approved') AS disponivel,
      EXISTS(SELECT 1 FROM simulacoes s WHERE s.configuracao_codigo=c.codigo AND s.status='approved' AND s.demonstrativo=1) AS demonstrativo
      FROM configuracoes c ORDER BY c.codigo''')])


@bp.get('/api/configuracoes/<codigo>')
def configuracao(codigo):
    linha = conexao().execute('SELECT * FROM configuracoes WHERE codigo=?',(codigo,)).fetchone()
    if not linha: abort(404)
    sim = conexao().execute("SELECT id,demonstrativo,cg_m,cp_m,margem_calibres FROM simulacoes WHERE configuracao_codigo=? AND status='approved' ORDER BY id DESC LIMIT 1",(codigo,)).fetchone()
    previa = conexao().execute("""SELECT s.id FROM simulacoes s WHERE s.configuracao_codigo=? AND s.status IN ('approved','pending_review')
        AND EXISTS(SELECT 1 FROM pontos p WHERE p.simulacao_id=s.id) ORDER BY (s.status='approved') DESC,s.id DESC LIMIT 1""",(codigo,)).fetchone()
    dados_tecnicos = {campo: sim[campo] for campo in ('cg_m','cp_m','margem_calibres')} if sim and not sim['demonstrativo'] else None
    return jsonify({**dict(linha),'disponivel':bool(sim),'demonstrativo':bool(sim and sim['demonstrativo']),
                   'dados_tecnicos':dados_tecnicos,
                   'url_previa':url_for('web.previa_voo',codigo=codigo) if previa else None})


@bp.post('/api/tentativas')
def criar_tentativa():
    dados = request.get_json(silent=True) or {}
    try:
        id_tentativa,criada = registrar(dados.get('nome'),dados.get('codigo'),dados.get('identificador_sessao'))
    except ValueError as exc:
        return jsonify(erro=str(exc)),422
    return jsonify(id=id_tentativa,criada=criada,url_voo=url_for('web.voo',id=id_tentativa)),201 if criada else 200


def obter_tentativa(id):
    linha = conexao().execute('''SELECT t.*,p.nome,s.tempo_apogeu_s,s.duracao_s,s.aviso_estabilidade
        FROM tentativas t JOIN participantes p ON p.id=t.participante_id
        JOIN simulacoes s ON s.id=t.simulacao_id WHERE t.id=?''',(id,)).fetchone()
    if not linha: abort(404)
    return dict(linha)


@bp.get('/voo/<int:id>')
def voo(id):
    return render_template('voo.html',tentativa=obter_tentativa(id))


@bp.get('/api/voo/<int:id>')
def dados_voo(id):
    tentativa = obter_tentativa(id)
    pontos = [dict(r) for r in conexao().execute('SELECT tempo_s,altitude_m,velocidade_ms,aceleracao_ms2 FROM pontos WHERE simulacao_id=? ORDER BY tempo_s',(tentativa['simulacao_id'],))]
    return jsonify(tentativa=tentativa,pontos=pontos,origem_trajetoria='serie_openrocket' if pontos else 'animacao_ilustrativa')


def obter_previa(codigo):
    linha = conexao().execute("""SELECT s.* FROM simulacoes s WHERE s.configuracao_codigo=? AND s.status IN ('approved','pending_review')
        AND EXISTS(SELECT 1 FROM pontos p WHERE p.simulacao_id=s.id) ORDER BY (s.status='approved') DESC,s.id DESC LIMIT 1""",(codigo,)).fetchone()
    if not linha: abort(404)
    simulacao = dict(linha)
    ultimo = conexao().execute('SELECT altitude_m FROM pontos WHERE simulacao_id=? ORDER BY tempo_s DESC LIMIT 1',(simulacao['id'],)).fetchone()
    simulacao['altitude_final_m'] = ultimo['altitude_m']
    simulacao['avisos_exibicao'] = (simulacao['observacoes'] or '').replace(
        'No recovery device defined in the simulation.',
        'Nenhum dispositivo de recuperação foi definido na simulação.')
    return simulacao


@bp.get('/previa/<codigo>')
def previa_voo(codigo):
    simulacao = obter_previa(codigo)
    return render_template('voo.html',tentativa=simulacao,previa=True)


@bp.get('/api/previa/<codigo>')
def dados_previa(codigo):
    simulacao = obter_previa(codigo)
    pontos = [dict(r) for r in conexao().execute('SELECT tempo_s,altitude_m,velocidade_ms,aceleracao_ms2 FROM pontos WHERE simulacao_id=? ORDER BY tempo_s',(simulacao['id'],))]
    indicadores = {campo:simulacao[campo] for campo in ('apogeu_m','tempo_apogeu_s','duracao_s')}
    return jsonify(tentativa=indicadores,pontos=pontos,origem_trajetoria='serie_openrocket',previa=True)


@bp.get('/resultado/<int:id>')
def resultado(id):
    tentativa = obter_tentativa(id)
    posicao = next((r['posicao'] for r in ranking() if r['id']==id),None)
    return render_template('resultado.html',tentativa=tentativa,posicao=posicao)


@bp.get('/ranking')
def pagina_ranking():
    melhor = request.args.get('melhor') == '1'
    return render_template('ranking.html',linhas=ranking(melhor),melhor=melhor)


@bp.get('/api/ranking')
def api_ranking():
    return jsonify(ranking(request.args.get('melhor')=='1'))


@bp.get('/dashboard')
def dashboard():
    return render_template('dashboard.html',dados=resumo(),distribuicoes=distribuicoes(),linhas=ranking()[:10])


@bp.get('/api/dashboard/resumo')
def api_resumo():
    return jsonify(resumo())


@bp.get('/api/dashboard/distribuicoes')
def api_distribuicoes():
    return jsonify(distribuicoes())


@bp.get('/diagnostico')
def diagnostico():
    db = conexao()
    return render_template('diagnostico.html',
        configuracoes=db.execute('SELECT count(*) FROM configuracoes').fetchone()[0],
        aprovadas=db.execute("SELECT count(*) FROM simulacoes WHERE status='approved'").fetchone()[0],
        tentativas=db.execute('SELECT count(*) FROM tentativas').fetchone()[0],
        integridade=db.execute('PRAGMA integrity_check').fetchone()[0])


@bp.route('/admin/entrar',methods=['GET','POST'])
def admin_entrar():
    erro = None
    if request.method == 'POST':
        token = current_app.config['ADMIN_TOKEN']
        recebido = request.form.get('token','')
        if token and hmac.compare_digest(token,recebido):
            session['admin_token'] = recebido
            session['csrf'] = secrets.token_urlsafe(32)
            return redirect(url_for('web.admin_simulacoes'))
        erro = 'Token inválido ou não configurado.'
    return render_template('admin_entrar.html',erro=erro)


@bp.get('/admin/simulacoes')
@exige_admin
def admin_simulacoes():
    linhas = [dict(r) for r in conexao().execute('''SELECT s.*,c.nome AS condicao FROM simulacoes s
        LEFT JOIN condicoes c ON c.id=s.condicao_id ORDER BY s.importado_em DESC,s.id DESC''')]
    return render_template('admin_simulacoes.html',linhas=linhas,csrf=session.get('csrf',''))


@bp.post('/admin/importar')
@exige_admin
def admin_importar():
    arquivo = request.files.get('arquivo')
    if not arquivo: return jsonify(erro='Arquivo CSV obrigatório'),400
    try:
        id_simulacao,criada = importar(arquivo.read(),arquivo.filename or 'importacao.csv',request.form.get('codigo',''),request.form.get('condicao') or 'Importação OpenRocket')
    except (ValueError,sqlite3.IntegrityError) as exc:
        return jsonify(erro=str(exc)),422
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return redirect(url_for('web.admin_simulacoes'))
    return jsonify(id=id_simulacao,criada=criada,status='approved'),201 if criada else 200


@bp.post('/admin/simulacoes/<int:id>/aprovar')
@exige_admin
def admin_aprovar(id):
    try: revisar(id,'approved')
    except ValueError as exc: return jsonify(erro=str(exc)),404
    return redirect(url_for('web.admin_simulacoes')) if request.accept_mimetypes.accept_html else jsonify(id=id,status='approved')


@bp.post('/admin/simulacoes/<int:id>/rejeitar')
@exige_admin
def admin_rejeitar(id):
    try: revisar(id,'rejected')
    except ValueError as exc: return jsonify(erro=str(exc)),404
    return redirect(url_for('web.admin_simulacoes')) if request.accept_mimetypes.accept_html else jsonify(id=id,status='rejected')


def csv_tentativas():
    saida = io.StringIO()
    campos = ('id','nome','configuracao_codigo','horario','apogeu_m','velocidade_max_ms','aceleracao_max_ms2','margem_calibres','posicao_calculada','demonstrativo')
    escritor = csv.DictWriter(saida,fieldnames=campos,extrasaction='ignore')
    escritor.writeheader()
    for linha in conexao().execute('''SELECT t.*,p.nome FROM tentativas t JOIN participantes p ON p.id=t.participante_id ORDER BY t.id'''):
        dados = dict(linha)
        if dados['nome'].startswith(('=','+','-','@')):
            dados['nome'] = "'" + dados['nome']
        escritor.writerow(dados)
    return '\ufeff'+saida.getvalue()


@bp.get('/admin/exportar')
@exige_admin
def admin_exportar():
    return Response(csv_tentativas(),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=tentativas-sepex.csv'})
