# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.model import MultiValueMixin, ValueMixin
from trytond.pool import Pool
from trytond import backend
from trytond.tools.multivalue import migrate_property
from trytond.pyson import Eval
from trytond.modules.account_invoice.invoice import STATES
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)

__all__ = ['Configuration', 'ConfigurationPaymentCollectAccount']


class Configuration(
        ModelSingleton, ModelSQL, ModelView, CompanyMultiValueMixin):
    'PaymentCollect Configuration'
    __name__ = 'payment_collect.configuration'
    payment_method = fields.MultiValue(fields.Many2One(
            'account.invoice.payment.method', "Payment Method", required=True))
    when_collect_payment = fields.MultiValue(
        fields.Selection(STATES, 'When collect payment'))
    create_invoices = fields.MultiValue(
        fields.Boolean('Add button to create invoices at return'))
    advance_account = fields.MultiValue(fields.Many2One(
            'account.account', "Advance Account",
            domain=[
                ('party_required', '=', True),
                ('company', '=', Eval('context', {}).get('company', -1)),
                ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'when_collect_payment':
            return pool.get('payment_collect.configuration.account')
        elif field == 'payment_method':
            return pool.get('payment_collect.configuration.account')
        elif field == 'create_invoices':
            return pool.get('payment_collect.configuration.account')
        elif field == 'advance_account':
            return pool.get('payment_collect.configuration.account')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_when_collect_payment(cls, **pattern):
        return cls.multivalue_model(
            'when_collect_payment').default_when_collect_payment()

    @classmethod
    def default_create_invoices(cls, **pattern):
        return cls.multivalue_model(
            'create_invoices').default_create_invoices()


class ConfigurationPaymentCollectAccount(ModelSQL, CompanyValueMixin):
    "PaymentCollect Configuration Accounting"
    __name__ = 'payment_collect.configuration.account'

    payment_method = fields.Many2One('account.invoice.payment.method',
        "Payment Method")
    when_collect_payment = fields.Char('when_collect_payment')
    create_invoices = fields.Boolean('Create invoice when process return')
    advance_account = fields.Many2One(
        'account.account', "Advance Account",
        domain=[
            ('party_required', '=', True),
            ('company', '=', Eval('company', -1)),
            ],
        depends=['company'])

    @classmethod
    def default_when_collect_payment(cls):
        return 'posted'

    @staticmethod
    def default_create_invoices():
        return False
