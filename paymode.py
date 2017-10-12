# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool
import stdnum.ar.cbu as cbu
import stdnum.exceptions

__all__ = ['PayMode']


class PayMode(ModelSQL, ModelView):
    'Paymode'
    __name__ = 'payment.paymode'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE',
        required=True, select=True)
    type = fields.Selection('get_origin', 'Type')

    ## DEBIT
    cbu_number = fields.Char('CBU number')
    ## CREDIT
    #credit_paymode = fields.Selection('get_credit_paymode', 'Type')
    credit_number = fields.Char('Number')
    credit_expiration_date = fields.Date('Expiration date')
    credit_bank = fields.Many2One('bank', 'Credit card bank')

    @classmethod
    def __setup__(cls):
        super(PayMode, cls).__setup__()
        cls._error_messages.update({
                'invalid_cbu': ('Invalid CBU number "%(cbu_number)s" '
                    'on party "%(party)s".'),
                })

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
            return name

    @fields.depends('type', 'cbu_number')
    def on_change_with_cbu_number(self):
        if self.type == 'payment.paymode.bccl':
            try:
                return cbu.compact(self.cbu_number)
            except stdnum.exceptions.ValidationError:
                pass
        return self.cbu_number

    def pre_validate(self):
        super(PayMode, self).pre_validate()
        self.check_cbu_number()

    @fields.depends('type', 'party', 'cbu_number')
    def check_cbu_number(self):
        if self.type == 'payment.paymode.bccl':
            if not cbu.is_valid(self.cbu_number):
                if self.party and self.party.id > 0:
                    party = self.party.rec_name
                else:
                    party = ''
                self.raise_user_error('invalid_cbu', {
                        'cbu_number': self.cbu_number,
                        'party': party,
                        })
