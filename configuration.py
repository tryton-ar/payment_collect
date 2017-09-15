# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.modules.account_invoice.invoice import STATES

__all__ = ['Configuration']
__metaclass__ = PoolMeta


class Configuration:
    __name__ = 'account.configuration'
    default_payment_collect_journal = fields.Property(
        fields.Many2One('account.journal', 'Default Payment Journal'))
    when_collect_payment = fields.Property(
        fields.Selection(STATES, 'When collect payment'))
