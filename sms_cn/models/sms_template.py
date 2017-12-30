# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)

import random
import re
import datetime
import dateutil.relativedelta as relativedelta
import logging

import functools
from werkzeug import urls

from odoo import _, api, fields, models, tools
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': urls.url_quote,
        'urlencode': urls.url_encode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': functools.reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class SmsTemplate(models.Model):
    _name = "sms.template"
    _description = 'Sms Templates'
    _order = 'name'

    @api.model
    def default_get(self, fields):
        res = super(SmsTemplate, self).default_get(fields)
        if res.get('model'):
            res['model_id'] = self.env['ir.model']._get(res.pop('model')).id
        return res

    name = fields.Char('Template name')
    model_id = fields.Many2one('ir.model', 'Applies to', help="The type of document this template can be used with")
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    lang = fields.Char('Language',
                       help="Optional translation language (ISO code) to select when sending out a sms. "
                            "If not set, the english version will be used. "
                            "This should usually be a placeholder expression "
                            "that provides the appropriate language, e.g. "
                            "${object.partner_id.lang}.",
                       placeholder="${object.partner_id.lang}")
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                             "of the related document model")
    # 10.0 增加 ir.values
    ref_ir_value = fields.Many2one('ir.values', 'Sidebar Button', readonly=True, copy=False,
                                   help="Sidebar button to open the sidebar action")
    # Fake fields used to implement the placeholder assistant
    model_object_field = fields.Many2one('ir.model.fields', string="Field",
                                         help="Select target field from the related document model.\n"
                                              "If it is a relationship field you will be able to select "
                                              "a target field at the destination of the relationship.")
    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True,
                                 help="When a relationship field is selected as first field, "
                                      "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', 'Sub-field',
                                             help="When a relationship field is selected as first field, "
                                                  "this field lets you select the target field within the "
                                                  "destination document model (sub-model).")
    null_value = fields.Char('Default Value', help="Optional value to use if the target field is empty")
    copyvalue = fields.Char('Placeholder Expression', help="Final placeholder expression, to be copy-pasted in the desired template field.")
    content_body = fields.Text('Content body', translate=True, help="Plain text version of the message (placeholders may be used here)")
    content_preview = fields.Text(string='Content preview', readonly=True, compute='_get_preview') # 内容预览
    account_id = fields.Many2one('iap.account', string="SMS account", domain="[('sms_gateway', '!=', False)]") # 短信账户
    variables_only = fields.Boolean(string='Variables only') # 仅发送变量到网关，技术字段
    variables_mapping = fields.Char(string='Variables mapping', help="Variables in template by service providers, Comma-separated multiple variables") # 变量映射
    template_type = fields.Selection([
        ('notice','Notice'), # 通知短信
        ('code', 'Verify code'), # 验证码
        ('marketing', 'Marketing'), # 营销短信
    ],string='Template type', default='notice') # 模版类型
    template_signature = fields.Char(string='SMS signature') # 短信签名
    template_code = fields.Char(string='SMS code') # 服务商模版id
    numbers = fields.Char(string='To (Number)', help="Comma-separated recipient mobile (placeholders may be used here)") # 接收号码
    active = fields.Boolean(string='Active', default=True, help="If unchecked, it will allow you to hide the product without removing it.") # 是否激活
    pass_test = fields.Boolean(string='Pass-test', default=False) # 是否调试成功？技术字段 domain 的判断条件
    priority = fields.Integer(string='Priority', required=True, default=10) # 优先级
    verify_digits = fields.Integer(string='Verify digits', default=4) # 验证码位数
    validity = fields.Integer(string='Validity (Mins)', default=15) # 验证码有效期

    _sql_constraints = [
        ('priority_uniq', 'unique (model_id, template_type, priority)', _("Priority repeat !")),
        ('priority_check', 'CHECK (priority>0)', _("Priority must be greater than 0 !")),
    ]

    @api.onchange('model_id')
    def onchange_model_id(self):
        # TDE CLEANME: should'nt it be a stored related ?
        if self.model_id:
            self.model = self.model_id.model
        else:
            self.model = False

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def onchange_sub_model_object_value_field(self):
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                # model = self.env['ir.model']._get(self.model_object_field.relation)
                model = self.env['ir.model'].search([('model', '=', self.model_object_field.relation)])
                if model:
                    self.sub_object = model.id
                    self.copyvalue = self.build_expression(self.model_object_field.name, self.sub_model_object_field and self.sub_model_object_field.name or False, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self.build_expression(self.model_object_field.name, False, self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False

    # @api.onchange('variables_mapping')
    # def onchange_variables_mapping(self):
    #     if self.content_body and self.variables_mapping and self.variables_only:
    #         m_list = self.variables_mapping.split(',')
    #         e_list = self.get_expression_list(self.content_body)
    #         if len(m_list) != len(e_list):
    #             raise ValidationError(_('The number of variable mapping and the number of expression do not match.'))

    # 显示模版实际发送效果预览
    @api.depends('template_signature', 'content_body', 'model_id')
    def _get_preview(self):
        signature = ''
        preview = ''
        error_msg = ''
        if self.template_signature:
            signature = u'【' + self.template_signature + u'】'
        if self.content_body:
            preview = self.content_body
            expression = self.get_expression_list(self.content_body)
            # 如果已指定了模型并且内容含有表达式，预览渲染后的内容
            if self.model_id and expression:
                record = self.env[self.model_id.model].search([])
                if record:
                    try:
                        preview = self.render_template(self.content_body, self.model_id.model, record[0].id)[0]
                    except Exception:
                        error_msg = _('Render error: The body contains an invalid expression !')
                else:
                    error_msg = _('Render error: Model no record for render !')
        # 内容预览显示错误提示+签名
        self.content_preview = error_msg + signature + preview

    @api.multi
    def send_template_test(self):
        for template in self:
            records = self.env[template.model_id.model].search([])
            if not records:
                raise ValidationError(_("The Related Document Model cannot found records. Create a record and try again."))
            state, msg = template.send_sms_template(self, records[0])
            if state:
                self.write({'pass_test': True})
            else:
                self.write({'pass_test': False})
                raise ValidationError(msg)
        return state, msg

    @api.model
    def send_sms_template(self, my_template, records, numbers=None):
        # 如果没有传numbers值，取模版的numbers 2017-12-22 Dong
        if numbers:
            my_numbers = numbers
        else:
            rendered_numbers = my_template.render_template(my_template.numbers, my_template.model_id.model, record.id)[0]
            my_numbers = rendered_numbers.split(',')
        # 渲染模版值并转换成符合网关要求的内容
        rendered_content = my_template.render_template(my_template.content_body, my_template.model_id.model, record.id)
        my_message = self._convert_message(my_template, rendered_content)
        # 每条记录创建短信的业务日志
        vals = {
            'sms_state': 'outgoing',
            'res_id': record.id,
            'model': my_template.model_id.model,
            'subject': my_template.name,
            'date': datetime.datetime.now(),
            'author_id': self.env.uid,
            'sms_template_id': my_template.id,
            'sms_account_id': my_template.account_id.id,
            'numbers': ','.join(my_numbers),
            'body': rendered_content[0],
            'verify_code': rendered_content[2].get('${code}') if my_template.template_type == 'code' else False,
            'validity': my_template.validity if my_template.template_type == 'code' else False,
        }
        sms_message = self.env['sms.message'].sudo().create(vals)
        try:
            state, msg = self.env['sms.api']._send_sms(my_numbers, my_message, my_template)
        except ValidationError as e:
            state, msg = False, str(e.args[0])
        # 更新发送结果
        update_vals = {
            'sms_state': 'sent' if state else 'exception',
            'sms_state_msg': msg,
        }
        sms_message.write(update_vals)
        return state, msg

    def _convert_message(self, my_template, rendered_content):
        # 默认返回完整字符串 2017-12-22 Dong
        message = rendered_content[0]
        if message == "":
            raise ValidationError(_('Message content can not be empty'))
        return message

    def render_template(self, template_txt, model, res_id):
        # 文本包含的表达式(列表)
        expression_list = self.get_expression_list(template_txt)
        # 加载待渲染全文
        template = mako_template_env.from_string(tools.ustr(template_txt))
        # 加载待渲染表达式列表
        expression = mako_template_env.from_string(tools.ustr(expression_list))
        # 准备模板变量
        variables = {
            'user': self.env.user,
            'object': self.env[model].browse(res_id),
            'code': self._create_code(),
            'validity': self.validity,
        }
        try:
            template_result = template.render(variables)
            expression_result = expression.render(variables)
        except Exception:
            template_result = _("Failed to render template %r using values %r" % (template, variables))
            expression_result = u""
        if template_result == u"False":
            template_result = u""
        # 渲染输出的字符串转还原成列表并组装字典 2017-12-22 Dong
        expression_result = safe_eval(expression_result)
        expression_dict = dict(zip(expression_list, expression_result))
        # 返回 全文(字符串)、变量渲染结果(列表)、表达式与渲染结果(字典)
        return template_result, expression_result, expression_dict

    @api.depends('verify_digits')
    def _create_code(self):
        # 根据位数随机生成验证码 2017-12-22 Dong
        code = ''
        for i in range(self.verify_digits):
            no = random.randint(1, 9) if i < 1 else random.randint(0, 9)
            code += code.join(str(no))
        return code

    def get_expression_list(self, template_txt):
        if isinstance(template_txt, bool):
            # 文本False返回空列表 2017-12-22 Dong
            return []
        return re.findall(r'\${[a-z0-9._A-Z0-9]*}', template_txt)

    def build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression
    
    @api.multi
    def copy(self, default=None):
        priority = self.search_count([('model','=',self.model)])+1
        copy_count = self.search_count([('name','=',self.name)])
        default = dict(default or {},
                       name=_("%s (%s)") % (self.name, copy_count),
                       priority=priority)
        return super(SmsTemplate, self).copy(default=default)

    @api.multi
    def unlink(self):
        self.unlink_action()
        return super(SmsTemplate, self).unlink()

    @api.multi
    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_window:
                template.ref_ir_act_window.sudo().unlink()
            # 10.0 增加 ir.values
            if template.ref_ir_value:
                template.ref_ir_value.sudo().unlink()
        return True

    @api.multi
    def create_action(self):
        ActWindowSudo = self.env['ir.actions.act_window'].sudo()
        # 10.0 增加 ir.values
        IrValuesSudo = self.env['ir.values'].sudo()
        view = self.env.ref('sms.send_sms_view_form')

        for template in self:
            button_name = _('Send SMS (%s)') % template.name
            action = ActWindowSudo.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'sms.send_sms',
                'src_model': template.model_id.model,
                'view_type': 'form',
                'context': "{'default_sand_mode': 'template', 'default_template_id' : %d}" % (template.id),
                'view_mode': 'form,tree',
                'view_id': view.id,
                'target': 'new',
                # 'binding_model_id': template.model_id.id,
            })
            # 10.0 增加 ir.values
            ir_value = IrValuesSudo.create({
                'name': button_name,
                'model': template.model_id.model,
                'key2': 'client_action_multi',
                'value': "ir.actions.act_window,%s" % action.id})

            template.write({
                'ref_ir_act_window': action.id,
                 # 10.0 增加 ir.values
                'ref_ir_value': ir_value.id,
            })

        return True

