# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Comunitea servicios Tecnológicos
#    $Omar Castiñeira Saavedra$ <omar@comunitea.com>
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
from openerp import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta


class product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_daily_sales(self):
        stock_per_day = 0
        virtual_stock = self.virtual_available
        replacements = self.search([('replacement_id', '=', self.id)])
        if replacements:
            virtual_stock += replacements[0].virtual_available
        if virtual_stock:
            last_sixty_days_sales = self.last_sixty_days_sales
            if replacements:
                last_sixty_days_sales += replacements[0].last_sixty_days_sales
            stock_per_day = last_sixty_days_sales / 60.0
        return stock_per_day

    @api.one
    def _calc_remaining_days(self):
        stock_days = 0.00
        stock_per_day = self.get_daily_sales()
        virtual_available = self.virtual_available - self.incoming_qty + \
                            self.qty_available_external
        if stock_per_day > 0 and virtual_available:
            stock_days = round(virtual_available / stock_per_day)

        self.remaining_days_sale = stock_days
        self.joking = stock_days * self.standard_price

    @api.model
    def calc_joking_index(self):

        search_date = (date.today() - relativedelta(days=60)). \
            strftime("%Y-%m-%d")
        warehouses = self.env["stock.warehouse"].search([])
        stock_location_ids = [x.lot_stock_id.id for x in warehouses]
        stock_location_ids. \
            append(self.env.ref('location_moves.stock_location_external').id)
        product_obj = self.env["product.product"]
        self.env.cr.\
            execute("select distinct product_id from stock_move where "
                    "date <= %s and location_dest_id in %s and "
                    "state = 'done' and company_id = %s",
                    (search_date, tuple(stock_location_ids),
                     self.env.user.company_id.id))
        res = self.env.cr.fetchall()
        joking_tot = 0
        product_ids = [x[0] for x in res]
        filter_ids = []
        max_joking = 0.0
        for stock_product_id in product_obj.browse(product_ids):
            if not stock_product_id.product_brand_id or not \
                    stock_product_id.product_brand_id.not_compute_joking:
                joking_tot += stock_product_id.joking
                filter_ids.append(stock_product_id.id)
        avg = joking_tot / len(filter_ids)
        for product in product_obj.search([]):
            if product.type != 'product' or product.id not in filter_ids:
                if product.joking_index != -1:
                    product.joking_index = -1
            else:
                joking_index = (product.joking - avg) / avg
                if product.joking_index > joking_index and product.joking_index > max_joking:
                    max_joking = product.joking_index
                elif product.joking_index < joking_index and joking_index > max_joking:
                    max_joking = joking_index
                if product.joking_index != joking_index:
                    product.joking_index = joking_index
        for product in product_obj.browse(filter_ids):
            if product.joking_index == -1 \
                    and product.last_sixty_days_sales == 0 \
                    and product.type == 'product' \
                    and product.categ_id.parent_id.name != 'Outlet' \
                    and (product.virtual_available - product.incoming_qty + product.qty_available_external) == 0:
                product.joking_index = 0
            elif product.joking_index == -1 \
                    and product.last_sixty_days_sales == 0 \
                    and product.type == 'product' \
                    and product.categ_id.parent_id.name != 'Outlet':
                product.joking_index = max_joking

    @api.model
    def _get_next_move(self, product, limit=1):
        next_move = self.env['stock.move'].search(
            [('product_id', '=', product.id),
             ('picking_type_id', '=', self.env.ref("stock.picking_type_in").id),
             ('location_id', '=', self.env.ref("stock.stock_location_suppliers").id),
             ('state', '=', 'assigned')],
            limit=limit,
            order='date_expected ASC')

        return next_move

    @api.one
    def _get_next_incoming_date(self):
        """ Get next incoming date """
        for product in self:
            next_move = self._get_next_move(product, limit=1)
            if next_move:
                product.next_incoming_date = next_move.date_expected

    @api.one
    def _get_min_suggested_qty(self):
        """ Get the min suggested qty to buy of a product """
        for product in self:
            next_moves = self._get_next_move(product, limit=3)
            sixty_days_sales = - product.last_sixty_days_sales
            order_cycle = product.order_cycle
            res = (sixty_days_sales / 60.0) * order_cycle \
                + product.virtual_stock_conservative
            for move in next_moves:
                res += move.product_uom_qty
            product.min_suggested_qty = res

    remaining_days_sale = fields.Float('Remaining Stock Days', readonly=True,
                                       compute='_calc_remaining_days',
                                       help="Stock measure in days of sale "
                                            "computed consulting sales in sixty "
                                            "days with stock.", multi=True)
    joking = fields.Float("Joking", readonly=True,
                          compute='_calc_remaining_days',
                          multi=True)
    joking_index = fields.Float("Joking Index", readonly=True)
    replacement_id = fields.Many2one("product.product", "Replaced by")
    min_days_id = fields.Many2one("minimum.day", "Stock Minimum Days",
                                  related="orderpoint_ids.min_days_id",
                                   readonly=True)
    next_incoming_date = fields.Date('Next incoming date', compute='_get_next_incoming_date')
    min_suggested_qty = fields.Integer('Min qty suggested', compute='_get_min_suggested_qty')
