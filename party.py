# -*- coding: utf-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import PoolMeta
from trytond.model import fields, ModelSQL, ModelView
from trytond.pyson import Eval

__all__ = ['Party']
__metaclass__ = PoolMeta


class Party(ModelSQL, ModelView):
    __name__ = 'party.party'

    customer_paymode = fields.Property(fields.Many2One(
        'payment.paymode',
        string='Customer pay mode', domain=[('party', '=', Eval('id'))],
        depends=['party']))

    supplier_paymode = fields.Property(fields.Many2One(
        'payment.paymode',
        string='Supplier pay mode', domain=[('party', '=', Eval('id'))],
        depends=['party']))
