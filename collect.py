# ! -*- coding: utf8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool, PoolMeta
import logging

import datetime
#import StringIO
#from decimal import Decimal
logger = logging.getLogger(__name__)
#import payments

__all__ = ['Collect', 'CollectSend', 'CollectSendStart', 'CollectReturn',
           'CollectReturnStart']
__metaclass__ = PoolMeta

class Collect(ModelSQL, ModelView):
    "Invoice"
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
    paymode_type = fields.Selection('get_types', 'Pay Mode', readonly=True)

    @classmethod
    def get_types(cls):
        paymode = Pool().get('payment.paymode')
        return paymode.get_types()

    def get_rec_name(self, name):
        if self.period and self.paymode_type:
            name = '[' + self.paymode_type + '] ' + self.period.rec_name
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

    period = fields.Many2One('account.period', 'Period', required=True)
    paymode_type = fields.Selection('get_types', 'Pay Mode')

    @classmethod
    def get_types(cls):
        paymode = Pool().get('payment.paymode')
        return paymode.get_types()


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
    generate_collect = StateTransition()

    def transition_generate_collect(self):
        logger.info("should creating new collect..")
        return 'end'


class CollectReturnStart(ModelView):
    'Collect Return Start'
    __name__ = 'payment.collect.return.start'

    period = fields.Many2One('account.period', 'Period', required=True)
    paymode_type = fields.Selection('get_types', 'Pay Mode')
    return_file = fields.Binary('Return File')

    @classmethod
    def get_types(cls):
        paymode = Pool().get('payment.paymode')
        return paymode.get_types()

class CollectReturn(Wizard):
    'Collect Send'
    __name__ = 'payment.collect.return'

    start = StateView(
        'payment.collect.return.start',
        'payment_collect.collect_return_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Return Collect', 'return_collect', 'tryton-ok', default=True),
        ])
    return_collect = StateTransition()

    def transition_return_collect(self):
        logger.info("should creating new return collect..")
        return 'end'
