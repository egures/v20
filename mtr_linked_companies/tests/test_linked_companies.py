# SPDX-License-Identifier: LicenseRef-Projet-Proprietary
#
# Copyright (c) 2026 Projet İş Çözümleri Limited Şirketi
#
# This file is part of a proprietary Odoo addon.
# Use of this file is governed by the LICENSE file included
# in the root of this repository.

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestLinkedCompanies(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_co = cls.env['res.partner'].create({
            'name': 'MTR Group Holding',
            'vat': 'TR1111111111',
            'street': 'Holding Street 1',
            'city': 'Istanbul',
        })
        cls.cari = cls.env['res.partner'].create({
            'name': 'Linked Cari A',
            'is_linked_company': True,
            'vat': 'TR2222222222',
            'street': 'Cari Street 5',
            'city': 'Izmir',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Service',
            'type': 'service',
            'list_price': 100.0,
        })

    def _create_order(self, partner):
        return self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                }),
            ],
        })

    def test_link_independent_company(self):
        """A linked company keeps its own commercial entity under the parent."""
        self.cari.parent_id = self.group_co
        self.assertEqual(self.cari.commercial_partner_id, self.cari)
        self.assertEqual(self.cari.vat, 'TR2222222222')
        self.assertEqual(self.cari.type, 'other')
        self.assertEqual(self.cari.street, 'Cari Street 5')
        self.assertEqual(self.group_co.commercial_partner_id, self.group_co)

    def test_link_with_accounting_history(self):
        """The core same-VAT guard is bypassed for linked companies and
        journal items are not repartnered."""
        invoice = self.init_invoice(
            'out_invoice', partner=self.cari, products=[self.product], post=True)
        self.cari.parent_id = self.group_co
        self.assertEqual(self.cari.parent_id, self.group_co)
        self.assertEqual(
            invoice.line_ids.partner_id, self.cari,
            'Journal items must stay on the linked company')

    def test_regular_contact_guard_preserved(self):
        """Non-linked partners still hit the core same-VAT guard."""
        regular = self.env['res.partner'].create({
            'name': 'Plain Contact', 'vat': 'TR3333333333',
        })
        self.init_invoice(
            'out_invoice', partner=regular, products=[self.product], post=True)
        with self.assertRaises(UserError):
            regular.parent_id = self.group_co

    def test_smart_button_aggregation(self):
        """child_of counters on the parent include the linked company's docs."""
        self.cari.parent_id = self.group_co
        self._create_order(self.cari)
        self._create_order(self.group_co)
        self.group_co.invalidate_recordset()
        self.assertEqual(self.group_co.sale_order_count, 2)
        self.assertEqual(self.cari.sale_order_count, 1)

    def test_invoice_action_aggregation(self):
        self.cari.parent_id = self.group_co
        invoice = self.init_invoice(
            'out_invoice', partner=self.cari, products=[self.product], post=True)
        action = self.group_co.action_view_partner_invoices()
        found = self.env['account.move'].search(action['domain'])
        self.assertIn(invoice, found)

    def test_flag_removal_blocked_while_linked(self):
        self.cari.parent_id = self.group_co
        with self.assertRaises(ValidationError):
            self.cari.is_linked_company = False

    def test_unlink_then_unflag(self):
        self.cari.parent_id = self.group_co
        self.cari.parent_id = False
        self.cari.is_linked_company = False
        self.assertEqual(self.cari.commercial_partner_id, self.cari)

    def test_cycle_blocked(self):
        self.cari.parent_id = self.group_co
        with self.assertRaises(ValidationError):
            self.group_co.parent_id = self.cari

    def test_group_company_on_documents(self):
        self.cari.parent_id = self.group_co
        order = self._create_order(self.cari)
        self.assertEqual(order.group_company_id, self.group_co)
        invoice = self.init_invoice(
            'out_invoice', partner=self.cari, products=[self.product], post=True)
        self.assertEqual(invoice.group_company_id, self.group_co)
