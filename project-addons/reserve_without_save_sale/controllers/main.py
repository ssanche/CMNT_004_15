# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Pexego All Rights Reserved
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

import json
import logging
from openerp.addons.web import http
from openerp.addons.web.http import request

_logger = logging.getLogger(__name__)


class WebsiteReservation(http.Controller):

    @http.route(['/reservations/create'],
                type='http', methods=['POST'], auth='user')
    def create_reservation(self, **post):
        _logger.debug('Creando reserva: %s', post)
        cr, uid, context = request.cr, request.uid, request.context
        reserv_obj = request.registry['stock.reservation']
        product_obj = request.registry['product.product']
        sale_line_obj = request.registry['sale.order.line']
        warehouse = request.registry['stock.warehouse'].\
            browse(cr, uid, int(post['warehouse']), context)
        product = product_obj.browse(cr, uid, int(post['product_id']), context)
        if product.type == "product":
            vals = {
                'product_id': int(post['product_id']),
                'product_uom': int(post['uom']),
                'product_uom_qty': float(post['qty']),
                'date_validity': False,
                'name': post.get('name', product.default_code),
                'location_id': warehouse.lot_stock_id.id,
                'price_unit': float(post['price_unit']),
                'unique_js_id': post['unique_js_id']
            }
            new_reservation = reserv_obj.create(cr, uid, vals, context)
            reserv_obj.browse(cr, uid, new_reservation, context).reserve()
            line_ids = sale_line_obj.search(cr, uid, [('unique_js_id', '=',
                                                       post['unique_js_id'])])
            if line_ids:
                reserv_obj.write(cr, uid, new_reservation,
                                 {'sale_line_id': line_ids[0]})
        return json.dumps(True)

    @http.route(['/reservations/unlink'],
                type='http', methods=['POST'], auth='user')
    def unlink_reservation(self, **post):
        unique_js_id = int(post['unique_js_id'])
        cr, uid, context = request.cr, request.uid, request.context
        reserv_obj = request.registry['stock.reservation']
        reservation = reserv_obj.search(cr, uid, [('unique_js_id', '=',
                                                   unique_js_id)],
                                        context=context)
        reserv_obj.unlink(cr, uid, reservation, context)
        return json.dumps(True)

    @http.route(['/reservations/write'],
                type='http', methods=['POST'], auth='user')
    def write_reservation(self, **post):
        """
            Si se ha modificado el producto, se elimina la reserva y se crea
            una nueva.
            Si solo se modifica la cantidad se escribe.

            Si se modifica el producto:
            @POST product_id
            @POST name
            @POST old_unique_js_id
            @POST unique_js_id(la reserva a crear)

            Si se modifica la cantidad
            @POST qty
            @POST unique_js_id(la reserva a modificar)
        """
        cr, uid, context = request.cr, request.uid, request.context
        reserv_obj = request.registry['stock.reservation']
        product_obj = request.registry['product.product']
        if post.get('product_id', False):
            product = product_obj.browse(cr, uid, int(post['product_id']),
                                         context)
            if product.type == "product":
                reservation = reserv_obj.\
                    search(cr, uid, [('unique_js_id', '=',
                                      post['old_unique_js_id'])],
                           context=context)
                new_data = {
                    'name': post.get('name', product.default_code),
                    'product_id': post['product_id'],
                    'unique_js_id': post['unique_js_id']
                }
                if post.get('qty'):
                    new_data['product_uom_qty'] = post['qty']
                reserv_id = reserv_obj.copy(cr, uid, reservation[0], new_data,
                                            context)
                reserv_obj.browse(cr, uid, reserv_id, context).reserve()
                reserv_obj.unlink(cr, uid, reservation, context)
            return json.dumps(True)
        elif post.get('qty'):
            reservation = reserv_obj.search(cr, uid, [('unique_js_id', '=',
                                                       post['unique_js_id'])],
                                            context=context)
            if reservation:
                reserv_obj.write(cr, uid, reservation,
                                 {'product_uom_qty': post['qty']}, context)
        elif post.get('old_unique_js_id', False) and \
                post.get('unique_js_id', False) and \
                post['old_unique_js_id'] != post['unique_js_id']:
            reservation = reserv_obj.\
                    search(cr, uid, [('unique_js_id', '=',
                                      post['old_unique_js_id'])],
                           context=context)
            reserv_obj.unlink(cr, uid, reservation, context)
        return json.dumps(True)
