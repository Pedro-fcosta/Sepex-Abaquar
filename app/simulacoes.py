import csv
import hashlib
import io
import json
import math
import re
import unicodedata
from pathlib import Path
from .db import conexao

ALIAS = {
 'tempo': ('tempo', 'time'),
 'altitude': ('altitude', 'height', 'altitude acima do solo'),
 'velocidade': ('velocidade total', 'total velocity', 'velocidade vertical', 'vertical velocity', 'velocidade', 'velocity', 'speed'),
 'aceleracao': ('aceleracao total', 'total acceleration', 'aceleracao vertical', 'vertical acceleration', 'aceleracao', 'acceleration'),
 'apogeu': ('apogeu', 'apogee', 'maximum altitude', 'max altitude'),
 'velocidade_max': ('velocidade maxima', 'maximum velocity', 'max velocity', 'maximum speed'),
 'aceleracao_max': ('aceleracao maxima', 'maximum acceleration', 'max acceleration'),
 'tempo_apogeu': ('tempo ate o apogeu', 'time to apogee'),
 'duracao': ('duracao total', 'total duration', 'flight time'),
 'cg': ('localizacao do cg', 'cg location', 'center of gravity', 'centro de gravidade', 'cg'),
 'cp': ('localizacao do cp', 'cp location', 'center of pressure', 'centro de pressao', 'cp'),
 'margem': ('calibres da margem de estabilidade', 'stability margin calibers', 'stability margin', 'margem estatica', 'static margin'),
 'aviso': ('aviso de estabilidade', 'stability warning', 'warning', 'aviso'),
}
UNIDADES = {'tempo':'s','altitude':'m','velocidade':'m/s','aceleracao':'m/s²','apogeu':'m','velocidade_max':'m/s','aceleracao_max':'m/s²','tempo_apogeu':'s','duracao':'s','cg':'m','cp':'m','margem':'cal'}


def sem_acentos(valor):
    return ''.join(c for c in unicodedata.normalize('NFKD', valor.lower()) if not unicodedata.combining(c)).replace('\u200b','').strip()


def identificar(coluna):
    texto = sem_acentos(coluna).lstrip('#').strip()
    for campo, nomes in ALIAS.items():
        if any(texto == nome or texto.startswith(nome + ' (') or texto.startswith(nome + ' [') for nome in nomes):
            return campo
    return None


def unidade(coluna, campo):
    partes = re.findall(r'\(([^()]*)\)|\[([^][]*)\]', coluna)
    original = (partes[-1][0] or partes[-1][1]).strip().lower() if partes else UNIDADES[campo]
    return original.replace('²','2').replace('^2','2').replace(' ','').replace('\u200b','').replace('\ufeff','')


def numero(valor, campo, unidade_original):
    if valor is None or str(valor).strip() == '':
        return None
    texto = str(valor).strip().replace(',', '.')
    try:
        n = float(texto)
    except ValueError as exc:
        raise ValueError(f'Número inválido em {campo}: {valor}') from exc
    if not math.isfinite(n):
        return None
    if campo in ('altitude','apogeu','cg','cp'):
        fatores = {'m':1,'cm':.01,'mm':.001,'ft':.3048,'feet':.3048}
    elif campo in ('velocidade','velocidade_max'):
        fatores = {'m/s':1,'km/h':1/3.6,'mph':.44704,'ft/s':.3048}
    elif campo in ('aceleracao','aceleracao_max'):
        fatores = {'m/s2':1,'g':9.80665,'ft/s2':.3048}
    elif campo in ('tempo','tempo_apogeu','duracao'):
        fatores = {'s':1,'ms':.001,'min':60}
    else:
        fatores = {'cal':1,'calibers':1,'calibres':1,'':1}
    if unidade_original not in fatores:
        raise ValueError(f'Unidade não suportada em {campo}: {unidade_original}')
    return n * fatores[unidade_original]


