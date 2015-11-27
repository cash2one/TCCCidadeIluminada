# coding: UTF-8
from __future__ import absolute_import

import os
from datetime import datetime
from StringIO import StringIO
from tempfile import mkstemp

from flask import request, abort, redirect, url_for, jsonify, render_template, send_file, \
    current_app, flash
from flask.ext.admin import Admin, expose, AdminIndexView
from flask.ext.admin.model import typefmt, InlineFormAdmin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.sqla.fields import QuerySelectField
from flask.ext.admin.form.widgets import Select2Widget
from flask.ext.mail import Message
from flask.ext.security import current_user, login_required, roles_accepted, roles_required
from xhtml2pdf import pisa
from wtforms.validators import Required

from cidadeiluminada.models import User, Role
from cidadeiluminada.protocolos import utils
from cidadeiluminada.protocolos.models import Regiao, Bairro, Logradouro, \
    Poste, ItemManutencao, Protocolo, OrdemServico, Servico, Equipamento, Material, \
    PrecoEquipamento
from cidadeiluminada.base import db, mail


class IndexView(AdminIndexView):

    @expose('/')
    @login_required
    def index(self):
        if current_user.has_role('admin'):
            return redirect(url_for('.index_admin'))
        elif current_user.has_role('urbam'):
            return redirect(url_for('.index_urbam'))
        elif current_user.has_role('secretaria'):
            return redirect(url_for('.index_secretaria'))

    @expose('/admin')
    @roles_required('admin')
    def index_admin(self):
        return self.render('admin/index_admin.html')

    @expose('/secretaria')
    @roles_accepted('admin', 'secretaria')
    def index_secretaria(self):
        im_query = ItemManutencao.query.join(Poste).join(Logradouro).join(Bairro).join(Regiao) \
            .filter(ItemManutencao.status == 'aberto')
        regioes_select_map = {}
        regioes_qty_map = {}
        for regiao in db.session.query(Regiao.id, Regiao.nome):
            qty_im = im_query.filter(Regiao.id == regiao.id).count()
            regioes_select_map[regiao.id] = u'Região {}'.format(regiao.nome)
            regioes_qty_map[regiao.id] = qty_im
        return self.render('admin/index_postes.html', regioes_map=regioes_select_map,
                           regioes_qty=regioes_qty_map)

    @expose('/urbam')
    @roles_accepted('admin', 'urbam')
    def index_urbam(self):
        ordens_servico_novas = OrdemServico.query.filter(OrdemServico.nova) \
            .order_by(OrdemServico.id.desc())
        ordens_servico_em_servico = OrdemServico.query.filter(OrdemServico.em_servico) \
            .order_by(OrdemServico.id.desc())
        return self.render('admin/index_urbam.html', ordens_servico_novas=ordens_servico_novas,
                           ordens_servico_em_servico=ordens_servico_em_servico)


default_formatters = dict(typefmt.BASE_FORMATTERS, **{
    datetime: lambda view, value: utils.datetime_format(value)
})


class _ModelView(ModelView):

    category = None

    column_type_formatters = default_formatters

    def is_accessible(self):
        has_secretaria = current_user.has_role('secretaria')
        return current_user.is_authenticated() and has_secretaria

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('name', self.name)
        kwargs.setdefault('category', self.category)
        super(_ModelView, self).__init__(self.model, db.session, *args, **kwargs)


class _UserModelsView(_ModelView):
    def is_accessible(self):
        return current_user.has_role('admin')


class InlinePrecoEquipamentoForm(InlineFormAdmin):
    column_labels = {
        'preco': u'Preço',
        'garantia_mes': 'Garantia em meses',
        'inicio_vigencia': u'Início de vigência'
    }


class EquipamentoView(_ModelView):
    model = Equipamento
    name = u'Equipamento'
    category = u'Equipamentos'

    column_labels = {
        'nome': u'Nome',
        u'precos': u'Preços',
        u'abreviacao': u'Abreviação',
    }

    form_excluded_columns = ['materiais']
    column_exclude_list = ['precos']

    inline_models = [InlinePrecoEquipamentoForm(PrecoEquipamento)]


class PrecoEquipamentoView(_ModelView):
    model = PrecoEquipamento
    name = u'Preços'
    category = u'Equipamentos'


