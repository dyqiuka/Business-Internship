from odoo import models, fields, api
import requests
from datetime import date
from odoo.exceptions import ValidationError

class VanBanDi(models.Model):
    _name = 'van_ban_di'
    _description = 'Bảng chứa thông tin văn bản đi'
    _rec_name = 'ten_van_ban'

    so_van_ban_di = fields.Char("Số văn bản đi", required=True) 
    ten_van_ban = fields.Char("Tên văn bản", required=True)
    so_hieu_van_ban = fields.Char("Số hiệu văn bản", required=True)
    noi_nhan = fields.Char("Nơi nhận")

    loai_van_ban_id = fields.Many2one('loai_van_ban', string="Loại văn bản")
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên soạn thảo/gửi")

    # --- 2 TRƯỜNG DÀNH CHO AI ---
    noi_dung_goc = fields.Text(string="Nội dung toàn văn")
    ai_tom_tat = fields.Text(string="AI Tóm tắt", readonly=True)

    def action_tom_tat_ai(self):
        """Hàm gọi API Gemini để tóm tắt văn bản đi"""
        for record in self:
            if not record.noi_dung_goc:
                record.ai_tom_tat = "Vui lòng dán nội dung văn bản gốc vào trước khi gọi AI!"
                continue
            
            # Đã lắp API Key xịn của bạn vào đây
            api_key = "AIzaSyD6kKArvR_2xCtYypB3C5hnBzu8j2z40-0" 
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            prompt = f"Bạn là một trợ lý ảo văn phòng. Hãy đọc văn bản sau và tóm tắt lại thành 3 ý chính ngắn gọn, gạch đầu dòng rõ ràng:\n\n{record.noi_dung_goc}"
            
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            
            try:
                # Gọi AI với giới hạn thời gian 10 giây chống treo server
                response = requests.post(url, headers=headers, json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    tom_tat = result['candidates'][0]['content']['parts'][0]['text']
                    record.ai_tom_tat = tom_tat
                else:
                    record.ai_tom_tat = f"Lỗi gọi AI: {response.text}"
            except Exception as e:
                record.ai_tom_tat = f"Lỗi kết nối mạng: {str(e)}"