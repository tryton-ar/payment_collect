#This file is part of the bank_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from .paymode import *
from .collect import *
from .invoice import *
from .party import *
from .configuration import *


def register():
    Pool.register(
        Party,
        PayMode,
        Collect,
        CollectSendStart,
        CollectReturnStart,
        CollectTransaction,
        Invoice,
        Configuration,
        module='payment_collect', type_='model')
    Pool.register(
        CollectSend,
        CollectReturn,
        module='payment_collect', type_='wizard')