def ler_csv(conteudo):
    for codificacao in ('utf-8-sig','cp1252'):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    linhas = texto.splitlines()
    cabecalho = next((i for i,l in enumerate(linhas) if len(re.findall(r'[,;\t]',l)) >= 1 and len([x for x in re.split(r'[,;\t]',l) if identificar(x)]) >= 2), None)
    if cabecalho is None:
        raise ValueError('Cabeçalho de simulação não encontrado')
    linha = linhas[cabecalho].lstrip('#').strip()
    delimitador = max((',', ';', '\t'), key=linha.count)
    leitor = csv.DictReader(io.StringIO('\n'.join([linha] + [l for l in linhas[cabecalho+1:] if l.strip() and not l.lstrip().startswith('#')])), delimiter=delimitador)
    colunas = {}
    unidades = {}
    for nome in leitor.fieldnames or ():
        campo = identificar(nome)
        if campo and campo not in colunas:
            colunas[campo] = nome
            if campo != 'aviso':
                unidades[campo] = unidade(nome,campo)
    linhas_dados = []
    for linha_dados in leitor:
        if not any(linha_dados.values()):
            continue
        registro = {}
        for campo,nome in colunas.items():
            registro[campo] = linha_dados.get(nome) if campo == 'aviso' else numero(linha_dados.get(nome),campo,unidades[campo])
        if registro.get('tempo') is not None or registro.get('apogeu') is not None:
            linhas_dados.append(registro)
    if not linhas_dados:
        raise ValueError('CSV sem dados reconhecidos')
    serie = 'tempo' in colunas and 'altitude' in colunas
    if serie:
        pontos = [r for r in linhas_dados if r.get('tempo') is not None and r.get('altitude') is not None]
        if not pontos:
            raise ValueError('Série temporal vazia')
        if any(p['tempo'] < 0 or p['altitude'] < 0 for p in pontos):
            raise ValueError('Tempo ou altitude negativos')
        pontos.sort(key=lambda p:p['tempo'])
        if len({p['tempo'] for p in pontos}) != len(pontos):
            raise ValueError('Tempos duplicados')
        pico = max(pontos,key=lambda p:p['altitude'])
        resumo = {'apogeu':pico['altitude'], 'tempo_apogeu':pico['tempo'], 'duracao':pontos[-1]['tempo'],
                  'velocidade_max':max((abs(p['velocidade']) for p in pontos if p.get('velocidade') is not None),default=None),
                  'aceleracao_max':max((abs(p['aceleracao']) for p in pontos if p.get('aceleracao') is not None),default=None)}
        for campo in ('cg','cp','margem','aviso'):
            resumo[campo] = next((p[campo] for p in pontos if p.get(campo) is not None),None)
    else:
        pontos = []
        resumo = linhas_dados[0]
    if resumo.get('apogeu') is None or resumo['apogeu'] < 0:
        raise ValueError('Apogeu ausente ou inválido')
    return resumo,pontos,unidades


def importar(conteudo, nome_arquivo, codigo, condicao='Padrão pendente de revisão'):
    db = conexao()
    if not db.execute('SELECT 1 FROM configuracoes WHERE codigo=?', (codigo,)).fetchone():
        raise ValueError('Configuração inexistente')
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    anterior = db.execute('SELECT id FROM simulacoes WHERE configuracao_codigo=? AND hash_arquivo=?',(codigo,hash_arquivo)).fetchone()
    if anterior:
        return anterior['id'],False
    resumo,pontos,unidades = ler_csv(conteudo)
    with db:
        db.execute('INSERT OR IGNORE INTO condicoes(nome) VALUES (?)',(condicao,))
        condicao_id = db.execute('SELECT id FROM condicoes WHERE nome=?',(condicao,)).fetchone()['id']
        cursor = db.execute('''INSERT INTO simulacoes(configuracao_codigo,condicao_id,apogeu_m,velocidade_max_ms,aceleracao_max_ms2,
          tempo_apogeu_s,duracao_s,cg_m,cp_m,margem_calibres,aviso_estabilidade,unidades_originais_json,origem,hash_arquivo)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
          (codigo,condicao_id,resumo['apogeu'],resumo.get('velocidade_max'),resumo.get('aceleracao_max'),resumo.get('tempo_apogeu'),resumo.get('duracao'),resumo.get('cg'),resumo.get('cp'),resumo.get('margem'),resumo.get('aviso'),json.dumps(unidades,ensure_ascii=False),Path(nome_arquivo).name,hash_arquivo))
        id_simulacao = cursor.lastrowid
        db.executemany('INSERT INTO pontos(simulacao_id,tempo_s,altitude_m,velocidade_ms,aceleracao_ms2) VALUES (?,?,?,?,?)',[(id_simulacao,p['tempo'],p['altitude'],p.get('velocidade'),p.get('aceleracao')) for p in pontos])
    return id_simulacao,True


def revisar(id_simulacao, decisao):
    if decisao not in ('approved','rejected'):
        raise ValueError('Decisão inválida')
    db = conexao()
    sim = db.execute('SELECT * FROM simulacoes WHERE id=?',(id_simulacao,)).fetchone()
    if sim is None:
        raise ValueError('Simulação inexistente')
    with db:
        if decisao == 'approved':
            db.execute("UPDATE simulacoes SET status='rejected' WHERE configuracao_codigo=? AND status='approved' AND id<>?",(sim['configuracao_codigo'],id_simulacao))
        db.execute('UPDATE simulacoes SET status=? WHERE id=?',(decisao,id_simulacao))
