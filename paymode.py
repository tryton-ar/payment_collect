# This file is part of the payment_collect module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from stdnum.ar import cbu

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext


class PayMode(ModelSQL, ModelView):
    'Pay Mode'
    __name__ = 'payment.paymode'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE',
        required=True, select=True)
    type = fields.Selection('get_origin', 'Type')
    # DEBIT
    cbu_number = fields.Char('CBU number')
    bank_account = fields.Many2One('bank.account', 'Bank Account',
        context={
            'owners': Eval('party'),
            'numbers.type': 'cbu',
            },
        domain=[
            ('owners', '=', Eval('party')),
            ('numbers.type', '=', 'cbu'),
            ],
        depends=['party'])
    # CREDIT
    #credit_paymode = fields.Selection('get_credit_paymode', 'Type')
    credit_number = fields.Char('Number')
    credit_expiration_date = fields.Date('Expiration date')
    credit_bank = fields.Many2One('bank', 'Credit card bank')

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
        return name

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
            ('party.name',) + tuple(clause[1:]),
            ('party.code',) + tuple(clause[1:]),
            ]

    @fields.depends('bank_account', 'type')
    def pre_validate(self):
        super().pre_validate()
        if (self.type == 'payment.paymode.bccl' and self.bank_account and not
                cbu.is_valid(self.bank_account.rec_name)):
            raise UserError(gettext('payment_collect.msg_invalid_cbu',
                    self.bank_account.rec_name))
