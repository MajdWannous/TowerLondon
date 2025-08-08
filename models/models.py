# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError
import base64
import os


class TowerNormTable(models.Model):
    _name = 'tower.norm.table'
    _description = 'Tower Normative Table (Attempts and Time)'

    norm_type = fields.Selection([
        ('attempts', 'Attempts'),
        ('time', 'Time')
    ], required=True)
    age = fields.Integer(string='Age', required=True)
    mean = fields.Float(string='Mean', required=True)
    std_dev = fields.Float(string='Standard Deviation', required=True)

    @api.model
    def create(self, vals):
        self._check_unique_age_type(vals)
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            new_vals = {
                'age': vals.get('age', rec.age),
                'norm_type': vals.get('norm_type', rec.norm_type),
            }
            rec._check_unique_age_type(new_vals, exclude_id=rec.id)
        return super().write(vals)

    def _check_unique_age_type(self, vals, exclude_id=None):
        domain = [
            ('age', '=', vals.get('age')),
            ('norm_type', '=', vals.get('norm_type'))
        ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        exists = self.search(domain, limit=1)
        if exists:
            raise ValidationError("A record with this age and type already exists.")



    def get_norm_value(self, age, norm_type):
        record = self.env['tower.norm.table'].search([
            ('norm_type', '=', norm_type),
            ('age', '=', age)
        ], limit=1)
        if record:
            return record.mean, record.std_dev
        else:
            return 0.0, 1.0

class ReportTowerPatient(models.AbstractModel):
    _name = 'report.tower_london.report_tower_patient_template'
    _description = 'Patient Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        patients = self.env['tower.patient'].browse(docids or [])

        if data and data.get('logo_base64'):
            logo_base64 = data['logo_base64']
        else:
            module_path = os.path.dirname(os.path.abspath(__file__))
            base_path = os.path.dirname(module_path)
            img_path = os.path.join(base_path, 'static', 'src', 'img', 'logo.png')
            with open(img_path, 'rb') as f:
                image_data = f.read()
            logo_base64 = 'data:image/png;base64,' + base64.b64encode(image_data).decode('utf-8')

        return {
            'doc_ids': docids,
            'doc_model': 'tower.patient',
            'docs': patients,
            'logo_base64': logo_base64,
        }

class Patient(models.Model):
    _name = 'tower.patient'
    _description = 'patient record'
    name = fields.Char(string='FullName', required=True)
    birth_date = fields.Date(string='Birth Date', required=True)
    gender = fields.Selection([('m','Male'),('f','Female')], string='Gender')
    parent_phone = fields.Char(string='Parent Phone')
    test_ids = fields.One2many('tower.of.london', 'patient_id', string='Tower Tests')
    parent_id = fields.Many2one('res.partner', string='Parent', domain="[('parent_id','=',False)]")
    invoice_ids = fields.One2many('account.move', 'tower_patient_id', string='Invoices')

    def print_patient_report(self):
        module_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(module_path)
        img_path = os.path.join(base_path, 'static', 'src', 'img', 'logo.png')

        with open(img_path, 'rb') as f:
            image_data = f.read()
        logo_base64 = 'data:image/png;base64,' + base64.b64encode(image_data).decode('utf-8')

        return self.env.ref('tower_london.action_report_tower_patient').report_action(
            self,
            data={'logo_base64': logo_base64}
        )


class TowerOfLondonTest(models.Model):
    _name = 'tower.of.london'
    _description = ' tower of london'

    patient_id = fields.Many2one('tower.patient', string='Patient', required=True)
    test_date = fields.Date(string='Test date', default=fields.Date.today, required=True)

    attempts_score = fields.Float(string='Attempts score', required=True)
    time_score = fields.Float(string='Time score', required=True)
    show_invoice_button = fields.Boolean(compute='_compute_show_invoice_button')

    age_years = fields.Integer(string='Age years', compute='_compute_age', store=True)
    age_months = fields.Integer(string='Age months', compute='_compute_age', store=True)

    attempts_z = fields.Float(string='Z-Score attempts', compute='_compute_scores', store=True)
    attempts_result = fields.Selection(
        [('within', 'Within'),
         ('borderline', 'Borderline'),
         ('below', 'Below'),
         ('above', 'Above')],
        string='attempts result',
        compute='_compute_scores',
        store=True
    )

    time_z = fields.Float(string='Z-Score time', compute='_compute_scores', store=True)
    time_result = fields.Selection(
        [('within', 'Within'),
         ('borderline', 'Borderline'),
         ('below', 'Below'),
         ('above', 'Above')],
        string='time_result',
        compute='_compute_scores',
        store=True
    )
    progress_summary = fields.Char(string='Progress Summary',
                compute='_compute_progress_summary',
                store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    specialist_id = fields.Many2one('res.users', string='Specialist')

    RESULT_RANKING = {
        'below': 0,
        'borderline': 1,
        'within': 2,
        'above': 3,
    }

    @api.depends('invoice_id')
    def _compute_show_invoice_button(self):
        for rec in self:
            rec.show_invoice_button = bool(rec.invoice_id)






    @api.depends('patient_id.birth_date', 'test_date')
    def _compute_age(self):
        for rec in self:
            if rec.patient_id.birth_date and rec.test_date:
                age_days = (rec.test_date - rec.patient_id.birth_date).days
                years = age_days // 365
                months = (age_days % 365) // 30
                rec.age_years = years
                rec.age_months = months
            else:
                rec.age_years = 0
                rec.age_months = 0

    def get_reference_age(self):
            year = self.age_years
            month = self.age_months
            ref_age = year
            # Rule:
            # 6.5 - 7.5 → 7
            if month >= 6:
                ref_age += 1
            return ref_age

    @api.depends('attempts_score', 'time_score', 'age_years', 'age_months')
    def _compute_scores(self):
        for rec in self:
            ref_age = rec.get_reference_age()

            # Attempts
            avg, std = rec.env['tower.norm.table'].get_norm_value(ref_age, 'attempts')
            rec.attempts_z = (rec.attempts_score - avg) / std if std else 0
            rec.attempts_result = rec.classify_result(rec.attempts_z)

            # Time
            avg, std = rec.env['tower.norm.table'].get_norm_value(ref_age, 'time')
            rec.time_z = (rec.time_score - avg) / std if std else 0
            rec.time_result = rec.classify_result(rec.time_z)

    def classify_result(self, z):
        category = self.env['z.score.category'].search([
            ('min_value', '<=', z),
            ('max_value', '>=', z)
        ], limit=1)

        return category.code if category else False

    @api.depends('attempts_result', 'time_result')
    def _compute_progress_summary(self):
        for rec in self:
            previous = rec.get_previous_test()
            if not previous:
                rec.progress_summary = "First Test"
                continue

            att_current = self.RESULT_RANKING.get(rec.attempts_result, 0)
            time_current =self.RESULT_RANKING.get(rec.time_result, 0)
            att_prev = self.RESULT_RANKING.get(previous.attempts_result, 0)
            time_prev = self.RESULT_RANKING.get(previous.time_result, 0)

            att_change = (att_current > att_prev) - (att_current < att_prev)
            time_change = (time_current > time_prev) - (time_current < time_prev)

            if att_change == 0 and time_change == 0:
                rec.progress_summary = "No Change"
            elif att_change > 0 and time_change > 0:
                rec.progress_summary = "Overall Improved"
            elif att_change < 0 and time_change < 0:
                rec.progress_summary = "Overall Regressed"
            elif att_change > 0:
                rec.progress_summary = "Attempts Improved, Time Regressed" if time_change < 0 else "Attempts Improved"
            elif time_change > 0:
                rec.progress_summary = "Time Improved, Attempts Regressed" if att_change < 0 else "Time Improved"
            else:
                rec.progress_summary = "Mixed Progress"

    def get_previous_test(self):
        for rec in self:
            if not rec.patient_id or not rec.test_date:
                return self.browse()
            domain = [
                ('patient_id', '=', rec.patient_id.id),
                ('test_date', '<=', rec.test_date),
                ('id', '!=', rec.id if rec.id and isinstance(rec.id, int) else 0),
            ]
            previous_tests = self.search(domain, order='test_date desc, id desc', limit=1)
            return previous_tests

    @api.model
    def get_dashboard_data(self):
        current_user = self.env.user
        domain = []
        if not current_user.has_group('base.group_system'):
            domain = []

        records = self.search(domain, order='age_years')
        data_by_patient = {}

        total_patients = self.env['tower.patient'].search_count([])
        total_invoices = self.env['account.move'].search_count([('tower_patient_id', '!=', False)])
        improved_tests = 0
        regressed_tests = 0

        for rec in records:
            patient_name = rec.patient_id.name or "Unknown"
            if patient_name not in data_by_patient:
                data_by_patient[patient_name] = {
                    'ages': [],
                    'z_attempts': [],
                    'z_time': [],
                }

            age = rec.get_reference_age()
            data_by_patient[patient_name]['ages'].append(str(age))
            data_by_patient[patient_name]['z_attempts'].append(rec.attempts_z)
            data_by_patient[patient_name]['z_time'].append(rec.time_z)

            previous = rec.get_previous_test()
            if previous:
                att_change = (self.RESULT_RANKING.get(rec.attempts_result, 0) > self.RESULT_RANKING.get(previous.attempts_result, 0)) - (
                        self.RESULT_RANKING.get(rec.attempts_result, 0) < self.RESULT_RANKING.get( previous.attempts_result, 0))
                time_change = (self.RESULT_RANKING.get(rec.time_result, 0) > self.RESULT_RANKING.get(previous.time_result, 0)) - (
                        self.RESULT_RANKING.get(rec.time_result, 0) < self.RESULT_RANKING.get(previous.time_result, 0))

                if att_change > 0 or time_change > 0:
                    improved_tests += 1
                elif att_change < 0 or time_change < 0:
                    regressed_tests += 1

        return {
            'patients_data': data_by_patient,
            'stats': {
                'total_patients': total_patients,
                'total_invoices': total_invoices,
                'improved_tests': improved_tests,
                'regressed_tests': regressed_tests,
            }
        }




    def action_delete_return(self):
        self.unlink()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tower.of.london',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record.create_invoice()
        return record


    def create_invoice(self):
        for rec in self:
            if not rec.patient_id or not rec.patient_id.parent_id:
                continue

            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            if not journal:
                journal = self.env['account.journal'].create({
                    'name': 'Training Journal',
                    'code': 'TJ',
                    'type': 'sale',
                })

            # first account type income
            account = self.env['account.account'].search([
                ('account_type', '=', 'income')
            ], limit=1)

            if not account:
                raise ValueError('Income account not found!')

            invoice_line = {
                'name': 'Test Service',
                'quantity': 1,
                'price_unit' : self.env.company.tower_test_price,
                'account_id': account.id,  # link account with invoice
            }

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.patient_id.parent_id.id,
                'invoice_date': rec.test_date or fields.Date.today(),
                'journal_id': journal.id,
                'invoice_line_ids': [(0, 0, invoice_line)],
                'tower_patient_id': rec.patient_id.id,
            })
            rec.invoice_id = invoice.id

    def open_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    tower_patient_id = fields.Many2one('tower.patient', string='Patient (Tower Test)')

