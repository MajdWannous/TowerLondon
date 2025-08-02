# -*- coding: utf-8 -*-
# from odoo import http


# class TowerLondon(http.Controller):
#     @http.route('/tower_london/tower_london', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tower_london/tower_london/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('tower_london.listing', {
#             'root': '/tower_london/tower_london',
#             'objects': http.request.env['tower_london.tower_london'].search([]),
#         })

#     @http.route('/tower_london/tower_london/objects/<model("tower_london.tower_london"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tower_london.object', {
#             'object': obj
#         })
