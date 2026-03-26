# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta 

class GoiBaoHanh(models.Model):
    _name = 'goi_bao_hanh'
    _description = 'Quản lý Gói Bảo Hành'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Thêm lịch sử thay đổi để theo dõi

    # [ĐÃ SỬA]: Tự động sinh mã duy nhất, không dùng default cứng
    name = fields.Char(string="Mã Bảo Hành", required=True, copy=False, readonly=True, default='Mới', tracking=True)
    khach_hang_id = fields.Many2one('khach_hang', string="Khách hàng", required=True, tracking=True)
    
    # [ĐÃ SỬA]: Rút gọn key của Selection để dễ tính toán bên dưới
    loai_goi = fields.Selection([
        ('6', 'Gói Cơ bản (6 tháng)'),
        ('12', 'Gói Tiêu chuẩn (12 tháng)'),
        ('24', 'Gói VIP (24 tháng)')
    ], string="Loại gói", required=True, tracking=True)

    ngay_kich_hoat = fields.Date(string="Ngày kích hoạt", default=fields.Date.context_today, tracking=True)
    ngay_het_han = fields.Date(string="Ngày hết hạn", compute='_compute_ngay_het_han', store=True, tracking=True)

    # [ĐÃ SỬA]: Trạng thái trở thành trường tự động tính toán (Compute)
    trang_thai = fields.Selection([
        ('hieu_luc', 'Đang hiệu lực'),
        ('het_han', 'Đã hết hạn')
    ], string="Trạng thái", compute='_compute_trang_thai', store=True, tracking=True)

    @api.depends('ngay_kich_hoat', 'loai_goi')
    def _compute_ngay_het_han(self):
        """Hàm tự động tính ngày hết hạn dựa vào loại gói"""
        for rec in self:
            if rec.ngay_kich_hoat and rec.loai_goi:
                thang = int(rec.loai_goi)
                # Dùng relativedelta để cộng chuẩn xác số tháng (Không bị lệch ngày)
                rec.ngay_het_han = rec.ngay_kich_hoat + relativedelta(months=thang)
            else:
                rec.ngay_het_han = False

    @api.depends('ngay_het_han')
    def _compute_trang_thai(self):
        """Hàm AI Tự động kiểm tra: Nếu hôm nay lớn hơn ngày hết hạn -> Tự động khóa gói"""
        for rec in self:
            if rec.ngay_het_han and rec.ngay_het_han < fields.Date.context_today(rec):
                rec.trang_thai = 'het_han'
            else:
                rec.trang_thai = 'hieu_luc'

    @api.model
    def create(self, vals):
        """Hàm tự động nhảy số thứ tự: BH-0001, BH-0002... khi tạo mới"""
        if vals.get('name', 'Mới') == 'Mới':
            # Tìm ID lớn nhất trong database để cộng thêm 1
            last_record = self.search([], order='id desc', limit=1)
            next_number = (last_record.id + 1) if last_record else 1
            vals['name'] = f"BH-{next_number:04d}"
            
        return super(GoiBaoHanh, self).create(vals)
    def name_get(self):
        """
        Ghi đè cách hiển thị tên Gói bảo hành.
        Mặc định hiển thị: BH-0001
        Sau khi sửa sẽ hiển thị: [BH-0001] Nguyễn Văn A - Gói Cơ bản (6 tháng)
        """
        result = []
        map_loai_goi = {
            '6': 'Gói Cơ bản (6 tháng)',
            '12': 'Gói Tiêu chuẩn (12 tháng)',
            '24': 'Gói VIP (24 tháng)'
        }
        for rec in self:
            # Lấy tên khách hàng
            ten_khach = rec.khach_hang_id.ten_khach_hang if rec.khach_hang_id else "Khách vãng lai"
            
            # Ép kiểu rec.loai_goi về dạng chuỗi (str) để chắc chắn khớp với bản đồ ở trên
            loai_goi_str = str(rec.loai_goi) if rec.loai_goi else ''
            ten_goi = map_loai_goi.get(loai_goi_str, 'Chưa rõ gói')
            
            # Lắp ráp thành chuỗi hoàn chỉnh
            full_name = f"[{rec.name}] {ten_khach} - {ten_goi}"
            
            result.append((rec.id, full_name))
            
        return result