# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SendSMS(models.TransientModel):
    _inherit = 'sms.send_sms'

    message = fields.Text('Message', required=False)
    sand_mode = fields.Selection([
        ('text', 'Text'),
        ('template', 'Template')],
        string='Sand Mode', required=True, default='text')
    template_id = fields.Many2one('sms.template', string="SMS template") 
    template_preview = fields.Text(string='Template preview', readonly=True, compute='_get_template_preview')

    def action_send_sms(self):
        if self.template_id:
            numbers = self.recipients.split(',')
            active_model = self.env.context.get('active_model')
            model = self.env[active_model]
            records = self._get_records(model)
            # TODO 修复模版渲染逻辑，启用迭代记录的方式发送短信，避免与多个号码重叠发送
            # for record in records:
            sent, msg = self.env['sms.template'].send_sms_template(self.template_id, record, numbers)
            if not sent:
                raise ValidationError(_("Record ('%s') sms message delivery failed : %s") % (record.name, msg))
            return True
        return super(SendSMS, self).action_send_sms()

    @api.depends('template_id')
    def _get_template_preview(self):
        active_model = self.env.context.get('active_model')
        model = self.env[active_model]
        records = self._get_records(model)
        preview = ''
        signature = ''
        if self.template_id:
            if self.template_id.template_signature:
                signature = u'【' + self.template_id.template_signature + u'】'
            try:
                preview = self.template_id.render_template(self.template_id.content_body, active_model, records[0].id)[0]
            except Exception:
                raise ValidationError(_('Template Render error: The body contains an invalid expression !'))
            self.template_preview = signature + preview
            self.message = signature + preview

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.message = self.template_preview