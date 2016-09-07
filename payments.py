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

class Payments:

    _EOL = '\r\n'
    _SEPARATOR = ';'
    csv_format = False
    monto_total = Decimal('0')
    cantidad_registros = 0
    paymode_type = res = period = type = None
    journal = 'CASH'

    def attach_collect(self):
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        collect = self._collect()
        filename = collect.paymode_type + '-' + self.type + '-' + datetime.date.today().strftime("%Y-%m-%d")
        attach = Attachment()
        attach.name = filename + '.txt'
        attach.resource = collect
        attach.data = ''.join(self.res)
        attach.save()

    def get_domain(self):
        invoice_type = ['out_invoice', 'out_credit_note']

        domain = [
            ('state', 'in', ['posted']),
            ('type', 'in', invoice_type),
            ('invoice_date', '>=', self.period.start_date),
            ('invoice_date', '<=', self.period.end_date),
            ]

        return domain

    def get_order(self):
        return [
                ('invoice_date', 'ASC'),
                ('id', 'ASC')
            ]

    def lista_campo_ordenados(self):
        """ Devuelve lista de campos ordenados """
        return []

    def a_texto(self, csv_format=False):
        """ Concatena los valores de los campos de la clase y los
        devuelve en una cadena de texto.
        """
        campos = self.lista_campo_ordenados()
        campos = [x for x in campos if x != '']
        separador = csv_format and self._SEPARATOR or ''
        return separador.join(campos) + self._EOL

    def message_invoice(self, invoice, collect_result, message):
        pool = Pool()
        CollectTransaction = pool.get('payment.collect.transaction')
        transaction = CollectTransaction()
        transaction.invoice = invoice
        transaction.party = invoice.party
        transaction.collect_result = collect_result
        transaction.collect_message = message
        transaction.save()
        return transaction

    def pay_invoice(self, invoice, amount_to_pay, pay_date=None):
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

        if invoice.type in ('in_invoice', 'out_credit_note'):
            amount = -amount

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

    def _collect(self):
        pool = Pool()
        Collect = pool.get('payment.collect')
        collect = Collect()
        collect.monto_total = self.monto_total
        collect.cantidad_registros = self.cantidad_registros
        collect.period = self.period
        collect.paymode_type = self.paymode_type
        collect.type = self.type
        collect.save()
        return collect

    def _add_attach_to_collect(self, collect, return_file):
        Attachment = Pool().get('ir.attachment')
        return_file.seek(0)
        attach = Attachment()
        filename = collect.paymode_type + '-' + self.type + '-' + datetime.date.today().strftime("%Y-%m-%d")
        attach = Attachment()
        attach.name = filename + '.txt'
        attach.resource = collect
        attach.data = return_file.read()
        attach.save()
