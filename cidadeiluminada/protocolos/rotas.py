# coding: UTF-8
from __future__ import absolute_import

from flask import request, jsonify
from flask.ext.admin import expose, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView

from cidadeiluminada.protocolos.models import Poste, Pendencia, ZonaCidade, Bairro, OrdemServico
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
        return self.render('admin/index_postes.html', pendencias_acao=pendencias_acao)

    @expose('/ordem_servico/nova/')
    def ordem_servico(self):
        zonas = ZonaCidade.query.all()
        return self.render('admin/index_postes.html', zonas=zonas)


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
    form_columns = ('cep', 'numero', 'logradouro', 'bairro', 'cidade', 'estado')
    form_excluded_columns = ('pendencias',)

    create_template = 'admin/model/edit_modelo_cep.html'

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        bairros = Bairro.query
        bairro_id_nome = {bairro.nome: bairro.id for bairro in bairros}
        self._template_args['bairro_id_nome_map'] = bairro_id_nome
        return super(PosteView, self).create_view()


class PendenciaView(_ModelView):
    model = Pendencia
    name = 'Protocolos'
    category = 'Protocolos'

    can_edit = True
    can_delete = True
    can_create = False

    named_filter_urls = True
    column_filters = ('ordens_servico', 'ordens_servico.id')

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


class OrdemServicoView(_ModelView):
    model = OrdemServico
    name = u'Ordem de Serviço'
    category = 'Protocolos'

    form_excluded_columns = ('protocolos')

    edit_template = 'admin/model/edit_os.html'

    form_widget_args = {
        'criacao': {
            'readonly': True,
            'disabled': True,
        },
    }


def init_app(app, config):
    del config['name']
    views = [PosteView(), PendenciaView(), ZonaCidadeView(), BairroView(), OrdemServicoView()]
    return IndexView(name='Principal', **config), views