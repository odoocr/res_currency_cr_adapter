# -*- coding: utf-8 -*-
# License OPL-1 nehemias@automatuanis.com
from odoo import models, fields, api
from ast import literal_eval
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bccr_indicador_compra = fields.Char(string='Indicador Compra BCCR')
    bccr_indicador_venta = fields.Char(string='Indicador Venta BCCR')
    bccr_usuario = fields.Char(string='Usuario BCCR')
    bccr_token = fields.Char(string='Token BCCR')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        bccr_indicador_compra = get_param('account.bccr_indicador_compra', '317')
        bccr_indicador_venta  = get_param('account.bccr_indicador_venta', '318')
        bccr_usuario          = get_param('account.bccr_usuario', '')
        bccr_token            = get_param('account.bccr_token', '')

        res.update(
            bccr_indicador_compra=bccr_indicador_compra,
            bccr_indicador_venta=bccr_indicador_venta,
            bccr_usuario=bccr_usuario,
            bccr_token=bccr_token
        )

        return res

    @api.multi
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param

        set_param('account.bccr_indicador_compra', self.bccr_indicador_compra)
        set_param('account.bccr_indicador_venta', self.bccr_indicador_venta)
        set_param('account.bccr_usuario', self.bccr_usuario)
        set_param('account.bccr_token', self.bccr_token)

        return res