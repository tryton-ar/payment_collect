#This file is part of the bank_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from . import paymode
from . import collect
from . import invoice
from . import party
from . import configuration


def register():
    Pool.register(
        party.Party,
        paymode.PayMode,
        collect.Collect,
        collect.CollectSendStart,
        collect.CollectReturnStart,
        collect.CollectTransaction,
        invoice.Invoice,
        configuration.Configuration,
        module='payment_collect', type_='model')
    Pool.register(
        collect.CollectSend,
        collect.CollectReturn,
        module='payment_collect', type_='wizard')
