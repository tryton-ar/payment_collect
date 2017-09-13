# ! -*- coding: utf8 -*-
# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool
import logging
logger = logging.getLogger(__name__)

__all__ = ['Collect', 'CollectSend', 'CollectSendStart', 'CollectReturn',
           'CollectReturnStart']


class Collect(ModelSQL, ModelView):
    'Collect'
    __name__ = 'payment.collect'

    monto_total = fields.Numeric('Monto total', digits=(16, 2), readonly=True)
    cantidad_registros = fields.Integer('Cantidad de registros', readonly=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    transactions_accepted = fields.Function(fields.One2Many(
        'payment.collect.transaction', None,
        'Transactions Accepted'), 'get_transactions_accepted')
    transactions_rejected = fields.Function(fields.One2Many(
        'payment.collect.transaction', None,
        'Transactions Rejected'), 'get_transactions_rejected')
    type = fields.Selection([
        (None, ''),
        ('send', 'Send'),
        ('return', 'Return'),
        ], 'Type', readonly=True)
    period = fields.Many2One('account.period', 'Period', readonly=True)
    paymode_type = fields.Char('Pay Mode', readonly=True)

    def get_rec_name(self, name):
        if self.paymode_type:
            name = self.paymode_type
        return name

    def get_transactions_accepted(self, name):
        transactions = set()
        pool = Pool()
        CollectTransaction = pool.get('payment.collect.transaction')
        transactions_accepted = CollectTransaction.search([
            ('collect', '=', self.id), ('collect_result', '=', 'A')])
        for transaction in transactions_accepted:
            transactions.add(transaction.id)
        return list(transactions)

    def get_transactions_rejected(self, name):
        transactions = set()
        pool = Pool()
        CollectTransaction = pool.get('payment.collect.transaction')
        transactions_rejected = CollectTransaction.search(
            [('collect', '=', self.id), ('collect_result', '=', 'R')])
        for transaction in transactions_rejected:
            transactions.add(transaction.id)
        return list(transactions)


class CollectSendStart(ModelView):
    'Collect Send Start'
    __name__ = 'payment.collect.send.start'

    csv_format = fields.Boolean('CSV format',
        help='Check this box if you want export to csv format.')
    period = fields.Many2One('account.period', 'Period', required=True)
    expiration_date = fields.Date('Fecha de vencimiento')
    paymode_type = fields.Selection('get_origin', 'Pay Mode')

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['']

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]


class CollectSend(Wizard):
    'Collect Send'
    __name__ = 'payment.collect.send'

    start = StateView(
        'payment.collect.send.start',
        'payment_collect.collect_send_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate Collect', 'generate_collect', 'tryton-ok',
                   default=True),
        ])
    generate_collect = StateAction(
        'payment_collect.act_payment_collect')

    def do_generate_collect(self, action):
        collects = []
        if self.start.paymode_type:
            PayModeType = Pool().get(self.start.paymode_type)
            collects = PayModeType.generate_collect(self.start)
        data = {'res_id': [c.id for c in collects]}
        if len(collects) == 1:
            action['views'].reverse()
        return action, data


class CollectReturnStart(ModelView):
    'Collect Return Start'
    __name__ = 'payment.collect.return.start'

    paymode_type = fields.Selection('get_origin', 'Pay Mode')
    return_file = fields.Binary('Return File')
    pay_date = fields.Date('Pay date')
    period = fields.Many2One('account.period', 'Period', required=True)

    @classmethod
    def default_csv_format(cls):
        Date = Pool().get('ir.date')
        return Date.today()

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['']

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]


class CollectReturn(Wizard):
    'Collect Send'
    __name__ = 'payment.collect.return'

    start = StateView(
        'payment.collect.return.start',
        'payment_collect.collect_return_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Return Collect', 'return_collect', 'tryton-ok', default=True),
        ])
    return_collect = StateAction(
        'payment_collect.act_payment_collect')

    def do_return_collect(self, action):
        collects = []
        if self.start.paymode_type:
            PayModeType = Pool().get(self.start.paymode_type)
            collects = PayModeType.return_collect(self.start)
        data = {'res_id': [c.id for c in collects]}
        if len(collects) == 1:
            action['views'].reverse()
        return action, data
