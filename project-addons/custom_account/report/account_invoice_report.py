# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields


class account_invoice_report(models.Model):

    _inherit = 'account.invoice.report'

    payment_mode_id = fields.Many2one('payment.mode', 'Payment mode')
    number = fields.Char('Number')
    benefit = fields.Float('Benefit')
    branch = fields.Char('Branch')

    def _select(self):
        select_str = super(account_invoice_report, self)._select()
        select_str += ', sub.payment_mode_id as payment_mode_id,' \
                      ' sub.number as number' \
                      ', sub.benefit as benefit' \
                      ', sub.name as name'
        return select_str

    def _sub_select(self):
        select_str = super(account_invoice_report, self)._sub_select()
        select_str += ', ai.payment_mode_id,' \
                      ' ai.number ' \
                      ', sum(ail.quantity * ail.price_unit * (100.0-ail.discount) ' \
                      '/ 100.0) - sum(sol.purchase_price*ail.quantity) as benefit, ' \
                      'pb.name'
        return select_str

    def _from(self):
        from_str = super(account_invoice_report, self)._from()
        from_str += ' LEFT JOIN sale_order_line_invoice_rel solir ON solir.invoice_id = ail.id ' \
                    ' LEFT JOIN sale_order_line sol ON sol.id = solir.order_line_id '\
                    ' LEFT JOIN product_brand pb ON pt.product_brand_id = pb.id '
        return from_str

    def _group_by(self):
        group_by_str = super(account_invoice_report, self)._group_by()
        group_by_str += ', ai.payment_mode_id,' \
                        ' ai.number,' \
                        ' pb.name'

        return group_by_str
