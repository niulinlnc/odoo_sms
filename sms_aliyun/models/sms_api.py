# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

import urllib, urllib2
import hashlib
import hmac
import base64
import uuid
import datetime
import json

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    def check_and_setup(self, account, sms_template=None):
        if account.sms_gateway == 'aliyun':
            msg = ''
            if not (account.key_id and account.key_secret):
                raise ValidationError(_("Missing KeyId or KeySecret."))
            if not sms_template:
                msg = _('There is no SMS template for testing.') # 没有可供测试的短信模版 2017-12-22 Dong
            else:
                state, msg = sms_template.send_template_test()
            return msg
        return super(SmsApi, self).check_and_setup(account)

    @api.model
    def _send_sms_aliyun(self, account, numbers, message, sms_template):
        def _specia_encode(pstr):
            pstr = str(pstr)
            res = urllib.quote(pstr.encode('utf8'), '')
            res = res.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
            return res

        def _get_signature(to_sign, key_secret):
            h = hmac.new(key_secret.encode('utf8'), to_sign.encode('utf8'), hashlib.sha1)
            signature = base64.encodestring(h.digest()).strip()
            return signature

        def _get_response(account, payload=None):
            url = 'http://dysmsapi.aliyuncs.com'
            key_id = str(account.key_id)
            key_secret = str(account.key_secret)
            params = {
                'Format': 'JSON',
                'Version': '2017-05-25',
                'AccessKeyId': key_id,
                'SignatureMethod': 'HMAC-SHA1',
                'SignatureVersion': '1.0',
                'SignatureNonce': str(uuid.uuid4()),
                'Timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'RegionId': 'cn-hangzhou',
            }
            if payload:
                params.update(payload)
            # 1.根据参数Key排序
            sorted_params = sorted(list(params.items()), key=lambda params: params[0])
            # 2.特殊Url编码：(参数Key) + “=” + (参数值)
            query_string = ''
            for key, value in sorted_params:
                query_string += '&' + _specia_encode(key) + '=' + _specia_encode(value)
            # 3.待签名字符串：HTTPMethod + “&” + (“/”) + ”&” + (query_string)除去第一个'&'字符
            to_sign = 'GET&%2F&' + _specia_encode(query_string[1:])
            # 4.签名 
            signature = _get_signature(to_sign, key_secret + '&')
            # 5.签名做特殊编码
            signature_string = _specia_encode(signature)
            # 6.增加签名结果到请求参数中，发送请求。
            req = url + '/?Signature=' + signature_string + query_string
            response = urllib2.urlopen(req) # , timeout=3
            result = json.loads(response.read().decode('utf-8'))
            return result

        valid_numbers, invalid_numbers = self._check_numbers(numbers)
        # 如果没有通过验证的号码抛出错误 2017-12-22 Dong
        if not valid_numbers:
            raise ValidationError(_("The number provided is invalid, Please check your to numbers!"))
        payload = {
            'Action': 'SendSms',
            'SignName': sms_template.template_signature,
            'TemplateCode': sms_template.template_code,
            'PhoneNumbers': valid_numbers,
            'TemplateParam': message,
        }
        try:
            response = _get_response(account, payload)
        except (urllib2.HTTPError, urllib2.URLError) as e:
            return False, _('Gateway Connect Error : %s ,\n Please contact the administrator.') % e

        gateway_code = str(response.get('Code'))
        gateway_msg = str(response.get('Message')) or _('UNKNOW')
        if invalid_numbers:
            gateway_msg += _(' , Invalid Numbers: ( %s )') % invalid_numbers
        if gateway_code == 'OK':
            return True, _('Aliyun : %s') % gateway_msg
        else:
            return False, _('Aliyun : %s - %s') % (gateway_code, gateway_msg)