class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def read(self, fields=None, load='_classic_read'):
        res = super().read(fields=fields, load=load)
        for action in res:
            if action.get('xml_id') == 'tower_london.action_tower_settings_company_only_price':
                action['res_id'] = self.env.company.id
        return res

class FinanceReport(models.AbstractModel):
    _name = 'report.tower_london.finance_report_template'
    _description = 'Finance Officer Report'

    def _get_report_values(self, docids, data=None):
        print("====== ENTERED _get_report_values ======")

        # Check user permissions
        if not (
                self.env.user.has_group('tower_london.group_tower_finance') or
                self.env.user.has_group('base.group_system')
        ):
            raise AccessError("You do not have permission to print this report.")

        # Get all invoices linked to patients
        invoices = self.env['account.move'].search([('tower_patient_id', '!=', False)])
        print("Total invoices linked to patients:", len(invoices))

        total_invoices = len(invoices)
        paid_invoice_count = 0
        unpaid_invoice_count = 0
        total_paid_amount = 0.0
        total_unpaid_amount = 0.0

        for invoice in invoices:
            if invoice.payment_state == 'paid':
                paid_invoice_count += 1
                total_paid_amount += invoice.amount_total
            else:
                unpaid_invoice_count += 1
                total_unpaid_amount += invoice.amount_total

        module_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(module_path)
        img_path = os.path.join(base_path, 'static', 'src', 'img', 'logo.png')

        with open(img_path, 'rb') as f:
            image_data = f.read()
        logo_base64 = 'data:image/png;base64,' + base64.b64encode(image_data).decode('utf-8')

        print("Total invoices:", total_invoices)
        print("Paid invoices:", paid_invoice_count)
        print("Unpaid invoices:", unpaid_invoice_count)
        print("Total paid amount:", total_paid_amount)
        print("Total unpaid amount:", total_unpaid_amount)

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'total_invoices': total_invoices,
            'paid_invoices': paid_invoice_count,
            'unpaid_invoices': unpaid_invoice_count,
            'total_paid_amount': total_paid_amount,
            'total_unpaid_amount': total_unpaid_amount,
            'logo_base64': logo_base64,
        }




