"""Gera os 108 modelos, simula no OpenRocket 24.12 e exporta CSVs para o site.

Uso: python -m scripts.gerar_108_openrocket --importar
Requer uma instalação local do OpenRocket 24.12. Os parâmetros dos modelos
existentes são preliminares e devem ser validados pela equipe antes do evento.
"""

import argparse
import copy
from datetime import datetime
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from app.simulacoes import ler_csv


RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / 'Foguete Modular - Banco' / '.ork'
DESTINO = RAIZ / 'Foguete Modular - Banco' / 'gerados'
CLASSE = RAIZ / 'scripts' / 'openrocket' / 'GerarVoos.class'
PADRAO = re.compile(r'C[1-3]-A[1-3]-F[3-5]-S[1-4]')
SEMENTE_VENTO = 2026
MASSA_LASTRO_KG = 0.025


def codigos():
    return [f'C{c}-A{a}-F{f}-S{s}' for c, a, f, s in itertools.product(range(1, 4), range(1, 4), range(3, 6), range(1, 5))]


def localizar_ambiente(jar_argumento=None, java_argumento=None):
    candidatos = [
        jar_argumento,
        os.getenv('OPENROCKET_JAR'),
        r'C:\Program Files\OpenRocket\jar\OpenRocket-24.12.jar',
    ]
    jar = next((Path(p) for p in candidatos if p and Path(p).is_file()), None)
    if jar is None:
        raise RuntimeError('OpenRocket 24.12 não encontrado. Instale-o ou defina OPENROCKET_JAR.')
    java = java_argumento or os.getenv('OPENROCKET_JAVA')
    if not java:
        instalado = jar.parent.parent / 'jre' / 'bin' / ('java.exe' if os.name == 'nt' else 'java')
        java = str(instalado) if instalado.is_file() else shutil.which('java')
    if not java or not Path(java).is_file():
        raise RuntimeError('Java 17 não encontrado. Defina OPENROCKET_JAVA para o Java do OpenRocket.')
    if not CLASSE.is_file():
        raise RuntimeError(f'Executor Java não encontrado: {CLASSE}')
    return Path(jar), Path(java)


def modelo_fonte(codigo):
    coifa, aleta, _, secao = codigo.split('-')
    candidato = FONTES / coifa / aleta / 'F3' / f'{coifa}-{aleta}-F3-{secao}.ork'
    if candidato.is_file():
        return candidato
    candidato = FONTES / coifa / aleta / 'F3' / f'{coifa}-{aleta}-F3-S1.ork'
    if candidato.is_file():
        return candidato
    raise FileNotFoundError(f'Sem modelo base para {codigo}')


def ler_modelo(caminho):
    with zipfile.ZipFile(caminho) as pacote:
        return ET.fromstring(pacote.read('rocket.ork'))


def exigir(elemento, descricao):
    if elemento is None:
        raise ValueError(f'Modelo incompleto: {descricao}')
    return elemento


def massa_padrao():
    referencia = FONTES / 'C1' / 'A1' / 'F3' / 'C1-A1-F3-S2.ork'
    return copy.deepcopy(exigir(ler_modelo(referencia).find('.//nosecone/subcomponents/masscomponent'), 'lastro de referência'))


def montar(codigo, lastro):
    coifa, aleta, quantidade, secao = codigo.split('-')
    fonte = modelo_fonte(codigo)
    raiz = ler_modelo(fonte)
    exigir(raiz.find('./rocket/name'), 'nome do foguete').text = codigo
    nariz = exigir(raiz.find('.//nosecone'), 'coifa')
    # Os CSVs existentes foram simulados com 25 g na coifa, inclusive os ORKs
    # antigos que não salvaram esse componente. Aplicamos o mesmo lastro a todos.
    subcomponentes = nariz.find('subcomponents')
    if subcomponentes is None:
        subcomponentes = ET.SubElement(nariz, 'subcomponents')
    for componente in list(subcomponentes.findall('masscomponent')):
        subcomponentes.remove(componente)
    subcomponentes.append(copy.deepcopy(lastro))
    exigir(raiz.find('.//bodytube/length'), 'comprimento do corpo').text = f'{int(secao[1:]) * 0.2:.1f}'
    aleta_modelo = raiz.find('.//trapezoidfinset') if aleta != 'A3' else raiz.find('.//ellipticalfinset')
    aleta_modelo = exigir(aleta_modelo, f'formato {aleta}')
    exigir(aleta_modelo.find('instancecount'), 'quantidade de aletas').text = quantidade[1:]
    exigir(aleta_modelo.find('fincount'), 'quantidade de aletas').text = quantidade[1:]
    simulacao = exigir(raiz.find('.//simulation'), 'simulação')
    exigir(simulacao.find('name'), 'nome da simulação').text = codigo
    simulacao.set('status', 'notsimulated')
    for voo_antigo in list(simulacao.findall('flightdata')):
        simulacao.remove(voo_antigo)
    exigir(simulacao.find('conditions'), 'condições da simulação')
    return raiz, fonte


