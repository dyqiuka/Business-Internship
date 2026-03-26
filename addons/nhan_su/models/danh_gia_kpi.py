# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import requests
import json

class DanhGiaKPI(models.Model):
    _name = 'danh_gia_kpi'
    _description = 'Đánh giá KPI Nhân sự bằng AI'
    _rec_name = 'name'

    name = fields.Char(string="Kỳ đánh giá", required=True, default="Đánh giá Tháng 03/2026")
    
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên cần đánh giá", required=True)
    ngay_danh_gia = fields.Date(string="Ngày chốt KPI", default=fields.Date.context_today)

    # Các trường Compute (Bỏ store=True để luôn cập nhật Real-time)
    so_task_hoan_thanh = fields.Integer(string="✅ Công việc Hoàn thành", compute='_compute_thong_ke')
    so_task_tre_han = fields.Integer(string="⚠️ Công việc Trễ hạn", compute='_compute_thong_ke')
    chi_tiet_cong_viec = fields.Text(string="Danh sách công việc chi tiết", compute='_compute_thong_ke')

    # --- KHỐI AI TRẢ KẾT QUẢ ---
    ai_nhan_xet = fields.Html(string="🤖 AI Đánh giá & Đề xuất", readonly=True)

    @api.depends('nhan_vien_id')
    def _compute_thong_ke(self):
        """Hàm tự động quét công việc của nhân viên vừa được chọn"""
        for rec in self:
            # 1. NGUYÊN TẮC VÀNG: Gán giá trị mặc định ngay lập tức để diệt tận gốc lỗi CacheMiss
            rec.so_task_hoan_thanh = 0
            rec.so_task_tre_han = 0
            rec.chi_tiet_cong_viec = "Vui lòng chọn nhân viên để xem thống kê..."
            
            # 2. Xử lý tính toán khi đã chọn nhân viên
            if rec.nhan_vien_id:
                # Lấy ID thật (chống lỗi NewId khi chưa bấm Lưu)
                nv_id = rec.nhan_vien_id._origin.id if hasattr(rec.nhan_vien_id, '_origin') and rec.nhan_vien_id._origin else rec.nhan_vien_id.id
                
                if nv_id:
                    # Sudo() để lấy quyền cao nhất, đọc toàn bộ task của nhân viên
                    tasks = self.env['cong_viec'].sudo().search([('nguoi_thuc_hien_id', '=', nv_id)])
                    
                    # Đếm task hoàn thành
                    hoan_thanh_tasks = tasks.filtered(lambda t: t.trang_thai == 'hoan_thanh')
                    rec.so_task_hoan_thanh = len(hoan_thanh_tasks)
                    
                    # Đếm task trễ hạn (so sánh với ngày hôm nay)
                    today = fields.Date.context_today(rec)
                    tre_han_tasks = tasks.filtered(lambda t: t.trang_thai != 'hoan_thanh' and t.han_chot and t.han_chot < today)
                    rec.so_task_tre_han = len(tre_han_tasks)
                    
                    # Gom tên các công việc lại làm mồi (prompt) cho AI
                    chi_tiet = ""
                    for t in tasks:
                        trang_thai_text = "Hoàn thành" if t.trang_thai == 'hoan_thanh' else "Chưa xong / Trễ"
                        chi_tiet += f"- {t.name} (Tình trạng: {trang_thai_text})\n"
                    
                    if chi_tiet:
                        rec.chi_tiet_cong_viec = chi_tiet
                    else:
                        rec.chi_tiet_cong_viec = "Nhân viên này chưa được giao công việc nào trong tháng."

    def action_ai_danh_gia(self):
        """Gọi Gemini API để viết nhận xét cuối tháng"""
        for record in self:
            # [CHỐNG LỖI NEWID]: Ép người dùng phải bấm LƯU trước khi gọi AI
            if not record.id or isinstance(record.id, models.NewId):
                raise exceptions.UserError("🛑 Vui lòng bấm LƯU (Save) bảng đánh giá này trước khi yêu cầu AI phân tích!")

            api_key = "".strip()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}

            prompt = f"""
            Bạn là một Giám đốc Nhân sự (HR Manager) nghiêm khắc nhưng công bằng.
            Hãy viết một bản đánh giá hiệu suất làm việc (KPI) chốt tháng cho nhân viên này.
            
            Dữ liệu thực tế từ hệ thống:
            - Số việc đã hoàn thành: {record.so_task_hoan_thanh}
            - Số việc đang trễ hạn/chưa xong: {record.so_task_tre_han}
            - Chi tiết các việc đã nhận:
            {record.chi_tiet_cong_viec}
            
            Yêu cầu BẮT BUỘC: 
            - Trả kết quả hoàn toàn bằng mã HTML (dùng thẻ <b>, <ul>, <li>, <br>, <span style='color:red/green'>) để giao diện hiển thị đẹp. Không dùng Markdown.
            - Phân bố cục thành 3 phần rõ ràng: 
              1. Nhận xét tổng quan hiệu suất.
              2. Đánh giá Điểm mạnh / Điểm cần khắc phục.
              3. Đề xuất của HR (Thưởng nóng nếu làm tốt, hoặc Phạt/Cảnh cáo nếu trễ hạn nhiều).
            """

            data = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                response = requests.post(url, headers=headers, json=data, timeout=20)
                if response.status_code == 200:
                    result = response.json()
                    text_response = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Xóa các tag rác markdown bọc ngoài HTML nếu có
                    text_response = text_response.replace('```html', '').replace('```', '').strip()
                    record.ai_nhan_xet = text_response
                else:
                    record.ai_nhan_xet = f"<p style='color:red;'>Lỗi từ Google: {response.text}</p>"
            except Exception as e:
                record.ai_nhan_xet = f"<p style='color:red;'>Lỗi kết nối AI: {str(e)}</p>"