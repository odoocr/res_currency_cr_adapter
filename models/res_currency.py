# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
import datetime
import logging
import requests
from lxml import etree

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
    def _cron_update(self, api_consulta='hacienda'):

        _logger.info("=========================================================")
        _logger.info("Executing exchange rate update")

        if api_consulta == 'hacienda':
            self._get_from_hacienda()
        elif api_consulta == 'bccr':
            self._get_from_bccr()

        _logger.info("=========================================================")

    def _get_from_hacienda(self):
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
            rates = []

            vals = {}
            vals['original_rate'] = data['dolar']['venta']['valor']
            # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
            vals['rate'] =  1 / vals['original_rate']
            vals['original_rate_2'] = data['dolar']['compra']['valor']
            vals['rate_2'] = 1 / vals['original_rate_2']
            vals['currency_id'] = self.env.ref('base.USD').id
            rates.append(vals)

            if 'euro' in data:
                vals = {}
                # sometimes hacienda's API returns the euro price in colones, other times it returns it in dollars
                # they are not beign consistent, we'll try to keep up with such inconsistency
                if 'colones' in data['euro']:
                    vals['original_rate'] = data['euro']['colones']
                elif 'valor' in data['euro']:
                    vals['original_rate'] = float(data['euro']['valor']) * float(data['dolar']['venta']['valor'])

                vals['rate'] =  1 / vals['original_rate']
                vals['original_rate_2'] = vals['original_rate']
                vals['rate_2'] = 1 / vals['original_rate_2']
                vals['currency_id'] = self.env.ref('base.EUR').id
                rates.append(vals)

            # Update rates for every company
            for company_id in self.sudo().env['res.company'].search([]):
                # and every currency
                for vals in rates:
                    rate_id = self.sudo().env['res.currency.rate'].search([('company_id', '=', company_id.id),('name', '=', today), ('currency_id', '=', vals['currency_id'])], limit=1)
                    if rate_id:
                        rate_id.write(vals)
                    else:
                        vals['name'] = today
                        vals['company_id'] = company_id.id
                        self.create(vals)               
                    _logger.info(vals)

    def _get_from_bccr(self, query_date=None):
        url = 'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML'
        
        get_param = self.env['ir.config_parameter'].sudo().get_param
        
        bccr_date_format      = '%d/%m/%Y' 
        if not query_date:
            query_date = datetime.datetime.now()

        bccr_indicador_compra = get_param('account.bccr_indicador_compra', '317')
        bccr_indicador_venta  = get_param('account.bccr_indicador_venta', '318')
        bccr_usuario          = get_param('account.bccr_usuario', '')
        bccr_token            = get_param('account.bccr_token', '')

        try:
            if bccr_indicador_compra and bccr_indicador_venta and bccr_usuario and bccr_token:
                params_compra = {
                    'Indicador': bccr_indicador_compra,
                    'FechaInicio': query_date.strftime(bccr_date_format),
                    'FechaFinal': query_date.strftime(bccr_date_format),
                    'Nombre': 'Automatuanis',
                    'SubNiveles': 'No',
                    'CorreoElectronico': bccr_usuario,
                    'Token': bccr_token
                }
                params_venta = params_compra.copy()
                params_venta['Indicador'] = bccr_indicador_venta

                response_compra = requests.get(url, params=params_compra, timeout=5)
                response_venta  = requests.get(url, params=params_venta, timeout=5)

        except requests.exceptions.RequestException as e:
            _logger.info('RequestException %s' % e)
            return False

        compra = venta = 0.0

        if response_compra.status_code in (200,):
            root = etree.fromstring(response_compra.content)
            datos = etree.fromstring(root.text)
            compra = float(datos.xpath("INGC011_CAT_INDICADORECONOMIC/NUM_VALOR")[0].text)
            _logger.info("compra %s" % compra)

        if response_venta.status_code in (200,):
            root = etree.fromstring(response_venta.content)
            datos = etree.fromstring(root.text)
            venta = float(datos.xpath("INGC011_CAT_INDICADORECONOMIC/NUM_VALOR")[0].text)
            _logger.info("venta %s" % venta)

        if compra and venta:
            self.update_exchange_rate(self.env.ref('base.USD'), query_date, compra, venta)
        

    def update_exchange_rate(self, currency_id, rate_date, compra, venta):
        vals = {}
        vals['original_rate'] = venta
        # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
        vals['rate'] =  1 / vals['original_rate']
        vals['original_rate_2'] = compra
        vals['rate_2'] = 1 / vals['original_rate_2']
        vals['currency_id'] = currency_id.id

        date_string = rate_date.strftime('%Y-%m-%d')

        for company_id in self.sudo().env['res.company'].search([]):
                
            rate_id = self.sudo().env['res.currency.rate'].search([('company_id', '=', company_id.id),('name', '=', date_string), ('currency_id', '=', currency_id.id)], limit=1)
            if rate_id:
                rate_id.write(vals)
            else:
                vals['name'] = date_string
                vals['company_id'] = company_id.id
                self.create(vals)               
            _logger.info(vals)