# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.modules.company.model import CompanyValueMixin


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    customer_paymode = fields.MultiValue(fields.Many2One('payment.paymode',
        'Customer pay mode', domain=[('party', '=', Eval('id'))],
        context={'party': Eval('id', None)}, depends=['id']))
    supplier_paymode = fields.MultiValue(fields.Many2One('payment.paymode',
        'Supplier pay mode', domain=[('party', '=', Eval('id'))],
        context={'party': Eval('id', None)}, depends=['id']))
    paymode_types = fields.One2Many('party.party.paymode', 'party',
        "Party Pay Mode")

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in ['customer_paymode', 'supplier_paymode']:
            return pool.get('party.party.paymode')
        return super().multivalue_model(field)


class PartyPayMode(CompanyValueMixin, ModelSQL):
    "Party Pay Mode"
    __name__ = 'party.party.paymode'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE')
    customer_paymode = fields.Many2One('payment.paymode', 'Customer pay mode')
    supplier_paymode = fields.Many2One('payment.paymode', 'Supplier pay mode')
