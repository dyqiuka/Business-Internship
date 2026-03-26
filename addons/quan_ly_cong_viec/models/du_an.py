# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions

class DuAn(models.Model):
    _name = 'du_an'
    _description = 'Quản lý Dự án'
    _rec_name = 'ten_du_an'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ma_du_an = fields.Char(string="Mã dự án", readonly=True, copy=False, default='Mới')
    ten_du_an = fields.Char(string="Tên dự án", required=True, tracking=True)
    
    nguoi_quan_ly_id = fields.Many2one('nhan_vien', string="Quản lý dự án", tracking=True)
    khach_hang_id = fields.Many2one('khach_hang', string="Khách hàng đối tác", tracking=True)
    
    # DANH SÁCH CÔNG VIỆC THUỘC DỰ ÁN NÀY
    cong_viec_ids = fields.One2many('cong_viec', 'du_an_id', string="Danh sách công việc")
    
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu", tracking=True)
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc dự kiến", tracking=True)
    
    trang_thai = fields.Selection([
        ('khoi_tao', 'Khởi tạo'),
        ('dang_trien_khai', 'Đang triển khai 🚀'),
        ('tam_dung', 'Tạm dừng ⏸️'),
        ('hoan_thanh', 'Hoàn thành ✅')
    ], string="Trạng thái", default='khoi_tao', tracking=True)
    
    ngan_sach = fields.Float(string="Ngân sách dự án", tracking=True)
    mo_ta = fields.Text(string="Mô tả & Mục tiêu")

    # ================= TÍNH NĂNG NÂNG CẤP: TỰ ĐỘNG THỐNG KÊ =================
    tong_cong_viec = fields.Integer(string="Tổng số việc", compute='_compute_tien_do', store=True)
    viec_hoan_thanh = fields.Integer(string="Đã hoàn thành", compute='_compute_tien_do', store=True)
    tien_do_phan_tram = fields.Float(string="Tiến độ (%)", compute='_compute_tien_do', store=True)

    @api.depends('cong_viec_ids', 'cong_viec_ids.trang_thai')
    def _compute_tien_do(self):
        """Hàm tự động tính toán tiến độ dự án và tự động chuyển trạng thái"""
        for rec in self:
            tong = len(rec.cong_viec_ids)
            hoan_thanh = len(rec.cong_viec_ids.filtered(lambda task: task.trang_thai == 'hoan_thanh'))
            
            rec.tong_cong_viec = tong
            rec.viec_hoan_thanh = hoan_thanh
            
            phan_tram = (hoan_thanh / tong * 100.0) if tong > 0 else 0.0
            rec.tien_do_phan_tram = phan_tram
            
            # [TÍNH NĂNG MỚI]: TỰ ĐỘNG CHUYỂN TRẠNG THÁI
            # Chỉ tự động chuyển nếu người dùng không tự tay bấm Tạm dừng
            if rec.trang_thai != 'tam_dung':
                if tong > 0 and phan_tram == 100.0:
                    rec.trang_thai = 'hoan_thanh'
                elif tong > 0 and phan_tram > 0.0 and phan_tram < 100.0:
                    rec.trang_thai = 'dang_trien_khai'
                elif tong == 0 or phan_tram == 0.0:
                    rec.trang_thai = 'khoi_tao'
    # ================= RÀO CHẮN BẢO VỆ DỮ LIỆU (VALIDATION) =================
    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_ngay_hop_le(self):
        """Chặn người dùng nhập Ngày kết thúc trước Ngày bắt đầu"""
        for rec in self:
            if rec.ngay_bat_dau and rec.ngay_ket_thuc and rec.ngay_ket_thuc < rec.ngay_bat_dau:
                raise exceptions.ValidationError("⚠️ LỖI LOGIC: Ngày kết thúc không thể diễn ra trước Ngày bắt đầu!")

    def write(self, vals):
        """Khóa quyền: Chỉ Sếp và Quản lý (Mức 1, 2) mới được sửa Ngân sách hoặc đổi Trạng thái dự án"""
        if 'ngan_sach' in vals or 'trang_thai' in vals:
            if not self.env.user.has_group('base.group_system'):
                nhan_vien = self.env['nhan_vien'].search([('ho_ten_day_du', '=', self.env.user.name)], limit=1)
                if not nhan_vien or nhan_vien.cap_bac not in ['1', '2']:
                    raise exceptions.UserError("🛑 TỪ CHỐI TRUY CẬP: Chỉ Quản lý dự án hoặc Giám đốc (Mức 1, 2) mới được quyền can thiệp vào Ngân sách và Trạng thái dự án!")
                    
        return super(DuAn, self).write(vals)

    # ================= SINH MÃ TỰ ĐỘNG THÔNG MINH =================
    @api.model
    def create(self, vals):
        if vals.get('ma_du_an', 'Mới') == 'Mới':
            # Thuật toán tìm ID cuối cùng an toàn hơn đếm count (tránh trùng lặp khi có dự án bị xóa)
            last_project = self.search([], order='id desc', limit=1)
            if last_project and last_project.ma_du_an.startswith('DA'):
                try:
                    last_number = int(last_project.ma_du_an[2:])
                    vals['ma_du_an'] = f"DA{last_number + 1:03d}"
                except ValueError:
                    vals['ma_du_an'] = "DA001"
            else:
                vals['ma_du_an'] = "DA001"
                
        return super(DuAn, self).create(vals)