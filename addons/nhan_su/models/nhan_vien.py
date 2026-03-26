# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import unicodedata
import requests

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ma_dinh_danh = fields.Char("Mã định danh", readonly=True, copy=False, tracking=True)
    ho_ten_dem = fields.Char("Họ và tên đệm", required=True, tracking=True)
    ten = fields.Char("Tên", required=True, tracking=True)
    ho_ten_day_du = fields.Char("Họ tên đầy đủ", compute="_compute_ho_ten_day_du", store=True)
    chuc_vu = fields.Char("Chức danh (Hiển thị)")
    
    cap_bac = fields.Selection([
        ('1', 'Mức 1 - Sếp / Giám đốc'),
        ('2', 'Mức 2 - Quản lý / Trưởng phòng'),
        ('3', 'Mức 3 - Nhân viên')
    ], string="Cấp bậc (Phân quyền)", default='3', required=True, tracking=True)

    ngay_sinh = fields.Date("Ngày sinh")
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    gioi_tinh = fields.Selection([
        ('nam', 'Nam'),
        ('nu', 'Nữ'),
        ('khac', 'Khác')
    ], string="Giới tính")
    so_dien_thoai = fields.Char("Số điện thoại")
    phong_ban_id = fields.Many2one('phong_ban', string="Phòng ban")

    chuyen_mon = fields.Selection([
        ('ky_thuat', 'Kỹ thuật viên'),
        ('tu_van', 'Tư vấn / Sale'),
        ('bao_tri', 'Bảo trì'),
        ('logistics', 'Logistics'),
        ('cskh', 'Chăm sóc khách hàng')
    ], string="Chuyên môn chính", required=True, tracking=True)
    
    trang_thai_lam_viec = fields.Selection([
        ('san_sang', 'Sẵn sàng'),
        ('dang_ban', 'Đang bận'),
        ('nghi_phep', 'Nghỉ phép')
    ], string="Trạng thái", default='san_sang', tracking=True)

    so_viec_dang_lam = fields.Integer(string="Số việc đang ôm", compute='_compute_so_viec')
    ai_danh_gia_nang_luc = fields.Html(string="🤖 AI Đánh giá Năng lực", readonly=True)

    # ================= CÁC TRƯỜNG MỚI ĐỂ LẤY ĐÁNH GIÁ TỪ KHÁCH =================
    
    @api.depends('cong_viec_ids.diem_danh_gia')
    def _compute_diem_trung_binh(self):
        """Hàm tự động quét qua các công việc đã làm để tính điểm phẩy môn Chăm sóc khách hàng"""
        for rec in self:
            # Lọc ra những công việc đã được đánh giá (chữ khác '0' và không rỗng)
            cac_viec_da_danh_gia = rec.cong_viec_ids.filtered(lambda t: t.diem_danh_gia and t.diem_danh_gia != '0')
            
            if cac_viec_da_danh_gia:
                # Ép kiểu điểm (chuỗi) sang số nguyên và tính tổng
                tong_diem = sum(int(t.diem_danh_gia) for t in cac_viec_da_danh_gia)
                # Chia trung bình và làm tròn 2 chữ số thập phân
                rec.diem_trung_binh = round(tong_diem / len(cac_viec_da_danh_gia), 2)
            else:
                rec.diem_trung_binh = 0.0

    # =========================================================================

    def _compute_so_viec(self):
        """Đếm việc và TỰ ĐỘNG CẬP NHẬT TRẠNG THÁI (Trừ người đang nghỉ phép)"""
        for rec in self:
            real_id = rec._origin.id if rec._origin else False
            
            if real_id:
                count = self.env['cong_viec'].sudo().search_count([
                    ('nguoi_thuc_hien_id', '=', real_id),
                    ('trang_thai', 'in', ['moi', 'dang_lam'])
                ])
                rec.so_viec_dang_lam = count

                if rec.trang_thai_lam_viec != 'nghi_phep':
                    new_status = 'dang_ban' if count > 0 else 'san_sang'
                    if rec.trang_thai_lam_viec != new_status:
                        rec.sudo().write({'trang_thai_lam_viec': new_status})
            else:
                rec.so_viec_dang_lam = 0

    @api.depends('ho_ten_dem', 'ten')
    def _compute_ho_ten_day_du(self):
        for record in self:
            ho_ten_dem = record.ho_ten_dem or ''
            ten = record.ten or ''
            record.ho_ten_day_du = f"{ho_ten_dem} {ten}".strip()

    def name_get(self):
        result = []
        for record in self:
            chuyen_mon_val = dict(self._fields['chuyen_mon'].selection).get(record.chuyen_mon, '')
            name = f"[{record.ma_dinh_danh}] {record.ho_ten_day_du} - {chuyen_mon_val}"
            result.append((record.id, name))
        return result

    def _remove_accents(self, text):
        if not text: return ""
        text = text.replace('Đ', 'D').replace('đ', 'd')
        text = unicodedata.normalize('NFD', text)
        return text.encode('ascii', 'ignore').decode('utf-8')

    @api.model
    def create(self, vals):
        if vals.get('ho_ten_dem') and vals.get('ten'):
            ho_ten_dem_khong_dau = self._remove_accents(vals['ho_ten_dem'])
            ten_khong_dau = self._remove_accents(vals['ten'])
            ma_co_ban = ''.join([w[0].upper() for w in ho_ten_dem_khong_dau.split()]) + ''.join([w[0].upper() for w in ten_khong_dau.split()])
            
            counter = 1
            ma_dinh_danh = f"{ma_co_ban}{counter:02d}"
            while self.search_count([('ma_dinh_danh', '=', ma_dinh_danh)]):
                counter += 1
                ma_dinh_danh = f"{ma_co_ban}{counter:02d}"
            vals['ma_dinh_danh'] = ma_dinh_danh
        return super(NhanVien, self).create(vals)

    def action_sieu_duyet_cong_viec(self):
        """Nút bấm duyệt dành cho Mức 1 và Mức 2"""
        for rec in self:
            if rec.cap_bac not in ['1', '2'] and not self.env.user.has_group('base.group_system'):
                raise exceptions.UserError("🛑 TỪ CHỐI: Tính năng này dành cho Cấp bậc 1 hoặc 2!")

            tasks_cho_duyet = self.env['cong_viec'].sudo().search([('trang_thai', '=', 'cho_duyet')])
            if not tasks_cho_duyet:
                raise exceptions.UserError("Không có báo cáo nào đang chờ duyệt!")

            for task in tasks_cho_duyet:
                task.action_phe_duyet_va_gui()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '🎉 THÀNH CÔNG!',
                    'message': f'Đã duyệt {len(tasks_cho_duyet)} công việc.',
                    'type': 'success',
                }
            }

    def action_ai_danh_gia_nang_luc(self):
        """Gọi Gemini API để đánh giá nhanh năng lực của nhân viên"""
        api_key = "".strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        for rec in self:
            chuyen_mon_text = dict(self._fields['chuyen_mon'].selection).get(rec.chuyen_mon, 'Chưa rõ')
            cap_bac_text = dict(self._fields['cap_bac'].selection).get(rec.cap_bac, 'Chưa rõ')
            trang_thai_text = dict(self._fields['trang_thai_lam_viec'].selection).get(rec.trang_thai_lam_viec, 'Chưa rõ')
            diem_tb = rec.diem_trung_binh

            prompt = f"""
            Bạn là một Giám đốc Nhân sự vui tính. Hãy nhận xét ngắn gọn (khoảng 3 câu) về nhân viên này:
            - Tên: {rec.ho_ten_day_du}
            - Chuyên môn chính: {chuyen_mon_text}
            - Cấp bậc: {cap_bac_text}
            - Trạng thái hiện tại: {trang_thai_text}
            - Số việc đang ôm cùng lúc: {rec.so_viec_dang_lam}
            - Điểm đánh giá trung bình từ Khách hàng: {diem_tb} / 5.0 sao

            Yêu cầu BẮT BUỘC: 
            - Trả kết quả bằng mã HTML (dùng <p>, <b>, <i>, <span style='color:blue'>).
            - Nếu đang ôm > 5 việc: Hãy khen ngợi sự chăm chỉ nhưng nhắc nhở cẩn thận burn-out.
            - Nếu ôm 0 việc mà trạng thái "Sẵn sàng": Hãy nhắc nhở quản lý giao việc ngay.
            - Nếu đang "Nghỉ phép": Hãy chúc họ có kỳ nghỉ vui vẻ.
            - Nhận xét thêm thái độ phục vụ: Nếu điểm TB < 3.0 thì nhắc nhở thái độ; Nếu điểm TB >= 4.0 thì khen ngợi dịch vụ xuất sắc. (Nếu điểm là 0.0 tức là chưa có khách nào đánh giá).
            """
            try:
                response = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
                if response.status_code == 200:
                    html_content = response.json()['candidates'][0]['content']['parts'][0]['text']
                    rec.ai_danh_gia_nang_luc = html_content.replace('```html', '').replace('```', '').strip()
                else:
                    rec.ai_danh_gia_nang_luc = f"<p style='color:red;'><b>🤖 Lỗi API:</b> {response.text}</p>"
            except Exception as e:
                rec.ai_danh_gia_nang_luc = f"<p style='color:red;'><b>🤖 Lỗi kết nối:</b> {str(e)}</p>"