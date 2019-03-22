# The COPYRIGHT file at the top level of this repository contains the
# full copyright notices and license terms.
from trytond import backend
from trytond.model import ModelView, ModelSQL, ValueMixin, fields
from trytond.pool import Pool, PoolMeta
from trytond.tools.multivalue import migrate_property
from trytond.pyson import Eval

__all__ = ['Party', 'PartyPayMode']
customer_paymode = fields.Many2One('payment.paymode',
    string='Customer pay mode', domain=[
        ('party', '=', Eval('id')),
        ], depends=['id'])

supplier_paymode = fields.Many2One('payment.paymode',
    string='Supplier pay mode', domain=[
        ('party', '=', Eval('id'))
        ], depends=['id'])


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'
    customer_paymode = fields.MultiValue(customer_paymode)
    supplier_paymode = fields.MultiValue(supplier_paymode)

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'customer_paymode', 'supplier_paymode'}:
            return pool.get('party.party.paymode')
        return super(Party, cls).multivalue_model(field)


class PartyPayMode(ModelSQL, ValueMixin):
    "Party PayMode"
    __name__ = 'party.party.paymode'
    party = fields.Many2One(
        'party.party', "Party", ondelete='CASCADE', select=True)
    customer_paymode = customer_paymode
    supplier_paymode = supplier_paymode

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)

        super(PartyPayMode, cls).__register__(module_name)

        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.extend(['customer_paymode', 'supplier_paymode'])
        value_names.extend(['customer_paymode', 'supplier_paymode'])
        migrate_property(
            'party.party', field_names, cls, value_names,
            parent='party', fields=fields)
