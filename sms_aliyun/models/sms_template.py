# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

import json

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class SmsTemplate(models.Model):
    _inherit = "sms.template"

    def _convert_message(self, my_template, rendered_content):
        message = super(SmsTemplate, self)._convert_message(my_template, rendered_content)
        if my_template.account_id.sms_gateway == 'aliyun':
            key_list = []
            values_list = rendered_content[1]
            if len(values_list) > 0:
                if not my_template.variables_mapping:
                    raise ValidationError(_("Gateway 'Aliyun' must config the 'Variables mapping'."))
                key_list = my_template.variables_mapping.split(',') 
                if len(key_list) != len(values_list):
                    raise ValidationError(_("SMS template (%s): The number of variable mapping and the number of expression do not match !") % my_template.name)
        
            content_dict = dict(zip(key_list, values_list))
            content_str = json.dumps(content_dict, ensure_ascii=False).encode('utf-8')
            # message = "{"
            # for key, value in content_dict.iteritems():
            #     message += "\\\"" + key + "\\\"" + ":" + "\\\"" + value + "\\\"" + ","
            # message = message[:-1] + "}"

            # 替换字符串换行符为阿里支持的json换行符 2017-12-22 Dong
            message = content_str.replace('\n', '\r\n')
        return message
