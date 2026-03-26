# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PhongBan(models.Model):
    _name = 'phong_ban'
    _description = 'Bảng chứa thông tin phòng ban'
    _rec_name = 'ten_phong_ban'
    _order = 'ma_phong_ban'

    ma_phong_ban = fields.Char("Mã phòng ban", readonly=True, copy=False)
    ten_phong_ban = fields.Char("Tên phòng ban", required=True)
    
    # Bộ lọc thông minh: Trưởng phòng phải là người thuộc chính phòng ban này
    truong_phong_id = fields.Many2one('nhan_vien', string="Trưởng phòng", domain="[('phong_ban_id', '=', id)]")
    
    mo_ta = fields.Text("Mô tả")
    
    # ================= KẾT NỐI DỮ LIỆU & THỐNG KÊ =================
    nhan_vien_ids = fields.One2many('nhan_vien', 'phong_ban_id', string="Danh sách nhân viên")
    
    so_luong_nhan_vien = fields.Integer("Số lượng nhân viên", compute="_compute_so_luong_nhan_vien", store=True)
    
    # [ĐÃ MỞ KHÓA] Liên kết xuyên Model: Tổng khối lượng công việc của cả phòng
    tong_viec_dang_lam = fields.Integer(string="Tổng việc đang xử lý", compute="_compute_tong_viec")

    @api.depends('nhan_vien_ids')
    def _compute_so_luong_nhan_vien(self):
        for record in self:
            record.so_luong_nhan_vien = len(record.nhan_vien_ids)

    @api.depends('nhan_vien_ids.so_viec_dang_lam')
    def _compute_tong_viec(self):
        """Tự động cộng dồn số việc mà các nhân viên trong phòng đang làm"""
        for rec in self:
            if rec.nhan_vien_ids:
                # Dùng hàm mapped() của Odoo để lôi tất cả số việc đang làm của từng ông thợ ra và cộng lại
                rec.tong_viec_dang_lam = sum(rec.nhan_vien_ids.mapped('so_viec_dang_lam'))
            else:
                rec.tong_viec_dang_lam = 0

    @api.model
    def create(self, vals):
        if not vals.get('ma_phong_ban'):
            counter = 1
            code = f"PB{counter:04d}"
            # Dùng search_count tối ưu hiệu năng hơn so với search
            while self.search_count([('ma_phong_ban', '=', code)]):
                counter += 1
                code = f"PB{counter:04d}"
            vals['ma_phong_ban'] = code
        return super(PhongBan, self).create(vals)