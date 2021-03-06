# coding: UTF-8
from __future__ import absolute_import

from flask.ext.script import Manager
from unicodecsv import DictReader, DictWriter

_help = 'Comandos do cidadeiluminada'

manager = Manager(help=_help, description=_help)


@manager.command
def criar_usuarios():
    from cidadeiluminada.models import user_datastore
    admin_role = user_datastore.find_or_create_role('admin')
    user_datastore.create_user(email='admin@cidadeiluminada', password='admin',
                               roles=[admin_role])
    urbam_role = user_datastore.find_or_create_role('urbam')
    user_datastore.create_user(email='urbam@cidadeiluminada', password='urbam',
                               roles=[urbam_role])
    secretaria_role = user_datastore.find_or_create_role('secretaria')
    user_datastore.create_user(email='secretaria@cidadeiluminada', password='secretaria',
                               roles=[secretaria_role])
    user_datastore.commit()


@manager.command
def carregar_enderecos(regioes_filename, logradouros_filename):
    carregar_regioes(regioes_filename)
    carregar_logradouros(logradouros_filename)


@manager.command
def carregar_regioes(filename):
    from cidadeiluminada.base import db
    from cidadeiluminada.protocolos.models import Bairro, Regiao
    with open(filename, 'r') as csvfile:
        csvreader = DictReader(csvfile)
        for row in csvreader:
            regiao_ = row['regiao']
            regiao = Regiao.query.filter_by(nome=regiao_).first()
            if not regiao:
                regiao = Regiao(nome=regiao)
                db.session.add(regiao)
            bairro_ = row['bairro']
            bairro = Bairro.query.filter_by(nome=bairro_).first()
            if not bairro:
                bairro = Bairro(nome=bairro_)
                db.session.add(bairro)
            bairro.regiao = regiao
    db.session.commit()


@manager.command
def carregar_logradouros(filename):
    from cidadeiluminada.base import db
    from cidadeiluminada.protocolos.models import Bairro, Logradouro
    with open(filename, 'r') as csvfile:
        csvreader = DictReader(csvfile)
        for row in csvreader:
            cidade = row['cidade']
            if cidade != u'São José dos Campos':
                continue
            bairro_ = row['bairro']
            bairro = Bairro.query.filter_by(nome=bairro_).first()
            if not bairro:
                print 'Bairro não encontrado:', bairro_
                continue
            cep = row['cep']
            logradouro_ = row['rua']
            logradouro = Logradouro.query.filter_by(cep=cep).first()
            if not logradouro:
                logradouro = Logradouro(cep=cep, logradouro=logradouro_)
                db.session.add(logradouro)
            if not logradouro.bairro:
                logradouro.bairro = bairro
    db.session.commit()
