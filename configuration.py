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
    collect_use_cron = fields.MultiValue(
        fields.Boolean('Use Cron to pay invoices'))
    create_invoices = fields.MultiValue(
        fields.Boolean('Add button to create invoices at return'))
    pos = fields.MultiValue(fields.Many2One('account.pos', "Point of Sale",
            domain=[('pos_daily_report', '=', False)]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'when_collect_payment':
            return pool.get('payment_collect.configuration.account')
        elif field == 'payment_method':
            return pool.get('payment_collect.configuration.account')
        elif field == 'collect_use_cron':
            return pool.get('payment_collect.configuration.account')
        elif field == 'create_invoices':
            return pool.get('payment_collect.configuration.account')
        elif field == 'pos':
            return pool.get('payment_collect.configuration.account')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_when_collect_payment(cls, **pattern):
        return cls.multivalue_model(
            'when_collect_payment').default_when_collect_payment()

    @classmethod
    def default_collect_use_cron(cls, **pattern):
        return cls.multivalue_model(
            'collect_use_cron').default_collect_use_cron()

    @classmethod
    def default_create_invoices(cls, **pattern):
        return cls.multivalue_model(
            'create_invoices').default_create_invoices()

    @classmethod
    def default_pos(cls, **pattern):
        return cls.multivalue_model(
            'pos').default_pos()


class ConfigurationPaymentCollectAccount(ModelSQL, CompanyValueMixin):
    "PaymentCollect Configuration Accounting"
    __name__ = 'payment_collect.configuration.account'

    payment_method = fields.Many2One('account.invoice.payment.method',
        "Payment Method")
    when_collect_payment = fields.Char('when_collect_payment')
    collect_use_cron = fields.Boolean('collect_use_cron')
    create_invoices = fields.Boolean('Create invoice when process return')
    pos = fields.Many2One('account.pos', "Point of Sale", required=True,
        domain=[('pos_daily_report', '=', False)])

    @classmethod
    def default_when_collect_payment(cls):
        return 'posted'

    @classmethod
    def default_collect_use_cron(cls):
        return False

    @staticmethod
    def default_create_invoices():
        return False

    @staticmethod
    def default_pos():
        return None
