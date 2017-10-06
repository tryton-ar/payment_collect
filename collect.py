# ! -*- coding: utf8 -*-
# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.transaction import Transaction
from trytond.model import Workflow, fields, ModelSQL, ModelView
from trytond.pool import Pool
from trytond.pyson import Eval
import logging
logger = logging.getLogger(__name__)

__all__ = ['Collect', 'CollectSend', 'CollectSendStart', 'CollectReturn',
           'CollectReturnStart']

STATES = [
    ('processing', 'Processing'),
    ('confirmed', 'Confirmed'),
    ('published', 'Published'),
    ('done', 'Done'),
    ]

class Collect(Workflow, ModelSQL, ModelView):
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
    state = fields.Selection(STATES, 'State', readonly=True, required=True)

    @classmethod
    def __setup__(cls):
        super(Collect, cls).__setup__()
        cls._transitions |= set((
                ('processing', 'processing'),
                ('processing', 'confirmed'),
                ('confirmed', 'published'),
                ('published', 'done'),
                ))
        cls._buttons.update({
                #'post_invoices': {},
                #'pay_invoices': {},
                'post_invoices': {
                    'invisible': Eval('state') != 'processing',
                    'readonly': ~Eval('transactions_accepted', []),
                    },
                'pay_invoices': {
                    'invisible': Eval('state') != 'confirmed',
                    },
                })

    @staticmethod
    def default_state():
        return 'processing'

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

    @classmethod
    def pay_invoice(cls, invoice, amount_to_pay, pay_date=None, journal=None):
        logger.info("PAY INVOICE: invoice_id: "+repr(invoice.number))
        # Pagar la invoice
        pool = Pool()
        Currency = pool.get('currency.currency')
        Configuration = pool.get('account.configuration')
        MoveLine = pool.get('account.move.line')
        Date = Pool().get('ir.date')

        if pay_date is None:
            pay_date = Date.today()

        with Transaction().set_context(date=pay_date):
            amount = Currency.compute(invoice.currency,
                amount_to_pay, invoice.company.currency)

        # FIXME migrate 4.0?
        #if invoice.type in ('in_invoice', 'out_credit_note'):
        #    amount = -amount

        reconcile_lines, remainder = \
            invoice.get_reconcile_lines_for_amount(amount)

        config = Configuration(1)

        amount_second_currency = None
        second_currency = None
        if invoice.currency != invoice.company.currency:
            amount_second_currency = amount_to_pay
            second_currency = invoice.currency

        line = None
        pay_journal = None
        if config.default_payment_collect_journal and journal is None:
            pay_journal = config.default_payment_collect_journal
        else:
            pay_journal = journal
        if not invoice.company.currency.is_zero(amount):
            line = invoice.pay_invoice(amount,
                                       pay_journal, pay_date,
                                       invoice.number, amount_second_currency,
                                       second_currency)
        if remainder != Decimal('0.0'):
            return
        else:
            if line:
                reconcile_lines += [line]
            if reconcile_lines:
                MoveLine.reconcile(reconcile_lines)
        # Fin pagar invoice

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def post_invoices(cls, collects):
        '''
        post invoices.
        '''
        Invoice = Pool().get('account.invoice')
        invoices = []
        for collect in collects:
            for transaction in collect.transactions_accepted:
                invoices.append(transaction.invoice)
        Invoice.post(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def pay_invoices(cls, collects):
        '''
        pay invoices.
        '''
        Configuration = Pool().get('account.configuration')
        config = Configuration(1)
        default_journal = None
        if config.default_payment_collect_bccl:
            default_journal = config.default_payment_collect_bccl
        for collect in collects:
            for transaction in collect.transactions_accepted:
                cls.pay_invoice(transaction.invoice,
                    transaction.invoice.amount_to_pay, default_journal)


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
            paymode = PayModeType()
            collects = paymode.generate_collect(self.start)
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
            paymode = PayModeType()
            collects = paymode.return_collect(self.start)
        data = {'res_id': [c.id for c in collects]}
        if len(collects) == 1:
            action['views'].reverse()
        return action, data
