# -*- coding: utf-8 -*-
# https://github.com/odoocr
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Costa Rica Currency Adapter',
    'version': '10.0.0.0.1',
    'category': 'Account',
    'author': "Odoo CR.",
    'website': 'https://github.com/odoocr/res_currency_cr_adapter',
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': [
        'data/currency_data.xml',

        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
