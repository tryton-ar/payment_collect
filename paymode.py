# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from stdnum.ar import cbu

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool
from trytond.pyson import Eval

__all__ = ['PayMode']


class PayMode(ModelSQL, ModelView):
    'Paymode'
    __name__ = 'payment.paymode'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE',
        required=True, select=True)
    type = fields.Selection('get_origin', 'Type')

    ## DEBIT
    cbu_number = fields.Char('CBU number')
    bank_account = fields.Many2One('bank.account',
        'Bank Account', context={
            'owners': Eval('party'),
            'numbers.type': 'cbu',
            }, domain=[
            ('owners', '=', Eval('party')),
            ('numbers.type', '=', 'cbu'),
            ])
    ## CREDIT
    #credit_paymode = fields.Selection('get_credit_paymode', 'Type')
    credit_number = fields.Char('Number')
    credit_expiration_date = fields.Date('Expiration date')
    credit_bank = fields.Many2One('bank', 'Credit card bank')

    @classmethod
    def __setup__(cls):
        super(PayMode, cls).__setup__()
        cls._error_messages.update({
                'invalid_cbu': 'Invalid CBU "%s".',
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
            return '[%s] %s' % (Pool().get(self.type).__doc__,
                self.party.rec_name)
        else:
            return name

    @fields.depends('bank_account', 'type')
    def pre_validate(self):
        super(PayMode, self).pre_validate()
        if (self.type == 'payment.paymode.bccl' and self.bank_account
                and not cbu.is_valid(self.bank_account.rec_name)):
            self.raise_user_error('invalid_cbu', self.bank_account.rec_name)
