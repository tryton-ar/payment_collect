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
    ('invoicing', 'Invoicing'),
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
    transactions_accepted = fields.One2Many('payment.collect.transaction',
        'collect','Accepted transactions', filter=[
            ('collect_result', '=', 'A'),
            ('invoice', '!=', None),
            ], readonly=True)
    transactions_rejected = fields.One2Many('payment.collect.transaction',
        'collect','Rejected transactions', filter=[
            ('collect_result', '=', 'R'),
            ('invoice', '!=', None),
            ], readonly=True)
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
    create_invoices_button = fields.Boolean('Create invoices', readonly=True,
        help='Check this box if you create invoices when process return.')

    @classmethod
    def __setup__(cls):
        super(Collect, cls).__setup__()
        cls._transitions |= set((
                ('invoicing', 'processing'),
                ('processing', 'processing'),
                ('processing', 'confirmed'),
                ('confirmed', 'paid'),
                ('paid', 'done'),
                ))
        cls._buttons.update({
                'create_invoices': {
                    'invisible': Or(Eval('type') == 'send',
                        Eval('state') != 'processing',
                        ~Eval('create_invoices_button', True)),
                    'readonly': Or(Eval('transactions_accepted', []),
                        Eval('transactions_rejected', []),
                        ),
                    },
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
    def default_type():
        return Transaction().context.get('type', None)

    @staticmethod
    def default_state():
        return 'processing'

    def get_rec_name(self, name):
        if self.paymode_type:
            name = self.paymode_type
        return name

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
            to_post = (t for t in collect.transactions_accepted
                if t.invoice.state == 'validated')
            for transaction in to_post:
                transaction.invoice.invoice_date = None
                invoices.append(transaction.invoice)

        if invoices:
            Invoice.__queue__.post(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('paid')
    def pay_invoices(cls, collects):
        '''
        pay invoices.
        '''

        CollectTransaction = Pool().get('payment.collect.transaction')
        for collect in collects:
            to_pay = (t for t in collect.transactions_accepted
                if t.invoice.state == 'posted')
            for transaction in to_pay:
                with Transaction().set_context(queue_name='pay_invoice'):
                    CollectTransaction.__queue__.pay_invoice(transaction)

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

    @classmethod
    @ModelView.button
    @Workflow.transition('processing')
    def create_invoices(cls, collects):
        '''
        create invoices.
        '''
        cls.__queue__._create_invoices(collects)


class CollectSendStart(ModelView):
    'Collect Send Start'
    __name__ = 'payment.collect.send.start'

    csv_format = fields.Boolean('CSV format?',
        help='Check this box if you want export to csv format.')
    period = fields.Many2One('account.period', 'Period', required=True)
    expiration_date = fields.Date('Fecha de vencimiento')
    paymode_type = fields.Selection('get_origin', 'Pay Mode')

    @staticmethod
    def default_csv_format():
        return False

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

    @staticmethod
    def default_pay_date():
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