class TowerOfLondonClinicReport(models.AbstractModel):
    _name = 'report.tower_london.report_clinic_dashboard_template'
    _description = 'Clinic Dashboard Report'

    def _get_report_values(self, docids, data=None):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError("You do not have permission to print this report.")
        module_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(module_path)
        img_path = os.path.join(base_path, 'static', 'src', 'img', 'logo.png')

        with open(img_path, 'rb') as f:
            image_data = f.read()
        logo_base64 = 'data:image/png;base64,' + base64.b64encode(image_data).decode('utf-8')
        docs = self.env['tower.of.london'].get_dashboard_data()
        return {
            'doc_ids': [1],
            'doc_model': 'tower.of.london',
            'docs': [docs],
            'logo_base64': logo_base64,
        }

class ResCompany(models.Model):
    _inherit = 'res.company'

    tower_test_price = fields.Float(string="Tower Test Price", default=4.0)


class ZScoreCategory(models.Model):
    _name = 'z.score.category'
    _description = 'Z-Score Category'

    code = fields.Selection([
        ('within', 'Within'),
        ('borderline', 'Borderline'),
        ('below', 'Below'),
        ('above', 'Above'),
    ], required=True)
    name = fields.Char(string='Category Name', required=True)
    min_value = fields.Float(string='Minimum Z')
    max_value = fields.Float(string='Maximum Z')
    color = fields.Char(string='Color')
    color_box = fields.Html(string='Color Box', compute='_compute_color_box')

    @api.depends('color')
    def _compute_color_box(self):
        for rec in self:
            if rec.color:
                rec.color_box = '<div style="width: 20px; height: 20px; background-color: %s;"></div>' % rec.color
            else:
                rec.color_box = ''