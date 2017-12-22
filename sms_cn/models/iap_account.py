# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class IapAccount(models.Model):
    _inherit = 'iap.account'

    sms_gateway = fields.Selection(selection=[('iap', 'In-App purchases')], string='SMS Gateway')
    key_id = fields.Char(string='KeyId', help='AccessKeyId / AccountSID / AppKey / Account')
    key_secret = fields.Char(string='KeySecret',help='AccessKeySecret / AuthToken / AppSecret ／ APIKey')
    last_check_date = fields.Datetime(string='Last check date', readonly=True)
    last_check_response = fields.Char(string='Last check response', readonly=True)
    notes = fields.Text(string='Remarks')

    @api.model
    def get(self, service_name):
        if service_name == 'sms':
            return super(IapAccount, self).get(service_name)
        account = self.search([('service_name', '=', service_name), ('company_id', 'in', [self.env.user.company_id.id, False])], limit=1)
        if not account:
            raise UserError(_('service name (%s) not found , You need to create an IAP account with this service name.') % service_name)
        return account

    @api.multi
    def check_sms_connection(self):
        for account in self:
            test_template = self.env['sms.template'].search([('account_id', '=', account.id)], limit=1)
            msg = self.env['sms.api'].check_and_setup(account, test_template)
            account.write({'last_check_date':fields.Datetime.now(),'last_check_response': msg})