# ! -*- coding: utf8 -*-
# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.transaction import Transaction
from trytond.model import Workflow, fields, ModelSQL, ModelView
from trytond.pool import Pool
from trytond.pyson import Eval, Or
import logging
logger = logging.getLogger(__name__)

__all__ = ['Collect', 'CollectSend', 'CollectSendStart', 'CollectReturn',
           'CollectReturnStart', 'PayInvoicesCron']

STATES = [
    ('processing', 'Processing'),
    ('confirmed', 'Confirmed'),
    ('paid', 'Paid'),
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
    state = fields.Selection(STATES, 'State', readonly=True,
        required=True, states={
            'invisible': Eval('type') == 'send',
        })
    pay_invoices_cron = fields.Many2One('payment.collect.pay_invoices_cron',
        'Pay Invoices Cron')

    @classmethod
    def __setup__(cls):
        super(Collect, cls).__setup__()
        cls._transitions |= set((
                ('processing', 'processing'),
                ('processing', 'confirmed'),
                ('confirmed', 'paid'),
                ('paid', 'done'),
                ))
        cls._buttons.update({
                'post_invoices': {
                    'invisible': Or(Eval('type') == 'send',
                        Eval('state') != 'processing'),
                    'readonly': ~Eval('transactions_accepted', []),
                    },
                'pay_invoices': {
                    'invisible': Or(Eval('type') == 'send',
                        Eval('state') != 'confirmed'),
                    },
                'publish_invoices': {
                    'invisible': Or(Eval('type') == 'send',
                        Eval('state') != 'paid'),
                    },
                })

    @classmethod
    def view_attributes(cls):
        return [
            ('/form//page[@id="accepted_invoices"]|/form//page[@id="rejected_invoices"]',
                'states', {
                    'invisible': Eval('type') == 'send',
                })
            ]

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
    def pay_invoice(cls, transaction):
        '''
        Adds a payment of amount to an invoice using the journal, date and
        description.
        '''
        pool = Pool()
        Currency = pool.get('currency.currency')
        Configuration = pool.get('account.configuration')
        MoveLine = pool.get('account.move.line')

        invoice = transaction.invoice
        amount_to_pay = transaction.pay_amount
        journal = transaction.journal
        pay_date = transaction.pay_date

        with Transaction().set_context(date=pay_date):
            amount = Currency.compute(invoice.currency,
                amount_to_pay, invoice.company.currency)

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

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def post_invoices(cls, collects):
        '''
        post invoices.
        '''
        pool = Pool()
        Invoice = pool.get('account.invoice')
        invoices = []
        for collect in collects:
            transactions_to_post = [i for i in collect.transactions_accepted
                 if i.invoice.state == 'validated']
            for transaction in transactions_to_post:
                transaction.invoice.invoice_date = None
                invoices.append(transaction.invoice)

        Invoice.post(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('paid')
    def pay_invoices(cls, collects):
        '''
        pay invoices.
        '''
        pool = Pool()
        Configuration = pool.get('account.configuration')
        config = Configuration(1)
        if config.collect_use_cron:
            PayInvoicesCron = pool.get('payment.collect.pay_invoices_cron')
            pay_invoices_cron = PayInvoicesCron()
            pay_invoices_cron.collects = collects
            pay_invoices_cron.paid = False
            pay_invoices_cron.save()
        else:
            for collect in collects:
                for transaction in collect.transactions_accepted:
                    cls.pay_invoice(transaction)

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def publish_invoices(cls, collects):
        '''
        publish invoices.
        '''
        InvoiceReport = Pool().get('account.invoice', type='report')
        invoices = []
        for collect in collects:
            for transaction in collect.transactions_accepted:
                invoices.append(transaction.invoice)
        InvoiceReport.execute([i.id for i in invoices], {})


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
        'payment_collect.act_payment_collect_send')

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
            Button('Return Collect', 'return_collect', 'tryton-ok',
                default=True),
        ])
    return_collect = StateAction(
        'payment_collect.act_payment_collect_return')

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


class PayInvoicesCron(ModelSQL, ModelView):
    'Pay Invoices Cron'
    __name__ = 'payment.collect.pay_invoices_cron'

    collects = fields.One2Many('payment.collect', 'pay_invoices_cron',
        'Collects')
    paid = fields.Boolean('Paid')

    @classmethod
    def pay_invoices_cron(cls, args=None):
        '''
        Cron to pay invoices.
        '''
        logger.info('Start Scheduler - pay invoices.')
        pay_invoices_cron_data = []
        pay_invoices_cron_data = cls.search(['paid', '=', False])
        if pay_invoices_cron_data != []:
            pay_invoices_cron_data = pay_invoices_cron_data[0]
        if pay_invoices_cron_data and pay_invoices_cron_data.collects:
            logger.info('Pay invoices - processing collects transactions')
            for collect in pay_invoices_cron_data.collects:
                for transaction in collect.transactions_accepted:
                    if transaction.invoice.state == 'posted':
                        collect.pay_invoice(transaction)
                        logger.debug('Pay invoices - Invoice: %s paid',
                            transaction.invoice.id)

            logger.info('Pay invoices - Invoices paid')
            pay_invoices_cron_data.paid = True
            pay_invoices_cron_data.save()
        else:
            logger.info('Pay invoices - no collects pending')

        logger.info('End Scheduler - Pay invoices')