class RegiaoView(_ModelView):
    model = Regiao
    name = u'Região'
    category = u'Endereço'

    form_excluded_columns = ['bairros']

    @expose('/bairros')
    def get_bairros(self):
        regiao_id = request.args['regiao_id']
        regiao = self.model.query.get_or_404(regiao_id)
        im_query = ItemManutencao.query.join(Poste).join(Logradouro).join(Bairro) \
            .filter(ItemManutencao.status == 'aberto')
        bairros = []
        for bairro in regiao.bairros:
            qty_im = im_query.filter(Bairro.id == bairro.id).count()
            serialized = bairro.serialize()
            serialized['qty_im'] = qty_im
            bairros.append(serialized)
        return jsonify({
            'payload': bairros,
        })


class BairroView(_ModelView):
    model = Bairro
    name = 'Bairro'
    category = u'Endereço'

    form_excluded_columns = ['logradouros']

    column_labels = {
        'regiao': u'Região',
    }

    column_filters = ['nome', 'regiao']

    @expose('/itens_manutencao')
    def get_itens_manutencao(self):
        bairro_id = request.args['bairro_id']
        im_query = ItemManutencao.query.join(Poste).join(Logradouro).join(Bairro) \
            .filter(ItemManutencao.status == 'aberto').filter(Bairro.id == bairro_id)
        postes = []
        for item_manutencao in im_query:
            poste = item_manutencao.poste
            serialized = poste.serialize()

            serialized['label'] = u'{} - {} - Nº {}'.format(poste.logradouro.cep,
                                                             poste.logradouro.logradouro,
                                                             poste.numero)
            postes.append(serialized)
        return jsonify({
            'payload': postes,
        })


class LogradouroView(_ModelView):
    model = Logradouro
    name = 'Logradouro'
    category = u'Endereço'

    create_template = 'admin/model/edit_modelo_cep.html'
    edit_template = 'admin/model/edit_modelo_cep.html'

    form_columns = ('cep', 'bairro', 'logradouro')

    form_widget_args = {
        'logradouro': {
            'readonly': True,
        },
    }

    column_labels = {
        'cep': 'CEP',
    }

    column_filters = ['logradouro', 'cep', 'bairro', 'bairro.regiao']

    def _inject_bairros(self):
        bairros = Bairro.query
        bairro_id_nome = {bairro.nome: bairro.id for bairro in bairros}
        self._template_args['bairro_id_nome_map'] = bairro_id_nome

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        self._inject_bairros()
        return super(LogradouroView, self).create_view()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        self._inject_bairros()
        return super(LogradouroView, self).edit_view()


class PosteView(_ModelView):
    def __init__(self, item_manutencao_view, *args, **kwargs):
        super(PosteView, self).__init__(*args, **kwargs)
        self.item_manutencao_view = item_manutencao_view

    model = Poste
    name = 'Postes'
    category = 'Protocolos'

    form_columns = ('logradouro', 'numero')

    edit_template = 'admin/model/edit_poste.html'

    column_labels = {
        'numero': u'Número',
    }

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        cols = self.item_manutencao_view.get_list_columns()
        cols.remove(('poste', 'Poste'))
        self._template_args['list_columns'] = cols
        self._template_args['get_item_manutencao_value'] = self.item_manutencao_view.get_list_value
        return super(PosteView, self).edit_view()


class ProtocoloView(_ModelView):
    model = Protocolo
    name = 'Protocolos 156'
    category = 'Protocolos'

    column_exclude_list = ['item_manutencao']
    column_filters = ['item_manutencao.id']

    named_filter_urls = True

    can_delete = False

    form_excluded_columns = ['item_manutencao']
    edit_template = 'admin/model/edit_protocolo.html'

    column_labels = {
        'criacao': u'Criação',
        'cod_protocolo': u'Código do protocolo',
        'nome_municipe': u'Nome do munícipe',
        'contato_municipe': u'Contato do munícipe',
    }

    form_extra_fields = {
        'poste': QuerySelectField(query_factory=lambda: Poste.query.all(), allow_blank=True,
                                  widget=Select2Widget(),
                                  validators=[Required(u'Campo obrigatório')])
    }

    def on_model_change(self, form, protocolo, is_created):
        if is_created:
            poste = form.poste.data
            item_manutencao = None
            for _item_manutencao in poste.itens_manutencao:
                if _item_manutencao.aberto:
                    item_manutencao = _item_manutencao
                    break
            if not item_manutencao:
                item_manutencao = ItemManutencao(poste=poste)
                db.session.add(item_manutencao)
            item_manutencao.protocolos.append(protocolo)
            db.session.commit()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        protocolo_id = request.args['id']
        protocolo = Protocolo.query.get_or_404(protocolo_id)
        poste_id = protocolo.item_manutencao.poste_id
        self._template_args['poste_id'] = poste_id
        return super(ProtocoloView, self).edit_view()


