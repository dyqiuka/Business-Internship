# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions

class PhieuKiemDuyet(models.Model):
    _name = 'phieu_kiem_duyet'
    _description = 'Phiếu Kiểm duyệt Công việc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Tên Phiếu", compute='_compute_name', store=True)
    cong_viec_id = fields.Many2one('cong_viec', string="Công việc liên quan", required=True, readonly=True, ondelete="cascade")
    nguoi_duyet_id = fields.Many2one('nhan_vien', string="Sếp hoặc trưởng phòng kiểm duyệt", required=True, tracking=True)
    
    # Trường AI Báo cáo
    ai_bao_cao = fields.Html(string="🤖 AI Báo cáo Nghiệm thu", readonly=True)
    nhan_xet_cua_sep = fields.Text(string="Nhận xét của Sếp hoặc trưởng phòng (Nếu từ chối)", tracking=True)
    
    ket_qua_duyet = fields.Selection([
        ('cho_duyet', '⏳ Đang chờ duyệt'),
        ('dong_y', '✅ Đồng ý (Hoàn thành)'),
        ('tu_choi', '❌ Từ chối (Bắt làm lại)')
    ], string="Kết quả", default='cho_duyet', tracking=True)

    @api.depends('cong_viec_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Phiếu duyệt: {rec.cong_viec_id.name}" if rec.cong_viec_id else "Phiếu duyệt mới"

    def action_dong_y(self):
        """Sếp hoặc trưởng phòng bấm Đồng ý -> Task hoàn thành -> Gọi XML gửi Email Mời đánh giá 5 sao"""
        for rec in self:
            # 1. Phân quyền (Chỉ cấp 1, 2 hoặc Admin mới được duyệt)
            is_sep = self.env.user.has_group('base.group_system')
            nhan_vien_hien_tai = self.env['nhan_vien'].sudo().search([('ho_ten_day_du', '=', self.env.user.name)], limit=1)
            if nhan_vien_hien_tai and nhan_vien_hien_tai.cap_bac in ['1', '2']:
                is_sep = True

            if not is_sep:
                raise exceptions.UserError("🛑 TỪ CHỐI: Bạn không có quyền kiểm duyệt phiếu này!")

            # 2. Cập nhật trạng thái Phiếu và Công việc
            rec.ket_qua_duyet = 'dong_y'
            if rec.cong_viec_id:
                rec.cong_viec_id.trang_thai = 'hoan_thanh' # Đẩy task về Đích
                
                # 3. GỌI TEMPLATE EMAIL (Dùng file XML bạn viết)
                template = self.env.ref('quan_ly_cong_viec.email_template_moi_danh_gia', raise_if_not_found=False)
                
                if template:
                    # Gửi mail đi (gắn với ID của công việc để template móc dữ liệu ra)
                    template.send_mail(rec.cong_viec_id.id, force_send=True)
                    rec.cong_viec_id.message_post(body="✅ <b>Sếp đã phê duyệt!</b> Hệ thống đã tự động chuyển trạng thái Hoàn thành và gửi Email mời đánh giá cho khách hàng.")
                else:
                    rec.cong_viec_id.message_post(body="⚠️ Đã phê duyệt nhưng hệ thống không tìm thấy mẫu Email XML (email_template_moi_danh_gia) để gửi!")

    def action_tu_choi(self):
        """Sếp hoặc trưởng phòng từ chối -> Bắt thợ làm lại"""
        for rec in self:
            if not rec.nhan_xet_cua_sep:
                raise exceptions.ValidationError("🛑 Sếp hoặc trưởng phòng vui lòng ghi rõ 'Nhận xét' lý do từ chối để Kỹ thuật viên biết đường sửa lại!")
            
            rec.ket_qua_duyet = 'tu_choi'
            if rec.cong_viec_id:
                rec.cong_viec_id.trang_thai = 'dang_lam' # Đẩy task ngược lại cho thợ
                rec.cong_viec_id.message_post(body=f"❌ <b>SẾP TỪ CHỐI BÁO CÁO!</b><br/>Lý do: {rec.nhan_xet_cua_sep}")