def escrever_ork(caminho, raiz):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = ET.tostring(raiz, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(caminho, 'w', compression=zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr('rocket.ork', conteudo)


def validar_saida(codigo, ork, csv):
    if not ork.is_file() or not csv.is_file():
        raise RuntimeError(f'Arquivos de saída ausentes para {codigo}')
    raiz = ET.parse(ork).getroot()
    if raiz.findtext('./rocket/name') != codigo:
        raise RuntimeError(f'Código incorreto no ORK de {codigo}')
    simulacao = exigir(raiz.find('.//simulation'), 'simulação salva')
    if simulacao.get('status') not in ('uptodate', 'loaded', 'aborted'):
        raise RuntimeError(f'Simulação incompleta para {codigo}: {simulacao.get("status")}')
    resumo, pontos, _ = ler_csv(csv.read_bytes())
    if len(pontos) < 10 or resumo['apogeu'] <= 0:
        raise RuntimeError(f'CSV sem voo válido para {codigo}')
    return {'apogeu_m': round(resumo['apogeu'], 3), 'pontos': len(pontos),
            'status_openrocket': simulacao.get('status'),
            'altitude_final_m': round(pontos[-1]['altitude'], 3)}


def importar_lote(pasta):
    from app import criar_app
    from app.catalogo import gerar_configuracoes

    aplicacao = criar_app()
    with aplicacao.app_context():
        gerar_configuracoes()
    banco = Path(aplicacao.config['DATABASE'])
    data = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = RAIZ / 'data' / 'exports' / f'backup-antes-108-{data}.sqlite3'
    backup.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(banco) as origem, sqlite3.connect(backup) as destino:
        origem.backup(destino)
    comando = [sys.executable, '-m', 'flask', '--app', 'run', 'importar-lote', str(pasta),
               '--condicao', 'OpenRocket 24.12 - lote automatizado preliminar']
    subprocess.run(comando, cwd=RAIZ, check=True)
    subprocess.run([sys.executable, '-m', 'flask', '--app', 'run', 'condicao-configurar',
                    'OpenRocket 24.12 - lote automatizado preliminar', '--motor', 'Estes D12',
                    '--vento-ms', '2', '--direcao-vento-graus', '90', '--altitude-local-m', '0',
                    '--trilho', 'Haste de lançamento de 1 m', '--versao-openrocket', '24.12',
                    '--observacoes', 'Modelo de referência: atmosfera ISA; coordenadas 28.61, -80.6; '
                    'sem recuperação por decisão do projeto. Local e peças físicas não medidos.'],
                   cwd=RAIZ, check=True)
    print(f'Backup anterior à importação: {backup}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--importar', action='store_true', help='importa e libera os CSVs no site após salvar um backup do banco')
    parser.add_argument('--somente', choices=codigos(), help='gera apenas uma combinação para conferência')
    parser.add_argument('--destino', type=Path, default=DESTINO, help='pasta de saída dos ORKs e CSVs')
    parser.add_argument('--jar', help='caminho do OpenRocket-24.12.jar')
    parser.add_argument('--java', help='caminho do executável Java 17')
    argumentos = parser.parse_args()
    if argumentos.somente and argumentos.destino == DESTINO:
        parser.error('--somente requer --destino para preservar o lote completo')
    jar, java = localizar_ambiente(argumentos.jar, argumentos.java)
    escolhas = [argumentos.somente] if argumentos.somente else codigos()
    lastro = massa_padrao()
    if float(exigir(lastro.find('mass'), 'massa do lastro').text) != MASSA_LASTRO_KG:
        raise RuntimeError('O lastro do modelo de referência mudou; revise antes de gerar o lote.')
    destino = argumentos.destino.resolve()
    manifesto = []
    with tempfile.TemporaryDirectory(prefix='sepex-openrocket-') as temporario:
        temporario = Path(temporario)
        entrada = temporario / 'entrada'
        orks = temporario / 'ork'
        csvs = temporario / 'csv'
        for codigo in escolhas:
            raiz, fonte = montar(codigo, lastro)
            relativo = Path(codigo[:2]) / codigo[3:5] / codigo[6:8] / f'{codigo}.ork'
            escrever_ork(entrada / relativo, raiz)
            manifesto.append({'codigo': codigo, 'modelo_base': str(fonte.relative_to(RAIZ)).replace('\\', '/')})
        comando = [str(java), '-Xmx1g', '-cp', os.pathsep.join((str(jar), str(CLASSE.parent))),
                   'GerarVoos', str(entrada), str(orks), str(csvs), str(SEMENTE_VENTO)]
        resultado = subprocess.run(comando, cwd=RAIZ, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        if resultado.returncode:
            raise RuntimeError('OpenRocket interrompeu o lote:\n' + '\n'.join(resultado.stdout.splitlines()[-30:]))
        for item in manifesto:
            codigo = item['codigo']
            relativo = Path(codigo[:2]) / codigo[3:5] / codigo[6:8] / codigo
            item.update(validar_saida(codigo, orks / relativo.with_suffix('.ork'), csvs / relativo.with_suffix('.csv')))
        for pasta, origem in (('ork', orks), ('csv', csvs)):
            for arquivo in origem.rglob('*'):
                if arquivo.is_file():
                    alvo = destino / pasta / arquivo.relative_to(origem)
                    alvo.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(arquivo, alvo)
    dados = {
        'openrocket': '24.12',
        'quantidade': len(manifesto),
        'lastro_coifa_kg': MASSA_LASTRO_KG,
        'vento_medio_ms': 2.0,
        'vento_desvio_ms': 0.0,
        'semente_vento': SEMENTE_VENTO,
        'revisao_tecnica': 'pending_review',
        'observacao': 'Parâmetros dos ORKs existentes são preliminares; motor, massas, geometria e condições devem ser revisados.',
        'simulacoes': manifesto,
    }
    destino.mkdir(parents=True, exist_ok=True)
    (destino / 'manifesto.json').write_text(json.dumps(dados, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(manifesto)} modelos ORK e CSVs gerados em {destino}')
    interrompidas = [item['codigo'] for item in manifesto if item['status_openrocket'] == 'aborted']
    print(f'{len(manifesto) - len(interrompidas)} voos concluídos; {len(interrompidas)} interrompidos: {", ".join(interrompidas) or "nenhum"}')
    if argumentos.importar:
        importar_lote(destino / 'csv')


if __name__ == '__main__':
    main()
