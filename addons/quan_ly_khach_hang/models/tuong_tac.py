# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import requests
import json

class TuongTac(models.Model):
    _name = 'tuong_tac'
    _description = 'Lịch sử tương tác và AI phân tích'
    _rec_name = 'tieu_de'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    tieu_de = fields.Char(string="Tiêu đề", required=True, tracking=True)
    
    khach_hang_id = fields.Many2one('khach_hang', string="Khách hàng", required=True, tracking=True)
    khach_hang_phone = fields.Char(related='khach_hang_id.so_dien_thoai', string="Số điện thoại KH", readonly=True)
    khach_hang_email = fields.Char(related='khach_hang_id.email', string="Email KH", readonly=True)

    # ĐÃ XÓA HÀM @api.constrains('khach_hang_id') CẤM ĐOÁN TẠI ĐÂY

    goi_bao_hanh_id = fields.Many2one(
        'goi_bao_hanh', 
        string="Gói bảo hành áp dụng", 
        tracking=True
    )
    
    ngay_ket_thuc_bh = fields.Date(related='goi_bao_hanh_id.ngay_het_han', string="Ngày hết hạn BH", readonly=True)
    
    tu_choi_bao_hanh = fields.Boolean(string="❌ Vô hiệu hóa BH (Do tác động ngoài)", tracking=True)
    so_tien_thanh_toan = fields.Float(string="Số tiền thanh toán (VNĐ)", tracking=True)
    thong_tin_thanh_toan = fields.Char(string="Bảo hành / Thanh toán", compute="_compute_thong_tin_thanh_toan", store=True)

    ngay_tuong_tac = fields.Datetime(string="Thời gian", default=fields.Datetime.now, tracking=True)
    
    loai_tuong_tac = fields.Selection([
        ('call', '📞 Gọi điện tư vấn/báo giá'),
        ('zalo', '💬 Chat Zalo'),
        ('facebook', '🌐 Nhắn tin Facebook'),
        ('meeting', '🤝 Gặp mặt trực tiếp'),
        ('khieu_nai', '🚨 KHIẾU NẠI ')
    ], string="Kênh tương tác", default='call', tracking=True)
    
    noi_dung = fields.Text(string="Nội dung chi tiết (Log chat/Ghi âm)", required=True)
    
    ai_nhan_dien_y_dinh = fields.Char(string="🤖 Ý định khách hàng", readonly=True, tracking=True)
    ai_diem_cam_xuc = fields.Selection([
        ('vui', 'Hài lòng 😊'),
        ('binh_thuong', 'Bình thường 😐'),
        ('tuc_gian', 'Bức xúc 😡')
    ], string="🤖 Cảm xúc", readonly=True, tracking=True)
    ai_de_xuat = fields.Text(string="🤖 AI Đề xuất hành động", readonly=True)

    @api.onchange('khach_hang_id', 'ngay_tuong_tac')
    def _onchange_loc_goi_bao_hanh_va_blacklist(self):
        """Vừa lọc gói bảo hành, vừa cảnh báo ngay nếu chọn khách Blacklist (Chỉ cảnh báo, KHÔNG cấm)"""
        if not self.khach_hang_id:
            return {'domain': {'goi_bao_hanh_id': [('id', '=', False)]}}

        # [TÍNH NĂNG MỚI]: Bắn cảnh báo ngay lập tức nếu là Blacklist NHƯNG VẪN CHO PHÉP CHỌN
        warning_res = {}
        if self.khach_hang_id.is_blacklist:
            warning_res = {
                'warning': {
                    'title': '⛔ CẢNH BÁO KHÁCH HÀNG BLACKLIST',
                    'message': 'Lưu ý: Khách hàng này nằm trong Danh sách đen!\nBạn vẫn có thể ghi nhận tương tác, nhưng hãy cẩn trọng và báo cáo quản lý.'
                }
            }

        # Lấy ngày tương tác làm mốc thời gian
        ngay_moc = self.ngay_tuong_tac.date() if self.ngay_tuong_tac else fields.Date.context_today(self)

        # Nếu đang chọn 1 gói mà đổi ngày làm gói đó bị quá hạn -> Tự động đá nó ra
        if self.goi_bao_hanh_id and self.ngay_ket_thuc_bh and self.ngay_ket_thuc_bh < ngay_moc:
            self.goi_bao_hanh_id = False

        # Chỉ xổ ra những gói có Ngày hết hạn >= Ngày tương tác
        res = {
            'domain': {
                'goi_bao_hanh_id': [
                    ('khach_hang_id', '=', self.khach_hang_id.id),
                    ('ngay_het_han', '>=', ngay_moc)
                ]
            }
        }
        
        # Nếu có cảnh báo Blacklist thì ghép nó vào kết quả trả về
        if warning_res:
            res.update(warning_res)
            
        return res

    @api.depends('goi_bao_hanh_id', 'tu_choi_bao_hanh', 'so_tien_thanh_toan', 'ngay_tuong_tac')
    def _compute_thong_tin_thanh_toan(self):
        for rec in self:
            tien_format = "{:,.0f} VNĐ".format(rec.so_tien_thanh_toan) if rec.so_tien_thanh_toan else "0 VNĐ"
            
            ngay_moc = rec.ngay_tuong_tac.date() if rec.ngay_tuong_tac else fields.Date.context_today(self)
            da_het_han = rec.ngay_ket_thuc_bh and rec.ngay_ket_thuc_bh < ngay_moc
            
            if rec.goi_bao_hanh_id:
                if da_het_han:
                    rec.thong_tin_thanh_toan = f"⏰ ĐÃ HẾT HẠN BH - Tính phí: {tien_format}"
                elif rec.tu_choi_bao_hanh:
                    rec.thong_tin_thanh_toan = f"⚠️ Từ chối BH - Thu: {tien_format}"
                else:
                    rec.thong_tin_thanh_toan = f"🛡️ {rec.goi_bao_hanh_id.name} (Miễn phí)"
            else:
                rec.thong_tin_thanh_toan = f"💰 Tính phí: {tien_format}"

    def action_goi_ai_phan_tich(self):
        api_key = "".strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        for record in self:
            if not record.noi_dung:
                continue
            
            ngay_moc = record.ngay_tuong_tac.date() if record.ngay_tuong_tac else fields.Date.context_today(record)
            da_het_han = record.ngay_ket_thuc_bh and record.ngay_ket_thuc_bh < ngay_moc

            if record.goi_bao_hanh_id:
                if da_het_han:
                    trang_thai_bh = "GÓI BẢO HÀNH ĐÃ HẾT HẠN THEO THỜI GIAN (Bắt buộc báo giá thu phí)"
                elif record.tu_choi_bao_hanh:
                    trang_thai_bh = "BỊ TỪ CHỐI BẢO HÀNH do tác động ngoài (Báo giá thu phí)"
                else:
                    trang_thai_bh = f"CÒN BẢO HÀNH (Gói: {record.goi_bao_hanh_id.name}) - MIỄN PHÍ"
            else:
                trang_thai_bh = "KHÔNG CÓ BẢO HÀNH (Báo giá thu phí)"

            prompt = f"""
            Đọc kỹ nội dung cuộc trao đổi sau giữa nhân viên và khách hàng: "{record.noi_dung}"
            
            Thông tin hệ thống: Khách hàng này hiện tại {trang_thai_bh}.
            
            Nhiệm vụ:
            1. Cảm xúc (cam_xuc): Trả về 'vui', 'binh_thuong', hoặc 'tuc_gian'.
            2. Ý định (y_dinh): Khách hàng thực sự muốn gì? Viết siêu ngắn gọn dưới 10 chữ.
            3. Đề xuất (de_xuat): Dựa vào nội dung và tình trạng bảo hành, đề xuất 1 hành động cụ thể cho nhân viên CSKH.
            
            Định dạng trả về BẮT BUỘC là JSON hợp lệ:
            {{"cam_xuc": "vui", "y_dinh": "Hỏi giá sản phẩm", "de_xuat": "Gửi bảng báo giá"}}
            Chỉ in ra JSON, không giải thích.
            """

            try:
                response = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
                if response.status_code == 200:
                    result = response.json()
                    text_response = result['candidates'][0]['content']['parts'][0]['text']
                    
                    clean_text = text_response.replace('```json', '').replace('```', '').replace('\n', '').strip()
                    
                    try:
                        parsed_data = json.loads(clean_text)
                    except json.JSONDecodeError:
                        record.message_post(body=f"❌ <b>Lỗi AI:</b> AI trả về dữ liệu không đúng chuẩn JSON. Nội dung trả về: {clean_text}")
                        continue
                    
                    record.ai_diem_cam_xuc = parsed_data.get('cam_xuc', 'binh_thuong')
                    record.ai_nhan_dien_y_dinh = parsed_data.get('y_dinh', 'Không rõ')
                    record.ai_de_xuat = "💡 ĐỀ XUẤT TỪ AI: " + parsed_data.get('de_xuat', 'Cần theo dõi thêm')
                    
                    # LOGIC TẠO TASK MỚI
                    ten_kh = record.khach_hang_id.display_name if record.khach_hang_id else "Khách vãng lai"
                    tien_to_bh = f"[{trang_thai_bh}]"
                    
                    if record.loai_tuong_tac != 'call' or record.ai_diem_cam_xuc == 'tuc_gian':
                        
                        if record.ai_diem_cam_xuc == 'tuc_gian' or record.loai_tuong_tac == 'khieu_nai':
                            do_uu_tien = '3'
                            tien_to = "🚨 [KHẨN CẤP]"
                        elif record.loai_tuong_tac == 'meeting':
                            do_uu_tien = '2'
                            tien_to = "🤝 [LỊCH HẸN]"
                        else:
                            do_uu_tien = '1'
                            tien_to = "💬 [MẠNG XÃ HỘI]"
                            
                        task_moi = self.env['cong_viec'].create({
                            'name': f"{tien_to} - {ten_kh}",
                            'khach_hang_id': record.khach_hang_id.id if record.khach_hang_id else False,
                            
                            'goi_bao_hanh_id': record.goi_bao_hanh_id.id if (record.goi_bao_hanh_id and not da_het_han and not record.tu_choi_bao_hanh) else False,
                            
                            'so_tien_thu': record.so_tien_thanh_toan,
                            'mo_ta_loi': f"{tien_to_bh}\nÝ định KH: {record.ai_nhan_dien_y_dinh}\nĐề xuất: {record.ai_de_xuat}\n\nNội dung gốc: {record.noi_dung}",
                            'do_uu_tien': do_uu_tien,
                            'trang_thai': 'moi'
                        })
                        
                        record.message_post(body=f"✅ <b>Thành công:</b> Đã tự động tạo Task cho Thợ ({do_uu_tien} sao). <br/>👉 Mã Task: <a href=# data-oe-model='cong_viec' data-oe-id='{task_moi.id}'>{task_moi.name}</a>")
                        
                    else:
                        record.message_post(body=f"ℹ️ <b>Đã lưu lịch sử:</b> Đây là cuộc gọi tư vấn/báo giá thông thường. Hệ thống KHÔNG tạo Task để tránh rác dữ liệu.")
                        
                else:
                    record.message_post(body=f"❌ <b>Lỗi Google API ({response.status_code}):</b> {response.text}")
            except Exception as e:
                record.message_post(body=f"❌ <b>Lỗi hệ thống:</b> {str(e)}")