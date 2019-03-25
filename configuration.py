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
    journal = fields.MultiValue(fields.Many2One(
            'account.journal', "Journal", required=True,
            domain=[
                ('type', '=', 'cash'),
                ]))
    when_collect_payment = fields.MultiValue(
        fields.Selection(STATES, 'When collect payment'))
    collect_use_cron = fields.MultiValue(
        fields.Boolean('Use Cron to pay invoices'))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'when_collect_payment':
            return pool.get('payment_collect.configuration.account')
        elif field == 'journal':
            return pool.get('payment_collect.configuration.account')
        elif field == 'collect_use_cron':
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


class ConfigurationPaymentCollectAccount(ModelSQL, CompanyValueMixin):
    "PaymentCollect Configuration Accounting"
    __name__ = 'payment_collect.configuration.account'

    journal = fields.Many2One(
        'account.journal', "Journal",
        domain=[
            ('type', '=', 'cash'),
            ])
    when_collect_payment = fields.Char('when_collect_payment')
    collect_use_cron = fields.Boolean('collect_use_cron')

    @classmethod
    def default_when_collect_payment(cls):
        return 'posted'

    @classmethod
    def default_collect_use_cron(cls):
        return False
