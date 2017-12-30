# -*- coding: utf-8 -*-
# Copyright(c): 2018 dong (<dong@freshoo.cn>)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


{
    'name': 'SMS Aliyun gateway',
    'version': '1.0',
    'license': 'AGPL-3',
    'summary': """Send your SMS through Aliyun gateway""",
    'description': """
    """,
    'depends': ['sms_cn'],
    'author': 'dong@freshoo.cn',
    'website': 'https://github.com/freshoo-dong',
    'images': ['static/description/banner.png'],
    'category': 'Tools',
    'data': [
        'data/sms_data.xml',
    ],
    'price': 0.0,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': True,
}