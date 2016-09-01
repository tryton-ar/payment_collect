# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import logging
logger = logging.getLogger(__name__)
from trytond.pool import Pool
from decimal import Decimal
import datetime

class Payments:

    _EOL = '\r\n'
    _SEPARATOR = ';'
    csv_format = False
    monto_total = Decimal('0')
    cantidad_registros = 0
    paymode_type = res = period = type = None

    def attach_collect(self):
        pool = Pool()
        Collect = pool.get('payment.collect')
        Attachment = pool.get('ir.attachment')
        collect = Collect()
        collect.monto_total = self.monto_total
        collect.cantidad_registros = self.cantidad_registros
        collect.period = self.period
        collect.paymode_type = self.paymode_type
        collect.type = self.type
        collect.save()
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

    def pay_invoice(self, invoice):
        logger.info("PAY INVOICE: invoice_id="+repr(invoice.number))
        # Pagar la invoice
        pool = Pool()
        Currency = pool.get('currency.currency')
        Journal = pool.get('account.journal')
        MoveLine = pool.get('account.move.line')
        amount = Currency.compute(invoice.currency, invoice.amount_to_pay, invoice.company.currency)
        reconcile_lines, remainder = \
            invoice.get_reconcile_lines_for_amount(amount)

        amount_second_currency = None
        second_currency = None
        if invoice.currency != invoice.company.currency:
            amount_second_currency = invoice.amount_to_pay
            second_currency = invoice.currency

        line = None
        pay_journal = Journal.search(['code', '=', 'VA'])[0]
        if not invoice.company.currency.is_zero(amount):
            line = invoice.pay_invoice(amount,
                                       pay_journal, invoice.invoice_date,
                                       invoice.number, amount_second_currency,
                                       second_currency)

        if line:
            reconcile_lines += [line]
        if reconcile_lines:
            MoveLine.reconcile(reconcile_lines)
        # Fin pagar invoice

    def _add_attach_to_collect(self, collect, return_file):
        Attachment = Pool().get('ir.attachment')
        return_file.seek(0)
        attach = Attachment()
        filename = self.start.collect_type
        if self.start.credit_paymode:
            filename = self.start.collect_type + '-' + self.start.credit_paymode.name.lower()
        filename = filename + '-' + datetime.date.today().strftime("%Y-%m-%d")
        attach.name = filename
        attach.resource = collect
        attach.data = return_file.read()
        attach.save()

class banco_credicoop(Payments):

    def generate_collect(self):
        logger.info("generate_collect: banco_credicoop")
        pass
