import csv
import hashlib
import os
import re
import sqlite3
from pathlib import Path
import click
from .catalogo import gerar_configuracoes
from .db import conexao, inicializar
from .simulacoes import importar, revisar
from .web import csv_tentativas


def registrar_comandos(app):
    @app.cli.command('init-db')
    def init_db():
        inicializar()
        click.echo('Banco inicializado.')

    @app.cli.command('seed-configuracoes')
    def seed():
        click.echo(f'{gerar_configuracoes()} configurações cadastradas.')

    @app.cli.command('importar-csv')
    @click.argument('codigo')
    @click.argument('arquivo',type=click.Path(exists=True,path_type=Path))
    @click.option('--condicao',default='Importação OpenRocket')
    def importar_csv(codigo,arquivo,condicao):
        id_simulacao,criada = importar(arquivo.read_bytes(),arquivo.name,codigo,condicao)
        click.echo(f'Simulação {id_simulacao}: {"importada e disponível" if criada else "já existente e disponível"}.')

    @app.cli.command('importar-lote')
    @click.argument('pasta',type=click.Path(exists=True,file_okay=False,path_type=Path))
    @click.option('--condicao',default='Lote OpenRocket de teste')
    def importar_lote(pasta,condicao):
        arquivos = sorted(pasta.rglob('*.csv'))
        if not arquivos:
            raise click.ClickException('Nenhum CSV encontrado na pasta.')
        novos = existentes = 0
        erros = []
        for arquivo in arquivos:
            codigo = arquivo.stem
            if not re.fullmatch(r'C[1-3]-A[1-3]-F[3-5]-S[1-4]',codigo):
                erros.append(f'{arquivo.name}: código inválido no nome')
                continue
            try:
                identificador,criada = importar(arquivo.read_bytes(),arquivo.name,codigo,condicao)
                novos += int(criada)
                existentes += int(not criada)
                click.echo(f'{codigo}: simulação {identificador} ({"disponível" if criada else "já existente e disponível"})')
            except ValueError as exc:
                erros.append(f'{arquivo.name}: {exc}')
        click.echo(f'Total: {novos} importadas, {existentes} já existentes, {len(erros)} erros. Simulações válidas disponíveis no programa.')
        if erros:
            raise click.ClickException('\n'.join(erros))

    @app.cli.command('pendentes')
    def pendentes():
        for linha in conexao().execute("SELECT id,configuracao_codigo,origem,apogeu_m FROM simulacoes WHERE status='pending_review' ORDER BY id"):
            click.echo(f'{linha["id"]} {linha["configuracao_codigo"]} {linha["origem"]} {linha["apogeu_m"]} m')

    @app.cli.command('revisar')
    @click.argument('id_simulacao',type=int)
    @click.argument('decisao',type=click.Choice(['approved','rejected']))
    def revisar_cli(id_simulacao,decisao):
        revisar(id_simulacao,decisao)
        click.echo(f'Simulação {id_simulacao}: {decisao}.')

    @app.cli.command('condicao-configurar')
    @click.argument('nome')
    @click.option('--motor')
    @click.option('--temperatura-c',type=float)
    @click.option('--pressao-pa',type=float)
    @click.option('--vento-ms',type=float)
    @click.option('--direcao-vento-graus',type=float)
    @click.option('--altitude-local-m',type=float)
    @click.option('--trilho')
    @click.option('--versao-openrocket')
    @click.option('--observacoes')
    @click.option('--data-simulacao')
    @click.option('--revisao-tecnica',type=click.Choice(['pending_review','approved','rejected']))
    def condicao_configurar(nome,**campos):
        db=conexao()
        if not nome.strip():
            raise click.BadParameter('Nome obrigatório')
        atualizacoes={chave:valor for chave,valor in campos.items() if valor is not None}
        with db:
            db.execute('INSERT OR IGNORE INTO condicoes(nome) VALUES (?)',(nome,))
            if atualizacoes:
                colunas=', '.join(f'{chave}=?' for chave in atualizacoes)
                db.execute(f'UPDATE condicoes SET {colunas} WHERE nome=?',(*atualizacoes.values(),nome))
        click.echo(f'Condição {nome} atualizada; revisão técnica: '+db.execute('SELECT revisao_tecnica FROM condicoes WHERE nome=?',(nome,)).fetchone()[0])

    @app.cli.command('demo-criar')
    def demo_criar():
        gerar_configuracoes()
        db=conexao()
        codigo='C2-A3-F4-S2'
        if db.execute("SELECT 1 FROM simulacoes WHERE configuracao_codigo=? AND status='approved' AND demonstrativo=0",(codigo,)).fetchone():
            click.echo('Já existe simulação real aprovada; demonstração não criada.')
            return
        hash_arquivo=hashlib.sha256(b'SEPEX-DEMO-C2-A3-F4-S2-v1').hexdigest()
        if db.execute('SELECT 1 FROM simulacoes WHERE configuracao_codigo=? AND hash_arquivo=?',(codigo,hash_arquivo)).fetchone():
            click.echo('Demonstração já existe.')
            return
        db.execute("INSERT OR IGNORE INTO condicoes(nome,observacoes,revisao_tecnica) VALUES ('DEMONSTRAÇÃO','Valores sintéticos para testar interface; não são resultados OpenRocket.','pending_review')")
        condicao=db.execute("SELECT id FROM condicoes WHERE nome='DEMONSTRAÇÃO'").fetchone()['id']
        with db:
            db.execute('''INSERT INTO simulacoes(configuracao_codigo,condicao_id,apogeu_m,velocidade_max_ms,aceleracao_max_ms2,
                tempo_apogeu_s,duracao_s,margem_calibres,origem,hash_arquivo,status,demonstrativo,observacoes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (codigo,condicao,120,42,65,7,15,None,'DADOS FICTÍCIOS',hash_arquivo,'approved',1,'APENAS DEMONSTRAÇÃO. Não é resultado OpenRocket.'))
        click.echo('Demonstração fictícia criada para C2-A3-F4-S2.')

    @app.cli.command('demo-limpar')
    def demo_limpar():
        db=conexao()
        with db:
            participantes_demo=[r[0] for r in db.execute('SELECT DISTINCT participante_id FROM tentativas WHERE demonstrativo=1')]
            db.execute('DELETE FROM tentativas WHERE demonstrativo=1')
            db.execute('DELETE FROM simulacoes WHERE demonstrativo=1')
            db.execute("DELETE FROM condicoes WHERE nome='DEMONSTRAÇÃO' AND NOT EXISTS(SELECT 1 FROM simulacoes WHERE condicao_id=condicoes.id)")
            for participante in participantes_demo:
                db.execute('DELETE FROM participantes WHERE id=? AND NOT EXISTS(SELECT 1 FROM tentativas WHERE participante_id=?)',(participante,participante))
        click.echo('Dados fictícios removidos.')

    @app.cli.command('exportar-tentativas')
    @click.argument('arquivo',type=click.Path(path_type=Path))
    def exportar(arquivo):
        arquivo.parent.mkdir(parents=True,exist_ok=True)
        arquivo.write_text(csv_tentativas(),encoding='utf-8')
        click.echo(str(arquivo))

    @app.cli.command('backup-db')
    @click.argument('arquivo',type=click.Path(path_type=Path))
    def backup(arquivo):
        arquivo.parent.mkdir(parents=True,exist_ok=True)
        destino=sqlite3.connect(arquivo)
        with destino:
            conexao().backup(destino)
        destino.close()
        click.echo(str(arquivo))

    @app.cli.command('verificar-cobertura')
    def cobertura():
        db=conexao()
        total=db.execute('SELECT count(*) FROM configuracoes').fetchone()[0]
        faltantes=[r['codigo'] for r in db.execute('''SELECT c.codigo FROM configuracoes c WHERE NOT EXISTS
            (SELECT 1 FROM simulacoes s WHERE s.configuracao_codigo=c.codigo AND s.status='approved') ORDER BY c.codigo''')]
        click.echo(f'{total-len(faltantes)}/{total} configurações cadastradas com simulação aprovada (esperadas: 108).')
        if faltantes:
            click.echo('Pendentes: '+', '.join(faltantes))
