from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

class VanBanDen(models.Model):
    _name = 'van_ban_den'
    _description = 'Quản lý văn bản đến'
    _rec_name = 'ten_van_ban'

    # 1. THÔNG TIN CHUNG
    so_van_ban_den = fields.Char("Số thứ tự (Hệ thống)", required=True, copy=False)
    ten_van_ban = fields.Char("Tên/Trích yếu văn bản", required=True)
    so_hieu_van_ban = fields.Char("Số ký hiệu văn bản gốc", required=True)
    noi_gui_den = fields.Char("Cơ quan ban hành/Nơi gửi")
    ngay_tiep_nhan = fields.Date("Ngày tiếp nhận", default=fields.Date.context_today)

    # 2. LIÊN KẾT DỮ LIỆU
    loai_van_ban_id = fields.Many2one('loai_van_ban', string="Loại văn bản")
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên tiếp nhận/xử lý")

    # 3. TRƯỜNG DỮ LIỆU DÀNH CHO AI
    noi_dung_goc = fields.Text(string="Nội dung toàn văn")
    ai_tom_tat = fields.Text(string="AI Tóm tắt nội dung", readonly=True)

    # 4. HÀM GỌI AI TÓM TẮT
    def action_tom_tat_ai(self):
        for record in self:
            if not record.noi_dung_goc:
                raise UserError("Bạn chưa nhập Nội dung toàn văn. Vui lòng dán nội dung vào trước khi gọi AI!")
            
            # BƯỚC QUAN TRỌNG: Bạn thay API Key của bạn vào dòng dưới này nhé
            api_key = "AIzaSyD6kKArvR_2xCtYypB3C5hnBzu8j2z40-0" 
            
            if api_key == "AIzaSyD6kKArvR_2xCtYypB3C5hnBzu8j2z40-0":
                raise UserError("Bạn chưa cấu hình API Key cho AI. Hãy thay key vào code nhé!")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            prompt = f"Bạn là một trợ lý ảo văn phòng xuất sắc. Hãy tóm tắt văn bản sau thành 3-4 ý chính quan trọng nhất, trình bày bằng các gạch đầu dòng ngắn gọn, dễ hiểu:\n\n{record.noi_dung_goc}"
            
            try:
                # Gọi AI với timeout 10 giây để tránh treo Odoo nếu rớt mạng
                response = requests.post(url, headers={'Content-Type': 'application/json'}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    tom_tat = result['candidates'][0]['content']['parts'][0]['text']
                    record.ai_tom_tat = tom_tat
                else:
                    record.ai_tom_tat = f"Lỗi từ AI: {response.text}"
            except Exception as e:
                record.ai_tom_tat = f"Không thể kết nối tới máy chủ AI. Lỗi: {str(e)}"