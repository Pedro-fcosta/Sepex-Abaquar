import math
import statistics
from collections import Counter, defaultdict
from .db import conexao


def ranking(melhor_por_participante=False):
    linhas = [dict(r) for r in conexao().execute('''SELECT t.*,p.nome,c.coifa,c.aleta,c.quantidade_aletas,c.secoes
        FROM tentativas t JOIN participantes p ON p.id=t.participante_id
        JOIN configuracoes c ON c.codigo=t.configuracao_codigo''')]
    linhas.sort(key=lambda r:(-r['apogeu_m'],-(r['velocidade_max_ms'] or 0),r['horario'],r['id']))
    if melhor_por_participante:
        vistos = set()
        linhas = [r for r in linhas if not (r['participante_id'] in vistos or vistos.add(r['participante_id']))]
    for i,linha in enumerate(linhas,1):
        linha['posicao'] = i
    return linhas


def resumo():
    linhas = ranking()
    alturas = [r['apogeu_m'] for r in linhas]
    velocidades = [r['velocidade_max_ms'] for r in linhas if r['velocidade_max_ms'] is not None]
    aceleracoes = [r['aceleracao_max_ms2'] for r in linhas if r['aceleracao_max_ms2'] is not None]
    def media(valores): return statistics.mean(valores) if valores else None
    def grupos(chave):
        conjunto = defaultdict(list)
        for r in linhas:
            conjunto[str(r[chave])].append(r['apogeu_m'])
        return [{'opcao':k,'tentativas':len(v),'apogeu_medio_m':media(v)} for k,v in sorted(conjunto.items())]
    return {
        'total_tentativas':len(linhas), 'participantes_unicos':len({r['participante_id'] for r in linhas}),
        'configuracoes_unicas':len({r['configuracao_codigo'] for r in linhas}),
        'apogeu_medio_m':media(alturas),'apogeu_mediana_m':statistics.median(alturas) if alturas else None,
        'apogeu_desvio_padrao_m':statistics.pstdev(alturas) if alturas else None,
        'apogeu_min_m':min(alturas,default=None),'apogeu_max_m':max(alturas,default=None),
        'velocidade_media_ms':media(velocidades),'velocidade_max_ms':max(velocidades,default=None),
        'aceleracao_media_ms2':media(aceleracoes),'aceleracao_max_ms2':max(aceleracoes,default=None),
        'configuracoes_mais_escolhidas':[{'codigo':k,'tentativas':v} for k,v in Counter(r['configuracao_codigo'] for r in linhas).most_common()],
        'coifas':grupos('coifa'),'aletas':grupos('aleta'),'quantidade_aletas':grupos('quantidade_aletas'),'secoes':grupos('secoes'),
        'tentativas_ao_longo_do_tempo':[{'data':k,'tentativas':v} for k,v in sorted(Counter(r['horario'][:10] for r in linhas).items())],
    }


def histograma(valores, classes=8):
    if not valores:
        return {'intervalos':[],'contagens':[],'normal_teorica':[],'media':None,'mediana':None,'desvio_padrao':None}
    minimo,maximo = min(valores),max(valores)
    largura = (maximo-minimo)/classes if maximo>minimo else 1
    inicio = minimo if maximo>minimo else minimo-largura*classes/2
    contagens = [0]*classes
    for valor in valores:
        indice = min(classes-1,max(0,int((valor-inicio)/largura)))
        contagens[indice] += 1
    media = statistics.mean(valores)
    desvio = statistics.pstdev(valores)
    normal = [(len(valores)*largura/(desvio*math.sqrt(2*math.pi))*math.exp(-.5*((inicio+(i+.5)*largura-media)/desvio)**2)) if desvio else 0 for i in range(classes)]
    return {'intervalos':[f'{inicio+i*largura:.1f}–{inicio+(i+1)*largura:.1f}' for i in range(classes)],
            'contagens':contagens,'normal_teorica':normal,'media':media,'mediana':statistics.median(valores),'desvio_padrao':desvio}


def distribuicoes():
    linhas = ranking()
    return {'apogeu':histograma([r['apogeu_m'] for r in linhas]),
            'velocidade':histograma([r['velocidade_max_ms'] for r in linhas if r['velocidade_max_ms'] is not None])}
