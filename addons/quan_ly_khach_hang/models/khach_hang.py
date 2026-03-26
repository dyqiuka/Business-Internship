# -*- coding: utf-8 -*-
from odoo import models, fields, api
import unicodedata
import requests
import json

class KhachHang(models.Model):
    _name = 'khach_hang'
    _description = 'Quản lý thông tin khách hàng'
    _rec_name = 'ten_khach_hang'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ma_khach_hang = fields.Char("Mã khách hàng", readonly=True, copy=False)
    ten_khach_hang = fields.Char("Tên khách hàng", required=True, tracking=True)
    loai_khach_hang = fields.Selection([
        ('ca_nhan', 'Cá nhân'),
        ('doanh_nghiep', 'Doanh nghiệp')
    ], string="Loại khách hàng", default='ca_nhan', required=True, tracking=True)
    
    # Thông tin liên hệ
    email = fields.Char("Email", tracking=True)
    so_dien_thoai = fields.Char("Số điện thoại", required=True, tracking=True)
    dia_chi = fields.Text("Địa chỉ")
    ngay_sinh = fields.Date("Ngày sinh")
    
    # Thông tin doanh nghiệp
    ma_so_thue = fields.Char("Mã số thuế")
    website = fields.Char("Website")
    
    trang_thai = fields.Selection([
        ('tiem_nang', 'Tiềm năng'),
        ('da_lien_he', 'Đã liên hệ'),
        ('dang_dam_phan', 'Đang đàm phán'),
        ('thanh_cong', 'Thành công'),
        ('that_bai', 'Thất bại')
    ], string="Trạng thái", default='tiem_nang', tracking=True)
    
    # Liên kết với module quản lý nhân sự & công việc
    nguoi_phu_trach_id = fields.Many2one('nhan_vien', string="Người phụ trách", tracking=True)
    ghi_chu = fields.Text("Ghi chú")

    # MỚI THÊM: Liên kết 1-nhiều để kéo toàn bộ công việc của khách hàng này về

    # ==========================================
    # CÁC TRƯỜNG TÍCH HỢP AI
    # ==========================================
    nhat_ky_tuong_tac = fields.Text(string='Nhật ký tương tác', help='Nhập nội dung trao đổi để AI phân tích')
    
    phan_tich_cam_xuc = fields.Selection([
        ('tich_cuc', 'Tích cực 🟢'),
        ('trung_tinh', 'Trung tính ⚪'),
        ('tieu_cuc', 'Tiêu cực 🔴')
    ], string='AI Đánh giá thái độ', readonly=True, tracking=True)

    is_blacklist = fields.Boolean(string='Blacklist ⛔', tracking=True)

    # ==========================================
    # LOGIC XỬ LÝ
    # ==========================================
    def _remove_accents(self, text):
        """Bỏ dấu tiếng Việt"""
        if not text: return ""
        text = text.replace('Đ', 'D').replace('đ', 'd')
        text = unicodedata.normalize('NFD', text)
        text = text.encode('ascii', 'ignore').decode('utf-8')
        return text
    
    @api.onchange('ten_khach_hang')
    def _onchange_ma_khach_hang(self):
        """Hiển thị preview mã khách hàng khi nhập tên"""
        if self.ten_khach_hang:
            ten_khong_dau = self._remove_accents(self.ten_khach_hang)
            ma_co_ban = ''.join([word[0].upper() for word in ten_khong_dau.split()])
            ma_co_ban = 'KH' + ma_co_ban
            
            counter = 1
            ma_khach_hang = f"{ma_co_ban}{counter:02d}"
            while self.search_count([('ma_khach_hang', '=', ma_khach_hang)]):
                counter += 1
                ma_khach_hang = f"{ma_co_ban}{counter:02d}"
            
            self.ma_khach_hang = ma_khach_hang
    
    @api.model
    def create(self, vals):
        if vals.get('ten_khach_hang'):
            ten_khong_dau = self._remove_accents(vals['ten_khach_hang'])
            ma_co_ban = ''.join([word[0].upper() for word in ten_khong_dau.split()])
            ma_co_ban = 'KH' + ma_co_ban
            
            counter = 1
            ma_khach_hang = f"{ma_co_ban}{counter:02d}"
            while self.search_count([('ma_khach_hang', '=', ma_khach_hang)]):
                counter += 1
                ma_khach_hang = f"{ma_co_ban}{counter:02d}"
            
            vals['ma_khach_hang'] = ma_khach_hang
        
        records = super(KhachHang, self).create(vals)
        records._add_birthday_campaign_if_today()
        return records

    def write(self, vals):
        res = super(KhachHang, self).write(vals)
        self._add_birthday_campaign_if_today()
        return res

    # ==========================================
    # HÀM GỌI AI: PHÂN TÍCH CẢM XÚC & BLACKLIST
    # ==========================================
    def action_ai_phan_tich(self):
        """Nút bấm để kích hoạt AI đọc nhật ký"""
        api_key = "".strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        for rec in self:
            if not rec.nhat_ky_tuong_tac:
                continue

            prompt = f"""
            Đọc đoạn nhật ký tương tác sau của khách hàng: "{rec.nhat_ky_tuong_tac}"
            Nhiệm vụ:
            1. Phân tích cảm xúc: Trả về chính xác 1 trong 3 từ khóa: 'tich_cuc', 'trung_tinh', hoặc 'tieu_cuc'.
            2. Kiểm tra blacklist: Trả về true nếu khách hàng có lời lẽ lăng mạ, đe dọa, bom hàng, lừa đảo. Trả về false nếu bình thường.
            
            Định dạng trả về BẮT BUỘC là JSON hợp lệ: {{"cam_xuc": "tieu_cuc", "blacklist": true}}
            Chỉ in ra JSON, không giải thích.
            """

            data = {"contents": [{"parts": [{"text": prompt}]}]}

            try:
                response = requests.post(url, headers=headers, json=data, timeout=15)
                if response.status_code == 200:
                    result = response.json()
                    text_response = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Dọn dẹp markdown code block
                    text_response = text_response.replace('```json', '').replace('```', '').strip()
                    parsed_data = json.loads(text_response)
                    
                    rec.phan_tich_cam_xuc = parsed_data.get('cam_xuc', 'trung_tinh')
                    rec.is_blacklist = parsed_data.get('blacklist', False)
                    
                    # ĐÃ SỬA: Dịch chữ True/False thành câu từ dễ hiểu để in ra log
                    blacklist_text = "⛔ CÓ DẤU HIỆU LỪA ĐẢO/PHÁ HOẠI!" if rec.is_blacklist else "✅ Khách hàng an toàn."
                    cam_xuc_dict = {'tich_cuc': '🟢 Tích cực', 'trung_tinh': '⚪ Bình thường', 'tieu_cuc': '🔴 Tiêu cực'}
                    cam_xuc_text = cam_xuc_dict.get(rec.phan_tich_cam_xuc, '⚪ Không rõ')

                    rec.message_post(body=f"""
                        <b>🤖 BÁO CÁO AI PHÂN TÍCH:</b><br/>
                        - Thái độ khách hàng: {cam_xuc_text}<br/>
                        - Cảnh báo Blacklist: <b>{blacklist_text}</b>
                    """)
                else:
                    rec.message_post(body=f"🤖 <b>Lỗi Google:</b> {response.text}")
            except Exception as e:
                rec.message_post(body=f"🤖 <b>Lỗi hệ thống:</b> {str(e)}")

    # ==========================================
    # LOGIC CHIẾN DỊCH SINH NHẬT
    # ==========================================
    def _add_birthday_campaign_if_today(self, today=None):
        today = today or fields.Date.context_today(self)
        if not today: return

        birthday_customers = self.filtered(
            lambda c: c.ngay_sinh and (c.ngay_sinh.month, c.ngay_sinh.day) == (today.month, today.day)
        )
        if not birthday_customers: return

        if 'chien_dich' in self.env:
            Campaign = self.env['chien_dich'].sudo()
            for customer in birthday_customers:
                campaign_name = f"Mừng sinh nhật {customer.ten_khach_hang}"
                campaign = Campaign.search([('ten_chien_dich', '=', campaign_name)], limit=1)
                if not campaign:
                    campaign = Campaign.create({
                        'ten_chien_dich': campaign_name,
                        'loai_chien_dich': 'khac',
                        'ngay_bat_dau': today,
                        'trang_thai': 'dang_chay',
                        'muc_tieu': f'Chăm sóc sinh nhật cho {customer.ten_khach_hang}.',
                        'khach_hang_ids': [(6, 0, [customer.id])],
                    })
                else:
                    campaign.write({
                        'khach_hang_ids': [(4, customer.id)],
                    })

    @api.model
    def _cron_add_birthdays_to_campaign(self):
        today = fields.Date.context_today(self)
        if not today: return
        birthday_customers = self.search([('ngay_sinh', '!=', False)])
        birthday_customers._add_birthday_campaign_if_today(today=today)