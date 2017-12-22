# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

from datetime import datetime
from odoo import api, models, fields, _


class SmsMessage(models.Model):
    _name = 'sms.message'
    _order = 'id desc'
    _rec_name = 'record_name'

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    subject = fields.Char('Subject')
    body = fields.Html('Contents', default='', sanitize_style=True, strip_classes=True)
    date = fields.Datetime('Date', default=fields.Datetime.now)
    # message_type = fields.Selection(selection_add=[('sms', 'SMS')])
    model = fields.Char('Related Document Model', index=True)
    res_id = fields.Integer('Related Document ID', index=True)
    record_name = fields.Char('Message Record Name', help="Name get of the related document.")
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True,
        ondelete='set null', default=_get_default_author,
        help="Author of the message.")
    message_id = fields.Char('Message-Id', help='Message unique identifier', index=True, readonly=1, copy=False)
    # mail_message_id = fields.Many2one('mail.message', 'Message', required=True, ondelete='cascade', index=True, auto_join=True)
    sms_state = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, default='outgoing')
    # failure_reason = fields.Text(
    #     'Failure Reason', readonly=1,
    #     help="Failure reason. This is usually the exception thrown by the gateway server.")
    scheduled_date = fields.Char('Scheduled Send Date',
        help="If set, the queue manager will send the sms after the date. If not set, the sms will be send as soon as possible.")
    
    sms_template_id = fields.Many2one('sms.template', string="SMS Template", readonly=True)
    sms_account_id = fields.Many2one('iap.account', readonly=True, string="SMS Account")
    sms_state_msg = fields.Char(string='Status Massage', readonly=True)
    numbers = fields.Char(string='To (Number)')
    validity = fields.Integer(string='Validity (Mins)', readonly=True)
    verify_code = fields.Integer('Verify Code', readonly=True, index=True)
    code_used = fields.Boolean(string='Code Used')
    
    @api.model
    def _get_record_name(self, values):
        """ Return the related document name, using name_get. It is done using
            SUPERUSER_ID, to be sure to have the record name correctly stored. """
        model = values.get('model', self.env.context.get('default_model'))
        res_id = values.get('res_id', self.env.context.get('default_res_id'))
        if not model or not res_id or model not in self.env:
            return False
        return self.env[model].sudo().browse(res_id).name_get()[0][1]

    @api.model
    def create(self, values):
        if 'record_name' not in values and 'default_record_name' not in self.env.context:
            values['record_name'] = self._get_record_name(values)
        message = super(SmsMessage, self).create(values)
        return message

    @api.multi
    def check_code_validity(self, cur_time):
        """ 查询验证码有效状态，有效返回 True, 过期返回 False / 2017-12-22 Dong """
        self.ensure_one()
        validity_sec = self.validity * 60
        send_time = datetime.strptime(self.date, '%Y-%m-%d %H:%M:%S')
        delta_sec = (cur_time - send_time).seconds
        if (not self.code_used) and (delta_sec < validity_sec):
            return True
        else:
            return False

    @api.multi
    def mark_code_used(self):
        self.ensure_one()
        return self.write({'code_used': True})