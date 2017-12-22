# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class IapAccount(models.Model):
    _inherit = 'iap.account'

    sms_gateway = fields.Selection(selection_add=[('aliyun', 'Aliyun'),])