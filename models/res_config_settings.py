# -*- coding: utf-8 -*-
# License OPL-1 nehemias@automatuanis.com
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
# from ast import literal_eval
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bccr_indicador_compra = fields.Char(string='Indicador Compra BCCR')
    bccr_indicador_venta = fields.Char(string='Indicador Venta BCCR')
    bccr_usuario = fields.Char(string='Usuario BCCR')
    bccr_token = fields.Char(string='Token BCCR')

    @api.model
    def get_default_values(self, fields):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # we use safe_eval on the result, since the value of the parameter is a nonempty string
        return {
            'bccr_indicador_compra': int(get_param('res_currency_cr_adapter.bccr_indicador_compra', '317')),
            'bccr_indicador_venta': int(get_param('res_currency_cr_adapter.bccr_indicador_venta', '318')),
            'bccr_usuario': int(get_param('res_currency_cr_adapter.bccr_usuario', '')),
            'bccr_token': int(get_param('res_currency_cr_adapter.bccr_token', '')),
        }

    @api.multi
    def set_default_values(self):
        self.ensure_one()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        # we store the repr of the values, since the value of the parameter is a required string
        set_param('res_currency_cr_adapter.bccr_indicador_compra', repr(self.bccr_indicador_compra))
        set_param('res_currency_cr_adapter.bccr_indicador_venta', repr(self.bccr_indicador_venta))
        set_param('res_currency_cr_adapter.bccr_usuario', repr(self.bccr_usuario))
        set_param('res_currency_cr_adapter.bccr_token', repr(self.bccr_token))
