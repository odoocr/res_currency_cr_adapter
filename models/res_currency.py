# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
import datetime
import logging
import requests

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    rate = fields.Float(digits=dp.get_precision('Currency Rate Precision'))


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'
    
    # Change decimal presicion to work with CRC where 1 USD is more de 555 CRC
    rate = fields.Float(string='Selling Rate', digits=dp.get_precision('Currency Rate Precision'))

    # Costa Rica uses two exchange rates: 
    #   - Buying exchange rate - used when a financial institutions buy USD from you (rate)
    #   - Selling exchange rate - used when financial institutions sell USD to you (rate_2)
    rate_2 = fields.Float(string='Buying Rate', digits=dp.get_precision('Currency Rate Precision'), help='The buying rate of the currency to the currency of rate 1.')

    # Rate as it is get 
    original_rate = fields.Float(string='Selling Rate in Costa Rica', digits=(6, 2), help='The selling exchange rate from CRC to USD as it is send from BCCR')
    # Rate as it is get 
    original_rate_2 = fields.Float(string='Buying Rate in Costa Rica', digits=(6, 2), help='The buying exchange rate from CRC to USD as it is send from BCCR')


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
            _logger.info(data)

            vals = {}
            vals['original_rate'] = data['dolar']['venta']['valor']
            # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
            vals['rate'] =  1 / vals['original_rate']
            vals['original_rate_2'] = data['dolar']['compra']['valor']
            vals['rate_2'] = 1 / vals['original_rate_2']
            vals['currency_id'] = self.env.ref('base.USD').id
            vals_usd = vals

            vals = {}
            vals['original_rate'] = data['euro']['colones']
            vals['rate'] =  1 / vals['original_rate']
            vals['original_rate_2'] = data['euro']['colones']
            vals['rate_2'] = 1 / vals['original_rate_2']
            vals['currency_id'] = self.env.ref('base.EUR').id
            vals_eur = vals

            rates = [vals_usd, vals_eur]

            # Revisamos cada compañia
            for company_id in self.sudo().env['res.company'].search([]):
                # y ejecutamos con cada moneda
                for vals in rates:
                    rate_id = self.sudo().env['res.currency.rate'].search([('company_id', '=', company_id.id),('name', '=', today), ('currency_id', '=', vals['currency_id'])], limit=1)
                    if rate_id:
                        rate_id.write(vals)
                    else:
                        vals['name'] = today
                        vals['company_id'] = company_id.id
                        self.create(vals)               
                    _logger.info(vals)
        _logger.info("=========================================================")
