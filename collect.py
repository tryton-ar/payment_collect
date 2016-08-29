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

__all__ = ['Collect', 'CollectSend', 'CollectSendStart', 'CollectReturn',
           'CollectReturnStart', 'CollectMessage']
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
        ('', ''),
        ('send', 'Send'),
        ('return', 'Return'),
        ], 'Type', readonly=True)
    paymode_type = fields.Many2One('payment.paymode', 'Pay Mode', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    end_date = fields.Date('End date', readonly=True)

    def get_rec_name(self, name):
        return self.type
    #    if self.type and self.credit_paymode is None:
    #        name = '[' + self.type + '][' +  self.collect_type + ']'
    #    elif self.type and self.credit_paymode:
    #        name = '[' + self.type + '][' +  self.collect_type + '] ' + self.credit_paymode.name.lower()
    #    elif self.type and self.debit_paymode:
    #        name = '[' + self.type + '][' +  self.collect_type + '] ' + self.debit_paymode.name.lower()
    #    else:
    #        name = self.name

    #    return name

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
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    expiration_date = fields.Date('Expiration date')
    paymode_type = fields.Selection('get_types', 'Pay Mode')

    @classmethod
    def get_types(cls):
        paymode = Pool().get('payment.paymode')
        return paymode.get_types()


class CollectMessage(ModelView):
    'Collect Message'
    __name__ = 'payment.collect.wizard.message'
    message = fields.Text('Message', readonly=True)


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
    message = StateView(
        'payment.collect.wizard.message',
        'payment_collect.collect_wizard_message_view', [
            Button('Previous', 'start', 'tryton-go-previous', default=True),
            Button('Close', 'end', 'tryton-close'),
        ])
    generate_collect = StateTransition()

    def default_start(self, fields):
        res = {}
        return res

    def default_message(self, fields):
        res = {'message': self.message.message}
        return res

    def transition_generate_collect(self):
        logger.info("should creating new collect..")
        self.start.paymode.generate_collect()

        self.message.message = u'Se ha generado el archivo con éxito.'
        return 'message'

    def _attach_collect(self, monto_total, cantidad_registros, identificador_empresa, lines):
        logger.info("Monto total: " + str(monto_total))
        logger.info("Cantidad de registros: " + str(cantidad_registros))
        pool = Pool()
        Collect = pool.get('payment.collect')
        Attachment = pool.get('ir.attachment')
        collect = Collect()
        collect.monto_total = monto_total
        collect.cantidad_registros = cantidad_registros
        collect.start_date = self.start.start_date
        collect.end_date = self.start.end_date
        collect.collect_type = self.start.collect_type
        collect.type = 'send'
        collect.credit_paymode = self.start.credit_paymode
        collect.save()
        if collect.collect_type == 'debit_credicoop':
            filename = 'main' + identificador_empresa + '_' + datetime.date.today().strftime("%d%m")
        else:
            filename = collect.collect_type + '-' + identificador_empresa + '-' +  datetime.date.today().strftime("%Y-%m-%d")
        attach = Attachment()
        attach.name = filename + '.txt'
        attach.resource = collect
        attach.data = lines
        attach.save()
        self.message.message = u'Se ha generado el archivo con éxito.'


class CollectReturnStart(ModelView):
    'Collect Return Start'
    __name__ = 'payment.collect.return.start'
    collect_type = fields.Selection([
        ('', ''),
        ('debit_credicoop', 'Debito Banco Credicoop'),
        ('credit_card', 'Credit Card'),
        ], 'Collect')
    #credit_paymode = fields.Many2One('account.paymode.credit_card', 'Credit Card')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    return_file = fields.Binary('Return File')


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
    message = StateView(
        'payment.collect.wizard.message',
        'payment_collect.collect_wizard_message_view', [
            Button('Previous', 'start', 'tryton-go-previous', default=True),
            Button('Close', 'end', 'tryton-close'),
        ])

    def default_start(self, fields):
        res = {}
        return res

    def default_message(self, fields):
        res = {'message': self.message.message}
        return res

    def transition_return_collect(self):
        # Return Collect
        logger.info("should creating new return collect..")
        if self.start.collect_type == 'debit_credicoop':
            self.return_collect_debit_credicoop()
            return 'message'
        elif self.start.collect_type == 'credit_card':
            if self.start.credit_paymode.name.lower() == 'visa':
                self.return_collect_credit_card_visa()
            if self.start.credit_paymode.name.lower() == 'mastercard':
                self.return_collect_credit_card_mastercard()
            if self.start.credit_paymode.name.lower() == 'cabal':
                self.return_collect_credit_card_cabal()
            return 'message'

        return 'end'

    def _collect(self):
        Collect = Pool().get('payment.collect')
        collect = Collect()
        collect.start_date = self.start.start_date
        collect.end_date = self.start.end_date
        collect.collect_type = self.start.collect_type
        collect.type = 'return'
        collect.credit_paymode = self.start.credit_paymode
        collect.save()
        return collect

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
