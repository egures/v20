# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2026 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    group_company_id = fields.Many2one(
        'res.partner', 'Group Company', related='partner_id.parent_id',
        store=True, index=True, readonly=True,
        help='Parent (group) company of the customer, for consolidated reporting.')