class ItemManutencaoView(_ModelView):
    model = ItemManutencao
    name = u'Itens Manutenção'
    category = 'Protocolos'

    column_labels = {
        'criacao': u'Criação'
    }


class OrdemServicoView(_ModelView):
    def __init__(self, *args, **kwargs):
        super(OrdemServicoView, self).__init__(*args, **kwargs)
        self.itens_manutencao_adicionar = None

    def item_manutencao_query(self):
        return ItemManutencao.query.join(Poste).filter(ItemManutencao.status == 'aberto')  # NOQA

    model = OrdemServico
    name = u'Ordem de Serviço'
    category = 'Protocolos'

    form_widget_args = {
        'criacao': {
            'readonly': True,
            'disabled': True,
        },
    }

    edit_template = 'admin/model/edit_os.html'
    form_excluded_columns = ['itens_manutencao']
    column_labels = {
        'criacao': u'Criação',
        'id': u'Número',
    }
    column_display_pk = True
    column_default_sort = ('id', True)
    can_edit = True

    column_formatters = {
        'status': lambda v, c, model, n: model.status_map[model.status]
    }

    _urbam_accessible = ['mostrar_pdf', 'enviar_para_servico', 'edit_view', 'atualizar_item_manutencao']

    def is_accessible(self):
        if not current_user.has_role('urbam', invert_for_admin=True):
            return super(OrdemServicoView, self).is_accessible()
        for endpoint in self._urbam_accessible:
            if request.endpoint == 'ordemservico.{}'.format(endpoint):
                return True

    def is_visible(self):
        if current_user.has_role('urbam', invert_for_admin=True):
            return False
        return super(OrdemServicoView, self).is_accessible()

    def on_model_change(self, form, ordem_servico, is_created):
        if is_created:
            itens_manutencao = self.itens_manutencao_adicionar
            self.itens_manutencao_adicionar = None
            for item_manutencao in itens_manutencao:
                item_manutencao.status = 'em_servico'
                assoc = Servico()
                assoc.ordem_servico = ordem_servico
                assoc.item_manutencao = item_manutencao
                db.session.add(assoc)
            db.session.commit()

    @expose('/atualizar_item_manutencao/<ordem_servico_id>', methods=['POST'])
    def atualizar_item_manutencao(self, ordem_servico_id):
        form = request.form
        ordem_servico = OrdemServico.query.get_or_404(ordem_servico_id)
        servico_id = form['servico_id']
        servico = Servico.query.get_or_404(servico_id)
        feito = form['servico_realizado_{}'.format(servico.id)]
        if feito == 'false':
            feito = False
        elif feito == 'true':
            feito = True
        servico.feito = feito
        if feito:
            equipamento_keys = [key for key in form.keys() if u'equipamento' in key]
            equipamento_id_quantidade = {}
            for key in equipamento_keys:
                _, equipamento_id = key.split(u'_')
                equipamento_id_quantidade[int(equipamento_id)] = int(form[key])
            equipamentos = Equipamento.query \
                .filter(Equipamento.id.in_(equipamento_id_quantidade.keys()))
            if all(quantidade == 0 for quantidade in equipamento_id_quantidade.values()):
                flash(u'Serviço deve usar pelo menos um equipamento', u'error')
                return redirect(request.referrer)
            for equipamento in equipamentos:
                quantidade = equipamento_id_quantidade[equipamento.id]
                if quantidade:
                    material = Material(equipamento=equipamento, servico=servico,
                                        quantidade=quantidade)
                    db.session.add(material)
        else:
            servico.obs_urbam = form[u'motivo_urbam']
        if all(servico.feito is not None for servico in ordem_servico.servicos):
            ordem_servico.status = 'feita'
        db.session.commit()
        return redirect(request.referrer)

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        if request.method == 'POST':
            postes_id = request.form.getlist('postes')
            if not postes_id:
                abort(400)
            query = self.item_manutencao_query().filter(Poste.id.in_(postes_id))
            count = query.count()
            if count <= 0 or count > 50:
                abort(400)
            self.itens_manutencao_adicionar = query.all()
        return super(OrdemServicoView, self).create_view()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        self._template_args['equipamentos'] = Equipamento.query.filter(Equipamento.ativo == True)
        self._template_args['os_status_map'] = OrdemServico.status_map
        return super(OrdemServicoView, self).edit_view()

    def _gerar_pdf(self, template):
        fd, temp_path = mkstemp()
        with open(temp_path, 'wb') as pdf_file:
            pisa.CreatePDF(StringIO(template), pdf_file)
        os.close(fd)
        return temp_path

    @expose('/enviar_pdf/<ordem_servico_id>', methods=['POST'])
    def enviar_pdf(self, ordem_servico_id):
        ordem_servico = self.model.query.get_or_404(ordem_servico_id)
        recipients = [request.form['email_urbam']]
        recipients.extend(current_app.config.get('MAIL_DEFAULT_RECIPIENTS'))
        assunto = current_app.config.get('MAIL_DEFAULT_SUBJECT')
        email_template = render_template('email/ordem_servico.txt')
        email = Message(subject=assunto.format(ordem_servico_id=ordem_servico.id),
                        recipients=recipients, body=email_template)
        pdf_template = render_template('pdf/ordem_servico.html', model=ordem_servico)
        pdf_path = self._gerar_pdf(pdf_template)
        with open(pdf_path, 'rb') as pdf_file:
            email.attach('ordem de servico.pdf', 'application/pdf', pdf_file.read())
        mail.send(email)
        flash('Email enviado.', 'success')
        return redirect(url_for('ordemservico.edit_view', id=ordem_servico.id))

    @expose('/pdf/<ordem_servico_id>')
    def mostrar_pdf(self, ordem_servico_id):
        ordem_servico = self.model.query.get_or_404(ordem_servico_id)
        template = render_template('pdf/ordem_servico.html', ordem_servico=ordem_servico)
        if not request.args.get('render_html'):
            pdf_path = self._gerar_pdf(template)
            return send_file(pdf_path,  as_attachment=True, mimetype='application/pdf',
                             attachment_filename=
                             u'Ordem de servico #{}.pdf'.format(ordem_servico.id))
        else:
            return template

    @expose('/servico/<ordem_servico_id>', methods=['POST'])
    def enviar_para_servico(self, ordem_servico_id):
        ordem_servico = self.model.query.get_or_404(ordem_servico_id)
        if ordem_servico.nova:
            ordem_servico.status = 'em_servico'
            db.session.commit()
        return redirect(request.referrer)

    @expose('/confirmar/<ordem_servico_id>', methods=['POST'])
    def confirmar(self, ordem_servico_id):
        ordem_servico = self.model.query.get_or_404(ordem_servico_id)
        if ordem_servico.feita:
            ordem_servico.status = 'confirmada'
            db.session.commit()
        return redirect(request.referrer)


class UserView(_UserModelsView):
    model = User
    name = u'Usuários'
    category = u'Usuários'

    column_labels = {
        'password': u'Senha',
        'active': u'Ativo',
    }


class RoleView(_UserModelsView):
    model = Role
    name = u'Role'
    category = u'Usuários'

    column_labels = {
        'name': u'Nome',
        'description': u'Descrição',
    }

    form_excluded_columns = ['users']


def init_app(app):
    config = {
        'url': '/',
    }
    imv = ItemManutencaoView()
    views = [
        # endereco
        RegiaoView(),
        BairroView(),
        LogradouroView(),
        # protocolos
        ProtocoloView(),
        PosteView(imv),
        imv,  # Retirar em prod
        OrdemServicoView(),
        # equipamentos
        EquipamentoView(),
        PrecoEquipamentoView(),
        # usuarios
        UserView(),
        RoleView(),

    ]
    index = IndexView(name='Principal', **config)
    admin = Admin(app, template_mode='bootstrap3', index_view=index, name='Cidade Iluminada',
                  **config)
    for view in views:
        admin.add_view(view)
