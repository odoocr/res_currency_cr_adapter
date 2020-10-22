# -*- coding: utf-8 -*-
# https://github.com/odoocr
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import datetime
import logging
import requests

_logger = logging.getLogger(__name__)


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'
    
    @api.model
    def _cron_update(self):

        _logger.info("=========================================================")
        _logger.info("Executing exchange rate update")

        try:
            url = 'https://api.hacienda.go.cr/indicadores/tc'
            response = requests.get(url, timeout=5, verify=False)

        except requests.exceptions.RequestException as e:
            _logger.info('RequestException %s' % e)
            return False

        if response.status_code in (200,):
            # Save the exchange rate in database
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            data = response.json()

            vals = {}
            # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
            vals['rate'] =  1 / data['dolar']['venta']['valor']

            rate_id = self.env['res.currency.rate'].search([('name', '=', today)], limit=1)

            if rate_id:
                rate_id.write(vals)
            else:
                vals['name'] = today
                self.create(vals)

        _logger.info(vals)
        _logger.info("=========================================================")

