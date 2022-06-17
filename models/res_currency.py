# -*- coding: utf-8 -*-
# https://github.com/odoocr
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import datetime
import logging
import requests
from lxml import etree

_logger = logging.getLogger(__name__)


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'
    
    @api.model
    def _cron_update(self, api_consulta='bccr', backfill=False, force_backfill=False):

        _logger.info("=========================================================")
        _logger.info("Executing exchange rate update")

        if api_consulta == 'hacienda':
            self._get_from_hacienda()
        elif api_consulta == 'bccr':
            self._get_from_bccr(backfill, force_backfill)

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

            vals = {}
            # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
            vals['rate'] =  1 / data['dolar']['venta']['valor']
            vals['currency_id'] = self.env.ref('base.USD').id

            rate_id = self.env['res.currency.rate'].search([('name', '=', today)], limit=1)

            if rate_id:
                rate_id.write(vals)
            else:
                vals['name'] = today
                self.create(vals)

            _logger.info(vals)
    
    def _get_from_bccr(self, backfill=False, force_backfill=False):
        url = 'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML'
        bccr_date_format         = '%d/%m/%Y'
        bccr_date_format_response = '%Y-%m-%d'

        get_param = self.env['ir.config_parameter'].sudo().get_param
        bccr_indicador_venta  = int(get_param('res_currency_cr_adapter.bccr_indicador_venta', '318'))
        bccr_usuario          = str(get_param('res_currency_cr_adapter.bccr_usuario', ''))
        bccr_token            = str(get_param('res_currency_cr_adapter.bccr_token', ''))
        
        date_from = date_to = datetime.datetime.now()
        if backfill: date_from = date_from.replace(month=1, day=1)

        try:
            if bccr_indicador_venta and bccr_usuario and bccr_token:
                params_venta = {
                    'Indicador': bccr_indicador_venta,
                    'FechaInicio': date_from.strftime(bccr_date_format),
                    'FechaFinal': date_to.strftime(bccr_date_format),
                    'Nombre': 'Automatuanis',
                    'SubNiveles': 'No',
                    'CorreoElectronico': bccr_usuario,
                    'Token': bccr_token
                }

                response_venta  = requests.get(url, params=params_venta, timeout=5)

        except requests.exceptions.RequestException as e:
            _logger.info('RequestException %s' % e)
            return False

        if response_venta.status_code in (200,):
            root = etree.fromstring(response_venta.content)
            datos = etree.fromstring(root.text)
            datos = datos.xpath("INGC011_CAT_INDICADORECONOMIC")

        for dato in datos:
            fecha = datetime.datetime.strptime(dato.xpath("DES_FECHA")[0].text[:10], bccr_date_format_response)
            venta = dato.xpath("NUM_VALOR")[0].text

            self.update_exchange_rate(self.env.ref('base.USD'), fecha, venta, force_backfill)


    def update_exchange_rate(self, currency_id, rate_date, venta, update=False):
        vals = {}
        vals['original_rate'] = float(venta)
        # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
        vals['rate'] =  1 / vals['original_rate']
        vals['currency_id'] = currency_id.id

        date_string = rate_date.strftime(rate_date.strftime('%Y-%m-%d 06:00:00'))

        for company_id in self.sudo().env['res.company'].search([]):
                
            rate_id = self.sudo().env['res.currency.rate'].search([('company_id', '=', company_id.id),('name', '=', date_string), ('currency_id', '=', currency_id.id)], limit=1)
            if rate_id:
                if update:
                    _logger.info('Updating %s with %s' % (rate_id, vals))
                    rate_id.write(vals)
                else:
                    _logger.info('Not updating %s' % rate_id)
            else:
                vals['name'] = date_string
                vals['company_id'] = company_id.id
                _logger.info('New record with %s' % vals)
                self.create(vals)               
                _logger.info('New record with %s' % vals)