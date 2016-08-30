# This file is part of the account_voucher_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields, ModelSQL, ModelView
from trytond.pyson import Eval, In
from trytond.pool import PoolMeta
import payments

__all__ = ['PayMode']
__metaclass__ = PoolMeta

_STATES = {
    'readonly': In(Eval('state'), ['posted']),
}


class PayMode(ModelSQL, ModelView):
    'Pay Mode'
    __name__ = 'payment.paymode'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE',
        required=True, select=True)
    type = fields.Selection('get_types', 'Type')

    # DEBIT
    #debit_paymode = fields.Selection([
    #        ('', ''),
    #        ('cbu', 'CBU'),
    #        ('0', 'C.C. $'),
    #        ('1', 'C.A. $'),
    #        ('2', 'C.A. USD'),
    #        ('5', 'C.C. USD'),
    #    ], 'Debit')
    #debit_number = fields.Char('Account number')
    #debit_filial_number = fields.Char('Filial number')
    #debit_bank = fields.Many2One('bank', 'Debit account bank')
    #cbu_number = fields.Char('CBU number')

    ## CREDIT
    #credit_paymode = fields.Many2One('payment.paymode.credit_card', 'Credit Card')
    #credit_number = fields.Char('Number')
    #credit_expiration_date = fields.Date('Expiration date')
    #credit_bank = fields.Many2One('bank', 'Credit card bank')

    #party = fields.Many2One('party.party', 'Party')

    def get_rec_name(self, name):
        if self.type and self.party:
            return '['+self.type+'] '+self.party.name
        else:
            return self.name

    @classmethod
    def get_types(cls):
        return [
            (None, ''),
            ]

    def generate_collect(self):
        klass = getattr(payments, self.type)
        collect_type = klass()
        return collect_type.generate_collect()
