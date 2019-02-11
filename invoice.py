# ! -*- coding: utf8 -*-
# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Not, Bool
from trytond.transaction import Transaction

__all__ = ['Invoice', 'CollectTransaction']


class CollectTransaction(ModelSQL, ModelView):
    'Collect Transaction'
    __name__ = 'payment.collect.transaction'

    collect_result = fields.Selection([
           ('', 'n/a'),
           ('A', 'Aceptado'),
           ('R', 'Rechazado')], 'Resultado', readonly=True,
        help=u"Resultado procesamiento de la Cobranza")
    collect_message = fields.Text('Mensaje', readonly=True,
                                  help=u"Mensaje de error u observación")
    invoice = fields.Many2One('account.invoice', 'Invoice', readonly=True)
    collect = fields.Many2One('payment.collect', 'Payment Collect')
    party = fields.Function(fields.Many2One('party.party', 'Party',
                                            readonly=True), 'get_party')
    phone = fields.Function(fields.Char('Phone', readonly=True),
                            'get_party_contact')
    email = fields.Function(fields.Char('E-mail', readonly=True),
                            'get_party_contact')
    invoice_state = fields.Function(fields.Char('Invoice state',
                                                readonly=True),
                                    'get_invoice_state')
    amount = fields.Function(fields.Char('Amount', readonly=True),
                             'get_invoice_amount')
    pay_date = fields.Date('Pay Date', readonly=True)
    pay_amount = fields.Numeric('Pay Amount', digits=(16, 2), readonly=True)
    journal = fields.Many2One('account.journal', 'Journal', required=True,
            domain=[('type', '=', 'cash')], readonly=True)

    def get_party(self, name):
        return self.invoice.party.id

    def get_party_contact(self, name):
        return self.invoice.party.get_mechanism(name)

    def get_invoice_state(self, name):
        return dict(self.invoice.fields_get()['state']['selection'])[self.invoice.state]

    def get_invoice_amount(self, name):
        return self.invoice.total_amount


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    collect_transactions = fields.One2Many(
        'payment.collect.transaction',
        'invoice', u"Collect Transaction",
        readonly=True)

    paymode = fields.Many2One(
        'payment.paymode',
        'Pay mode', domain=[('party', '=', Eval('party'))], states={
            'readonly': Not(Bool(Eval('state').in_(['draft', 'validated']))),
        }, depends=['party', 'state'])

    def __get_paymode(self):
        '''
        Return a pay mode.
        '''
        if self.party:
            if (self.type == 'out' and self.party.customer_paymode):
                self.paymode = self.party.customer_paymode
            if (self.type == 'in' and self.party.supplier_paymode):
                self.paymode = self.party.supplier_paymode

    @fields.depends('party', 'payment_term', 'type', 'company', 'paymode')
    def on_change_party(self):
        super(Invoice, self).on_change_party()
        self.paymode = None
        self.__get_paymode()

    @classmethod
    def compute_default_paymode(cls, values):
        pool = Pool()
        Party = pool.get('party.party')
        Company = pool.get('company.company')

        payment_type = values.get('payment_type')
        party = values.get('party')
        _type = values.get('type')
        company = values.get('company', Transaction().context.get('company'))

        changes = {}
        if not payment_type and party and _type and company:
            invoice = cls()
            invoice.party = Party(party)
            invoice.type = _type
            invoice.company = Company(company)
            invoice.payment_type = None
            invoice.__get_paymode()
            if hasattr(invoice, 'paymode'):
                changes['paymode'] = invoice.paymode

        return changes

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values.update(cls.compute_default_paymode(values))
        return super(Invoice, cls).create(vlist)

    @classmethod
    def copy(cls, invoices, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['collect_transactions'] = None
        return super(Invoice, cls).copy(invoices, default=default)
