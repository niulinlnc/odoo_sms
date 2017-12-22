# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

import re

from odoo import api, models, fields, _
from odoo.addons.iap.models import iap
from odoo.exceptions import ValidationError


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    @api.model
    def _send_sms(self, numbers, message, sms_template=None):
        t_account = sms_template.account_id if sms_template else False
        # 应用内购买账户 2017-12-22 Dong
        # i_account = self.env['iap.account'].get('Freshoo SMS')
        # if i_account and (i_account == t_account):
        #     params = {
        #         'account_token': i_account.account_token,
        #         'numbers': numbers,
        #         'message': message,
        #         'key_id': i_account.key_id,
        #         'key_secret': i_account.key_secret,
        #         'template_signature': sms_template.template_signature,
        #         'template_code': sms_template.template_code,
        #     }
        #     endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', 'https://iap.freshoo.cn')
        #     r = iap.jsonrpc(endpoint + '/iap/sms/send', params=params)
        #     return r
        # elif t_account and (not t_account.sms_gateway == 'iap'):
        if t_account and (not t_account.sms_gateway == 'iap'):
            # 非应用内购买的账户调用网关api的方法 2017-12-22 Dong
            return getattr(self, '_send_sms_%s' % t_account.sms_gateway)(t_account, numbers, message, sms_template)
        return super(SmsApi, self)._send_sms(numbers, message)

    def check_and_setup(self, account, sms_template=None):
        msg = ''
        if account.sms_gateway and account.sms_gateway == 'iap':
            try:
                self.env['sms.api']._send_sms('13800138000', '{test:Test}', sms_template)
                msg = 'Successful'
            except Exception, e:
                msg = e
        return msg

    def _check_numbers(self, numbers):
        """ 正则校验手机号
        :param numbers: 待检查的电话号码(列表)
        :returns valid_numbers: 匹配的电话号码(逗号分隔的字符串)
        :returns invalid_numbers: 无效的电话号码(逗号分隔的字符串)
        """
        valid_list = []
        invalid_list = []
        regex_cn = re.compile('^13\d{9}|14[57]\d{8}|15[012356789]\d{8}|17\d{9}|18[01256789]\d{8}$')
        # regex_cn = re.compile('^(13[0-9]|14[57]|15[012356789]|18[0-9]|17[0-9])\d{8}$')
        for number in numbers:
            if regex_cn.match(number) and len(number) == 11:
                valid_list.append(number)
            else:
                invalid_list.append(number)
        valid_numbers = ','.join(valid_list)
        invalid_numbers = ','.join(invalid_list)
        return valid_numbers, invalid_numbers
