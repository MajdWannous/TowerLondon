# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date

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

    _sql_constraints = [
        ('unique_age_type', 'unique(norm_type, age)', 'Each age must have only one entry per type!')
    ]

    def get_norm_value(self, age, norm_type):
        record = self.env['tower.norm.table'].search([
            ('norm_type', '=', norm_type),
            ('age', '=', age)
        ], limit=1)
        if record:
            return record.mean, record.std_dev
        else:
            return 0.0, 1.0



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


class TowerOfLondonTest(models.Model):
    _name = 'tower.of.london'
    _description = ' tower of london'

    patient_id = fields.Many2one('tower.patient', string='Patient', required=True)
    test_date = fields.Date(string='Test date', default=fields.Date.today, required=True)

    attempts_score = fields.Float(string='Attempts score', required=True)
    time_score = fields.Float(string='Time score', required=True)
    show_invoice_button = fields.Boolean(compute='_compute_show_invoice_button')

    # حسابات تلقائية
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
        if -1 <= z <= 1:
            return 'within'
        elif -2 <= z < -1:
            return 'borderline'
        elif z < -2:
            return 'below'
        elif z > 2:
            return 'above'
        return False

    @api.depends('attempts_result', 'time_result')
    def _compute_progress_summary(self):
        for rec in self:
            previous = rec.get_previous_test()
            if not previous:
                rec.progress_summary = "First Test"
                continue

            att_current = rec.attempts_result
            time_current = rec.time_result
            att_prev = previous.attempts_result
            time_prev = previous.time_result

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
            # استبعاد السجل الحالي
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
        if not current_user.has_group('base.group_system'):  # ليس أدمن
            domain = [('specialist_id', '=', current_user.id)]

        records = self.search(domain, order='age_years')
        data_by_patient = {}

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

        return data_by_patient

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
                raise ValueError('iname account not found!')

            invoice_line = {
                'name': 'Test Service',
                'quantity': 1,
                'price_unit': 4.0,
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