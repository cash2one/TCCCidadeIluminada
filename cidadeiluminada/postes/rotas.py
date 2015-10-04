# coding: UTF-8
from __future__ import absolute_import

from flask import request, jsonify
from flask.ext.admin import expose, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView

from cidadeiluminada.postes.models import Poste, Pendencia, ZonaCidade, Bairro
from cidadeiluminada.base import db

_endereco_widget_args = {
    'estado': {
        'readonly': True,
    },
    'cidade': {
        'readonly': True,
    }
}

_endereco_args = {
    'estado': {
        'default': u'SP',
    },
    'cidade': {
        'default': u'São José dos Campos',
    }
}


class IndexView(AdminIndexView):

    @expose('/')
    def index(self):
        pendencias_acao = Pendencia.query.filter(Pendencia.poste == None)
        return self.render('postes/index_postes.html', pendencias_acao=pendencias_acao)


class _ModelView(ModelView):

    category = None

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('name', self.name)
        kwargs.setdefault('category', self.category)
        super(_ModelView, self).__init__(self.model, db.session, *args, **kwargs)


class PosteView(_ModelView):
    model = Poste
    name = 'Postes'
    category = 'Protocolos'

    form_widget_args = _endereco_widget_args
    form_args = _endereco_args
    form_excluded_columns = ('pendencias',)


class PendenciaView(_ModelView):
    model = Pendencia
    name = 'Protocolos'
    category = 'Protocolos'

    can_edit = True
    can_delete = True
    can_create = False

    form_args = _endereco_args
    form_widget_args = dict(_endereco_widget_args, **{
        'bairro': {
            'readonly': True,
            'disabled': True,
        },
        'criacao': {
            'readonly': True,
            'disabled': True,
        },
        'cep': {
            'readonly': True,
        },
        'logradouro': {
            'readonly': True,
        },
        'numero': {
            'readonly': True,
        }
    })

    def on_model_change(self, form, model, is_created):
        if not is_created:
            return
        model.preencher_endereco()
        model.descobrir_poste()
        duplicidade = model.verificar_duplicidade()
        if duplicidade:
            raise ValueError(u'Em duplicidade')
        pass

    @expose('/nova_pendencia/', methods=['POST'])
    def nova_pendencia(self):
        form = self.create_form(request.form)
        if form.validate():
            try:
                pendencia = self.create_model(form)
            except ValueError as ex:
                return jsonify(payload={'status': 'ERRO', 'erros': [ex.message]}), 400
            return jsonify(payload={'pendencia_id': pendencia.id, 'status': 'OK'}), 200
        return jsonify(payload={'status': 'ERRO', 'erros': form.errors}), 400


class ZonaCidadeView(_ModelView):
    model = ZonaCidade
    name = 'Zona'
    category = 'Bairro'


class BairroView(_ModelView):
    model = Bairro
    name = 'Bairro'
    category = 'Bairro'

    form_columns = ('zona', 'nome')


def init_app(app, config):
    del config['name']
    return IndexView(name='Principal', **config), [PosteView(), PendenciaView(), ZonaCidadeView(), BairroView()]
