# This file is part of the bank_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import paymode
from . import collect
from . import invoice
from . import party
from . import configuration

__all__ = ['register']


def register():
    Pool.register(
        party.Party,
        party.PartyPayMode,
        paymode.PayMode,
        collect.Collect,
        collect.CollectPeriod,
        collect.CollectSendStart,
        collect.CollectReturnStart,
        invoice.CollectTransaction,
        invoice.Invoice,
        configuration.Configuration,
        configuration.ConfigurationPaymentCollectAccount,
        module='payment_collect', type_='model')
    Pool.register(
        collect.CollectSend,
        collect.CollectReturn,
        module='payment_collect', type_='wizard')
