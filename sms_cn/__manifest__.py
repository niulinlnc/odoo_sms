# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


{
    'name': 'SMS for China',
    'version': '1.0',
    'license': 'AGPL-3',
    'summary': """SMS base for China""",
    'description': """
    """,
    'depends': ['sms'],
    'author': 'dong@freshoo.cn',
    'website': 'https://github.com/freshoo-dong',
    'images': ['static/description/banner.png'],
    'category': 'Tools',
    'data': [
        'data/iap_account_data.xml',
        'views/sms_template.xml',
        'views/sms_message.xml',
        # 'views/mail_message_views.xml',
        'views/iap_views.xml',
        'wizard/send_sms.xml',
    ],
    'price': 0.0,
    'currency': 'EUR',
    'installable': True,
    'auto_install': True,
    'application': False,
}