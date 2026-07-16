# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
import logging

from trytond.pool import Pool
from trytond.transaction import Transaction

logger = logging.getLogger(__name__)


class PaymentMixIn:
    __slots__ = ()

    _EOL = '\r\n'
    _SEPARATOR = ';'
    csv_format = False
    monto_total = Decimal('0')
    cantidad_registros = 0
    filename = None
    paymode_type = None
    res = None
    periods = None
    type = None
    collect = None
    return_file = None

    @classmethod
    def attach_collect(cls, collect, res, filename):
        Attachment = Pool().get('ir.attachment')
        attach = Attachment()
        attach.name = filename
        attach.resource = collect
        if res:
            attach.data = ''.join(res).encode('utf8')
        else:
            attach.data = collect.return_file
        attach.save()
        return collect

    @classmethod
    def get_domain(cls, periods=None):
        Config = Pool().get('payment_collect.configuration')
        config = Config(1)
        invoice_type = ['out']

        domain = [
            ('state', 'in', [config.when_collect_payment]),
            ('type', 'in', invoice_type),
            ]
        if periods:
            domain.append(('move.period', 'in', periods))

        return domain

    @classmethod
    def get_order(cls):
        return [('invoice_date', 'ASC'), ('id', 'ASC')]

    @classmethod
    def lista_campo_ordenados(cls, linea):
        """ Devuelve lista de campos ordenados """
        return []

    @classmethod
    def a_texto(cls, linea, csv_format=False):
        """ Concatena los valores de los campos de la clase y los
        devuelve en una cadena de texto.
        """
        campos = cls.lista_campo_ordenados(linea)
        campos = [x for x in campos if x != '']
        separador = csv_format and cls._SEPARATOR or ''
        return separador.join(campos) + cls._EOL

    @classmethod
    def message_invoice(cls, invoices, collect_result, message, pay_amount,
            pay_date=None, payment_method=None):
        pool = Pool()
        CollectTransaction = pool.get('payment.collect.transaction')
        Configuration = pool.get('payment_collect.configuration')
        config = Configuration(1)
        invoice, = invoices
        transaction = CollectTransaction()
        transaction.invoice = invoice
        transaction.pay_date = pay_date
        transaction.pay_amount = pay_amount
        if not payment_method:
            payment_method = config.payment_method
        transaction.payment_method = payment_method
        transaction.party = invoice.party
        transaction.collect_result = collect_result
        transaction.collect_message = message
        transaction.save()
        return transaction

    @classmethod
    def pay_invoice(cls, invoice, amount_to_pay, pay_date=None,
            payment_method=None):
        logger.info("pay_invoice: %s", invoice.number)
        pool = Pool()
        Currency = pool.get('currency.currency')
        Configuration = pool.get('account.configuration')
        MoveLine = pool.get('account.move.line')
        Date = pool.get('ir.date')

        if pay_date is None:
            pay_date = Date.today()

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
        pay_payment_method = None
        if config.payment_method and payment_method is None:
            pay_payment_method = config.payment_method
        else:
            pay_payment_method = payment_method
        if not invoice.company.currency.is_zero(amount):
            line = invoice.pay_invoice(amount, pay_payment_method, pay_date,
                invoice.number, amount_second_currency, second_currency)
        if remainder != Decimal('0.0'):
            return
        else:
            if line:
                reconcile_lines += [line]
            if reconcile_lines:
                MoveLine.reconcile(reconcile_lines)

    def create_collect(self):
        pool = Pool()
        Collect = pool.get('payment.collect')
        Model = pool.get('ir.model')

        model, = Model.search([('model', '=', self.__name__)])
        collect = Collect()
        collect.type = self.type
        collect.paymode_type = model.name
        collect.cantidad_registros = self.cantidad_registros
        collect.monto_total = self.monto_total
        if self.periods:
            collect.periods = self.periods
        collect.save()
        self.collect = collect
        return collect

    def return_collect(self, start, tabla_codigos={}):
        self.type = 'return'
        self.return_file = start.return_file
        if hasattr(start, 'periods'):
            self.periods = start.periods
        self.create_collect()
        self.invoices_id = {
            'accepted_invoices': [],
            'rejected_invoices': [],
            }
        self.codigo_retorno = {}
        self.tabla_codigos = tabla_codigos
        return []

    @classmethod
    def get_format_date(cls):
        "get_format_date"
        pool = Pool()
        Lang = pool.get('ir.lang')
        format_ = '%d/%m/%Y'
        es_419 = Lang(
            code='es_419',
            date=format_,
            )
        return (lambda value, format=None:
            value and es_419.strftime(value, format or format_) or '')

    @classmethod
    def get_format_number(cls):
        "get_format_number"
        pool = Pool()
        Lang = pool.get('ir.lang')
        es_419 = Lang(
            decimal_point=',',
            thousands_sep='.',
            grouping='[]',
            )
        return lambda value: es_419.format('%.2f', value)
