# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import logging
logger = logging.getLogger(__name__)
from trytond.pool import Pool
from decimal import Decimal
import datetime
from trytond.transaction import Transaction

class PaymentMixIn(object):

    _EOL = '\r\n'
    _SEPARATOR = ';'
    csv_format = False
    monto_total = Decimal('0')
    cantidad_registros = 0
    paymode_type = res = period = type = None
    journal = 'CASH'

    @classmethod
    def attach_collect(cls):
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        collect = cls._collect()
        filename = collect.paymode_type + '-' + cls.type + '-' + \
            datetime.date.today().strftime("%Y-%m-%d")
        attach = Attachment()
        attach.name = filename + '.txt'
        attach.resource = collect
        attach.data = ''.join(cls.res)
        attach.save()

    @classmethod
    def get_domain(cls, period):
        invoice_type = ['out']

        domain = [
            ('state', 'in', ['posted']),
            ('type', 'in', invoice_type),
            ('invoice_date', '>=', period.start_date),
            ('invoice_date', '<=', period.end_date),
            ]

        return domain

    @classmethod
    def get_order(cls):
        return [
                ('invoice_date', 'ASC'),
                ('id', 'ASC')
            ]

    @classmethod
    def lista_campo_ordenados(cls):
        """ Devuelve lista de campos ordenados """
        return []

    @classmethod
    def a_texto(cls, csv_format=False):
        """ Concatena los valores de los campos de la clase y los
        devuelve en una cadena de texto.
        """
        campos = cls.lista_campo_ordenados()
        campos = [x for x in campos if x != '']
        separador = csv_format and cls._SEPARATOR or ''
        return separador.join(campos) + cls._EOL

    @classmethod
    def message_invoice(cls, invoice, collect_result, message):
        pool = Pool()
        CollectTransaction = pool.get('payment.collect.transaction')
        transaction = CollectTransaction()
        transaction.invoice = invoice
        transaction.party = invoice.party
        transaction.collect_result = collect_result
        transaction.collect_message = message
        transaction.save()
        return transaction

    @classmethod
    def pay_invoice(cls, invoice, amount_to_pay, pay_date=None):
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
        if config.defualt_payment_collect_journal:
            pay_journal = config.default_payment_collect_journal
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
    def _collect(cls):
        pool = Pool()
        Collect = pool.get('payment.collect')
        collect = Collect()
        collect.monto_total = cls.monto_total
        collect.cantidad_registros = cls.cantidad_registros
        collect.period = cls.period
        collect.paymode_type = cls.__name__
        collect.type = cls.type
        collect.save()
        return collect

    @classmethod
    def _add_attach_to_collect(cls, collect, return_file):
        Attachment = Pool().get('ir.attachment')
        return_file.seek(0)
        attach = Attachment()
        filename = collect.paymode_type + '-' + cls.type + '-' + \
            datetime.date.today().strftime("%Y-%m-%d")
        attach = Attachment()
        attach.name = filename + '.txt'
        attach.resource = collect
        attach.data = return_file.read()
        attach.save()
