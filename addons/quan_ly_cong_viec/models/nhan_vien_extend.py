# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhanVienExtend(models.Model):
    _inherit = 'nhan_vien' # Tìm bảng nhân viên để cấy thêm đồ vào

    cong_viec_ids = fields.One2many('cong_viec', 'nguoi_thuc_hien_id', string="Lịch sử công việc")
    diem_trung_binh = fields.Float(string="⭐ Điểm TB Khách Đánh Giá", compute="_compute_diem_trung_binh")
    so_viec_dang_lam = fields.Integer(string="Số việc đang ôm", compute='_compute_so_viec')

    @api.depends('cong_viec_ids.diem_danh_gia')
    def _compute_diem_trung_binh(self):
        for rec in self:
            cac_viec = rec.cong_viec_ids.filtered(lambda t: t.diem_danh_gia and t.diem_danh_gia != '0')
            if cac_viec:
                tong_diem = sum(int(t.diem_danh_gia) for t in cac_viec)
                rec.diem_trung_binh = round(tong_diem / len(cac_viec), 2)
            else:
                rec.diem_trung_binh = 0.0

    def _compute_so_viec(self):
        for rec in self:
            if rec.id:
                count = self.env['cong_viec'].search_count([
                    ('nguoi_thuc_hien_id', '=', rec.id),
                    ('trang_thai', 'in', ['moi', 'dang_lam'])
                ])
                rec.so_viec_dang_lam = count
            else:
                rec.so_viec_dang_lam = 0