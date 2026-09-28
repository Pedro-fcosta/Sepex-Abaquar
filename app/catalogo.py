import itertools
import json
import os
import re
from .db import conexao, inicializar

COIFAS = {'C1': 'Cônica', 'C2': 'Ogival', 'C3': 'Elipsoidal'}
ALETAS = {'A1': 'Trapezoidal reta', 'A2': 'Trapezoidal enflechada', 'A3': 'Elíptica'}
PADRAO_CODIGO = re.compile(r'^C[1-3]-A[1-3]-F[3-5]-S[1-4]$')


def codigo_configuracao(coifa, aleta, quantidade_aletas, secoes):
    codigo = f'{coifa}-{aleta}-F{quantidade_aletas}-S{secoes}'
    if not PADRAO_CODIGO.fullmatch(codigo):
        raise ValueError('Componentes inválidos')
    return codigo


def gerar_configuracoes():
    inicializar()
    db = conexao()
    secao_mm = int(os.getenv('SEPEX_SECAO_MM', '200'))
    diametro_mm = int(os.getenv('SEPEX_DIAMETRO_MM', '40'))
    coifa_mm = int(os.getenv('SEPEX_COIFA_MM', '100'))
    material_impresso = os.getenv('SEPEX_MATERIAL_IMPRESSO', 'PETG')
    material_tubo = os.getenv('SEPEX_MATERIAL_TUBO', 'papel kraft')
    espessura_mm = float(os.getenv('SEPEX_ESPESSURA_ALETA_MM', '2'))
    corda_mm = float(os.getenv('SEPEX_CORDA_RAIZ_MM', '60'))
    envergadura_mm = float(os.getenv('SEPEX_ENVERGADURA_MM', '40'))
    opcoes = [(c, 'coifa', n, f'Coifa {n.lower()}', f'coifa_{c.lower()}.png', {'comprimento_mm': coifa_mm, 'material_sugerido': material_impresso, 'revisao': 'pending_review'}) for c, n in COIFAS.items()]
    opcoes += [(a, 'aleta', n, f'Aleta {n.lower()}', f'aleta_{a.lower()}.png', {'espessura_mm': espessura_mm, 'corda_raiz_mm': corda_mm, 'envergadura_mm': envergadura_mm, 'material_sugerido': material_impresso, 'revisao': 'pending_review'}) for a, n in ALETAS.items()]
    opcoes += [('CORPO', 'corpo', 'Tubo do corpo', 'Seção modular', 'corpo.png', {'diametro_externo_mm': diametro_mm, 'comprimento_secao_mm': secao_mm, 'material_sugerido': material_tubo, 'revisao': 'pending_review'})]
    for c, cat, nome, descricao, imagem, props in opcoes:
        db.execute('INSERT OR IGNORE INTO componentes(codigo,categoria,nome,descricao,imagem,propriedades_json) VALUES (?,?,?,?,?,?)', (c,cat,nome,descricao,imagem,json.dumps(props,ensure_ascii=False)))
    for c,a,f,s in itertools.product(COIFAS,ALETAS,(3,4,5),(1,2,3,4)):
        db.execute('INSERT OR IGNORE INTO configuracoes(codigo,coifa,aleta,quantidade_aletas,secoes,comprimento_corpo_mm) VALUES (?,?,?,?,?,?)', (codigo_configuracao(c,a,f,s),c,a,f,s,s*secao_mm))
    db.commit()
    return db.execute('SELECT count(*) FROM configuracoes').fetchone()[0]
