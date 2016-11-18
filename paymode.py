# This file is part of the account_voucher_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import PoolMeta, Pool

__all__ = ['PayMode']
__metaclass__ = PoolMeta

class PayMode(ModelSQL, ModelView):
    'Pay Mode'
    __name__ = 'payment.paymode'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE',
        required=True, select=True)
    type = fields.Selection('get_origin', 'Type')

    ## CREDIT
    #credit_paymode = fields.Many2One('payment.paymode.credit_card', 'Credit Card')
    #credit_number = fields.Char('Number')
    #credit_expiration_date = fields.Date('Expiration date')
    #credit_bank = fields.Many2One('bank', 'Credit card bank')

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['']

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [(None, '')] + [(m.model, m.name) for m in models]


    def get_rec_name(self, name):
        if self.type and self.party:
            return '['+self.type+'] '+self.party.name
        else:
            return self.name
