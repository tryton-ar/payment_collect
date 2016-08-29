# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import logging
logger = logging.getLogger(__name__)
from trytond.pool import Pool
import datetime

class Payments:

    def attach_collect(self, monto_total, cantidad_registros, identificador_empresa, lines):
        logger.info("Monto total: " + str(monto_total))
        logger.info("Cantidad de registros: " + str(cantidad_registros))
        pool = Pool()
        Collect = pool.get('payment.collect')
        Attachment = pool.get('ir.attachment')
        collect = Collect()
        collect.monto_total = monto_total
        collect.cantidad_registros = cantidad_registros
        collect.start_date = self.start.start_date
        collect.end_date = self.start.end_date
        collect.collect_type = self.start.collect_type
        collect.type = 'send'
        collect.credit_paymode = self.start.credit_paymode
        collect.save()
        if collect.collect_type == 'debit_credicoop':
            filename = 'main' + identificador_empresa + '_' + datetime.date.today().strftime("%d%m")
        else:
            filename = collect.collect_type + '-' + identificador_empresa + '-' +  datetime.date.today().strftime("%Y-%m-%d")
        attach = Attachment()
        attach.name = filename + '.txt'
        attach.resource = collect
        attach.data = lines
        attach.save()
        self.message.message = u'Se ha generado el archivo con éxito.'


class banco_credicoop(Payments):

    def generate_collect(self):
        logger.info("generate_collect: banco_credicoop")
        pass
