# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
import logging

from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.transaction import Transaction
from trytond.model import Workflow, fields, ModelSQL, ModelView
from trytond.pool import Pool
from trytond.pyson import Eval, Or

logger = logging.getLogger(__name__)


class Collect(Workflow, ModelSQL, ModelView):
    'Collect'
    __name__ = 'payment.collect'

    monto_total = fields.Numeric('Monto total', digits=(16, 2), readonly=True)
    cantidad_registros = fields.Integer('Cantidad de registros', readonly=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    transactions_accepted = fields.One2Many('payment.collect.transaction',
        'collect', 'Accepted transactions', filter=[
            ('collect_result', '=', 'A'),
            ('invoice', '!=', None),
            ], readonly=True)
    transactions_rejected = fields.One2Many('payment.collect.transaction',
        'collect', 'Rejected transactions', filter=[
            ('collect_result', '=', 'R'),
            ('invoice', '!=', None),
            ], readonly=True)
    apply_credit_to_invoices = fields.Many2Many('payment.collect-account.move.line',
        'collect', 'move_line', 'Apply Credit', readonly=True)
    type = fields.Selection([
        (None, ''),
        ('send', 'Send'),
        ('return', 'Return'),
        ], 'Type', readonly=True)
    period = fields.Many2One('account.period', 'Period', readonly=True)
    periods = fields.Many2Many('payment.collect-account.period',
        'collect', 'period', 'Periods', readonly=True)
    state = fields.Selection([
        ('invoicing', 'Invoicing'),
        ('processing', 'Processing'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], 'State', readonly=True, required=True,
        states={'invisible': Eval('type') == 'send'})
    paymode_type = fields.Char('Pay Mode', readonly=True)
    create_invoices_button = fields.Boolean('Create invoices', readonly=True,
        help='Check this box if you create invoices when process return.')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._transitions |= set((
                ('invoicing', 'processing'),
                ('invoicing', 'cancel'),
                ('processing', 'invoicing'),
                ('processing', 'processing'),
                ('processing', 'processing'),
                ('processing', 'confirmed'),
                ('processing', 'cancel'),
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
                })

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
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

    def get_paid_invoices(self):
        return []

    @classmethod
    def apply_credit(cls, transaction):
        pool = Pool()
        Company = pool.get('company.company')
        Configuration = Pool().get('payment_collect.configuration')
        Date = pool.get('ir.date')
        Invoice = pool.get('account.invoice')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        PaymentMethod = pool.get('account.invoice.payment.method')
        Period = pool.get('account.period')
        config = Configuration(1)

        amount = transaction['amount']
        invoice = Invoice(transaction['invoice'])
        date = transaction['date']
        payment_method = PaymentMethod(transaction['payment_method'])
        move_lines = []

        if not date:
            date = Date.today()

        move, = Move.create([{
            'period': Period.find(invoice.company.id, date=date),
            'journal': payment_method.journal.id,
            'date': date,
            'origin': str(invoice),
            'description': 'advance Factura: %s' % invoice.number,
        }])

        move_lines.append({
            'debit': abs(amount),
            'credit': Decimal('0'),
            'account': payment_method.debit_account.id,
            'move': move.id,
            'journal': payment_method.journal.id,
            'period': Period.find(invoice.company.id, date=date),
            'party': (payment_method.debit_account.party_required
                and invoice.party.id or None),
        })

        move_lines.append({
            'debit': Decimal('0'),
            'credit': abs(amount),
            'account': config.advance_account.id,
            'move': move.id,
            'journal': payment_method.journal.id,
            'period': Period.find(invoice.company.id, date=date),
            'party': (invoice.account.party_required
                and invoice.party.id or None),
            'description': 'advance %s' % invoice.number
        })
        created_lines = MoveLine.create(move_lines)
        Move.post([move])
        return created_lines[1]

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
            Invoice.post(invoices)

    @classmethod
    @ModelView.button
    @Workflow.transition('paid')
    def pay_invoices(cls, collects):
        '''
        pay invoices.
        '''
        pool = Pool()
        CollectTransaction = pool.get('payment.collect.transaction')
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')
        apply_credits = []

        for collect in collects:
            to_credit = collect.get_paid_invoices()
            to_pay = (t for t in collect.transactions_accepted
                if t.invoice.state == 'posted')
            period_and_journals = set((Period.find(t.invoice.company.id,
                        t.pay_date), t.payment_method.journal)
                for t in collect.transactions_accepted)

            for period, journal in period_and_journals:
                MoveLine.check_journal_period_modify(Period(period), journal)

            for transaction in to_pay:
                with Transaction().set_context(queue_name='pay_invoice'):
                    CollectTransaction.__queue__.pay_invoice(transaction)

            for transaction in to_credit:
                move_line = cls.apply_credit(transaction)
                apply_credits.append(move_line.id)

            cls.write([collect], {
                'apply_credit_to_invoices': [('add', apply_credits)],
                })

    @classmethod
    @ModelView.button
    @Workflow.transition('processing')
    def create_invoices(cls, collects):
        '''
        create invoices.
        '''
        cls.__queue__._create_invoices(collects)

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, collects):
        pass

    @classmethod
    def _create_invoices(cls, collects):
        pass


class CollectPeriod(ModelSQL):
    'Collect - Period'
    __name__ = 'payment.collect-account.period'
    _table = 'collect_period_rel'
    collect = fields.Many2One('payment.collect', 'Collect', ondelete='CASCADE',
            required=True, select=True)
    period = fields.Many2One('account.period', 'Period',
        ondelete='CASCADE', required=True, select=True)


class CollectMoveLine(ModelSQL):
    'Collect - Credit applied'
    __name__ = 'payment.collect-account.move.line'
    _table = 'collect_credit_account_move_line_rel'
    collect = fields.Many2One('payment.collect', 'Collect',
            ondelete='CASCADE', required=True, select=True)
    move_line = fields.Many2One('account.move.line', 'Line',
            ondelete='CASCADE', required=True, select=True)


class CollectSendStart(ModelView):
    'Send Payment Collect'
    __name__ = 'payment.collect.send.start'

    csv_format = fields.Boolean('CSV format?',
        help='Check this box if you want export to csv format.')
    periods = fields.Many2Many('account.period', None, None, 'Periods')
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
    'Send Payment Collect'
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
    'Return Payment Collect'
    __name__ = 'payment.collect.return.start'

    paymode_type = fields.Selection('get_origin', 'Pay Mode')
    periods = fields.Many2Many('account.period', None, None, 'Periods')
    return_file = fields.Binary('Return File')
    pay_date = fields.Date('Pay date')
    create_invoices = fields.Boolean('Create Invoices',
        help='Check this box if you want to import invoices.')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.periods.states.update({
            'invisible': Eval('paymode_type').in_(cls._paymode_types())
        })
        cls.periods.depends += ['paymode_type']

    @staticmethod
    def default_create_invoices():
        return False

    @staticmethod
    def default_pay_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['']

    @classmethod
    def _paymode_types(cls):
        'Return list of Model names for paymode_type'
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
    'Return Payment Collect'
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
