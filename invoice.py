# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from decimal import Decimal

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Not, Bool
from trytond.transaction import Transaction

__all__ = ['Invoice', 'CollectTransaction']
logger = logging.getLogger(__name__)


class CollectTransaction(ModelSQL, ModelView):
    'Collect Transaction'
    __name__ = 'payment.collect.transaction'

    collect_result = fields.Selection([
            ('', 'n/a'),
            ('A', 'Aceptado'),
            ('R', 'Rechazado'),
            ], 'Resultado', readonly=True,
        help="Resultado procesamiento de la Cobranza")
    collect_message = fields.Text('Mensaje', readonly=True,
        help="Mensaje de error u observación")
    invoice = fields.Many2One('account.invoice', 'Invoice', readonly=True,
        ondelete='CASCADE')
    collect = fields.Many2One('payment.collect', 'Payment Collect')
    party = fields.Function(fields.Many2One('party.party', 'Party',
            readonly=True), 'get_party')
    phone = fields.Function(fields.Char('Phone', readonly=True),
        'get_party_contact')
    email = fields.Function(fields.Char('E-mail', readonly=True),
        'get_party_contact')
    invoice_state = fields.Function(fields.Char('Invoice state',
            readonly=True), 'get_invoice_state')
    invoice_date = fields.Function(fields.Date('Invoice date'),
            'get_invoice_date')
    amount = fields.Function(fields.Numeric('Amount', digits=(16, 2),
            readonly=True), 'get_invoice_amount')
    pay_date = fields.Date('Pay Date', readonly=True)
    pay_amount = fields.Numeric('Pay Amount', digits=(16, 2), readonly=True)
    payment_method = fields.Many2One('account.invoice.payment.method',
        'Payment Method', required=True, readonly=True)

    @classmethod
    def __register__(cls, module_name):
        super(CollectTransaction, cls).__register__(module_name)

        table = cls.__table_handler__(cls, module_name)
        # Migration from 5.0: remove journal column
        table.drop_column('journal')

    def get_party(self, name):
        if hasattr(self.invoice, 'party'):
            return self.invoice.party.id
        return None

    def get_party_contact(self, name):
        if hasattr(self.invoice, 'party'):
            return self.invoice.party.get_mechanism(name)
        return ''

    def get_invoice_state(self, name):
        if hasattr(self.invoice, 'state'):
            return self.invoice.state
        return None

    def get_invoice_date(self, name):
        if hasattr(self.invoice, 'invoice_date'):
            return self.invoice.invoice_date
        return None

    def get_invoice_amount(self, name):
        if hasattr(self.invoice, 'total_amount'):
            return self.invoice.total_amount
        return None

    @classmethod
    def pay_invoice(cls, transaction):
        '''
        Adds a payment of amount to an invoice using the
        payment_method, date and description.
        '''
        pool = Pool()
        Currency = pool.get('currency.currency')
        Configuration = pool.get('payment_collect.configuration')
        MoveLine = pool.get('account.move.line')

        invoice = transaction.invoice
        amount_to_pay = transaction.amount
        payment_method = transaction.payment_method
        pay_date = transaction.pay_date
        config = Configuration(1)

        with Transaction().set_context(date=pay_date):
            amount = Currency.compute(invoice.currency,
                amount_to_pay, invoice.company.currency)

        with Transaction().set_context(date=pay_date):
            amount = Currency.compute(invoice.currency,
                amount_to_pay, invoice.company.currency)
            amount_invoice = Currency.compute(
                invoice.currency, amount_to_pay, invoice.currency)

        reconcile_lines, remainder = \
            invoice.get_reconcile_lines_for_amount(amount)

        amount_second_currency = None
        second_currency = None
        if invoice.currency != invoice.company.currency:
            amount_second_currency = amount_to_pay
            second_currency = invoice.currency

        #if amount_invoice > invoice.amount_to_pay:
        #    lang = Lang.get()
        #    raise PayInvoiceError(
        #        gettext('account_invoice'
        #            '.msg_invoice_pay_amount_greater_amount_to_pay',
        #            invoice=invoice.rec_name,
        #            amount_to_pay=lang.currency(
        #                invoice.amount_to_pay, invoice.currency)))

        pay_payment_method = None
        if config.payment_method and payment_method is None:
            pay_payment_method = config.payment_method
        else:
            pay_payment_method = payment_method

        line = None
        if not invoice.company.currency.is_zero(amount):
            line = invoice.pay_invoice(amount,
                pay_payment_method, pay_date,
                invoice.number, amount_second_currency,
                second_currency)

        if remainder != Decimal('0.0'):
            return
        else:
            if line:
                reconcile_lines += [line]
            if reconcile_lines:
                MoveLine.reconcile(reconcile_lines)


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    collect_transactions = fields.One2Many('payment.collect.transaction',
        'invoice', "Collect Transaction", readonly=True)
    paymode = fields.Many2One(
        'payment.paymode',
        'Pay mode', domain=[('party', '=', Eval('party', -1))],
        states={
            'readonly': Not(Bool(Eval('state').in_(['draft', 'validated']))),
        }, depends=['state', 'party'])

    @fields.depends('party', 'type')
    def on_change_with_paymode(self):
        paymode = None
        if self.party:
            if self.type == 'out':
                paymode = self.party.customer_paymode
            elif self.type == 'in':
                paymode = self.party.supplier_paymode
        return paymode.id if paymode else None

    @classmethod
    def copy(cls, invoices, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['collect_transactions'] = None
        default['paymode'] = None
        return super(Invoice, cls).copy(invoices, default=default)
