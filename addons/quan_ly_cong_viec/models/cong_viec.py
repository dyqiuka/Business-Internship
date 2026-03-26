# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import requests
import re
import json

class CongViec(models.Model):
    _name = 'cong_viec'
    _description = 'Quản lý Công việc & AI'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ================= 1. CÁC TRƯỜNG DỮ LIỆU CƠ BẢN =================
    name = fields.Char(string="Tên Công việc / Hạng mục", required=True, tracking=True)
    mo_ta_loi = fields.Text(string="Mô tả lỗi (Từ KH)") 
    
    khach_hang_id = fields.Many2one('khach_hang', string="Khách hàng")
    du_an_id = fields.Many2one('du_an', string="Dự án")
    tuong_tac_id = fields.Many2one('tuong_tac', string="Nguồn tương tác KH", readonly=True)
    nguoi_thuc_hien_id = fields.Many2one(
        'nhan_vien', 
        string="Người thực hiện", 
        tracking=True,
        domain="[('trang_thai_lam_viec', '!=', 'nghi_phep')]",
        ondelete='restrict'
    )
    
    # [ĐÃ THAY ĐỔI]: Tạo liên kết 1-Nhiều sang bảng Phiếu kiểm duyệt
    phieu_duyet_ids = fields.One2many('phieu_kiem_duyet', 'cong_viec_id', string="Lịch sử Phiếu duyệt")
    
    han_chot = fields.Date(string="Hạn chót", tracking=True)
    do_uu_tien = fields.Selection([
        ('0', 'Thấp'), ('1', 'Trung bình'), ('2', 'Cao'), ('3', 'Rất cao')
    ], string='Độ ưu tiên', default='1', tracking=True)
    
    trang_thai = fields.Selection([
        ('moi', 'Mới tạo'),
        ('dang_lam', 'Đang xử lý'),
        ('cho_duyet', 'Chờ duyệt'),
        ('hoan_thanh', 'Hoàn thành')
    ], string="Trạng thái", default='moi', tracking=True)

    goi_bao_hanh_id = fields.Many2one('goi_bao_hanh', string="Gói bảo hành")
    so_tien_thu = fields.Float(string="Số tiền thu (VNĐ)")
    ghi_chu_tho = fields.Text(string="Ghi chú nhân viên")
    # BỔ SUNG 2 TRƯỜNG NÀY VÀO FILE PYTHON
    diem_danh_gia = fields.Selection([
        ('0', 'Chưa đánh giá'),
        ('1', '⭐ Rất Tệ'),
        ('2', '⭐⭐ Kém'),
        ('3', '⭐⭐⭐ Bình thường'),
        ('4', '⭐⭐⭐⭐ Hài lòng'),
        ('5', '⭐⭐⭐⭐⭐ Tuyệt vời')
    ], string="Điểm đánh giá", default='0', tracking=True)
    
    nhan_xet_khach_hang = fields.Text(string="Nhận xét từ Khách hàng", tracking=True)

    # ================= 2. HÀM KIỂM TRA & TIỆN ÍCH =================
    @api.constrains('nguoi_thuc_hien_id')
    def _check_trang_thai_nhan_vien(self):
        for rec in self:
            if rec.nguoi_thuc_hien_id and rec.nguoi_thuc_hien_id.trang_thai_lam_viec == 'nghi_phep':
                raise exceptions.ValidationError(
                    f"🛑 TỪ CHỐI GIAO VIỆC!\nNhân viên '{rec.nguoi_thuc_hien_id.ho_ten_day_du}' đang NGHỈ PHÉP. "
                )

    def _mask_pii_data(self, text):
        if not text: return ""
        masked_text = re.sub(r'\b(0[3|5|7|8|9])+([0-9]{8})\b', '[SĐT_BẢO_MẬT]', text)
        if self.khach_hang_id:
            ten_khach = getattr(self.khach_hang_id, 'ten_khach_hang', self.khach_hang_id.display_name)
            if ten_khach and ten_khach in masked_text:
                masked_text = masked_text.replace(ten_khach, '[TÊN_KHÁCH_HÀNG]')
        return masked_text

    def _call_gemini_api(self, prompt_text, task_name):
        api_key = "AIzaSyDdvkp-XovmC2HzKlIXZ2cbuHz5j7O1i4I".strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        prompt = f"""
        Bạn là Kỹ thuật viên trưởng. Viết báo cáo nghiệm thu kỹ thuật ngắn gọn:
        - Tên hạng mục: {task_name}
        - Ghi chú thực tế của thợ: '{prompt_text}'
        Yêu cầu BẮT BUỘC:
        1. Tuyệt đối không viết văn hoa. 
        2. Nếu thợ báo không sửa, phải giải thích kỹ thuật.
        3. Định dạng hoàn toàn bằng HTML (dùng <b>, <p>, <ul>, <li>).
        """
        try:
            response = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            if response.status_code == 200:
                html_content = response.json()['candidates'][0]['content']['parts'][0]['text']
                return html_content.replace('```html', '').replace('```', '').strip()
            return f"<p style='color:red;'><b>🤖 Lỗi API:</b> {response.text}</p>"
        except Exception as e:
            return f"<p style='color:red;'><b>🤖 Lỗi Internet:</b> {str(e)}</p>"

    # ================= 3. CÁC NÚT BẤM (ACTION) =================
    def action_ai_tim_tho(self):
        """Hàm AI: Đọc nội dung việc và chọn đúng THỢ KỸ THUẬT"""
        api_key = "AIzaSyDdvkp-XovmC2HzKlIXZ2cbuHz5j7O1i4I".strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        for rec in self:
            if rec.nguoi_thuc_hien_id:
                raise exceptions.UserError("Công việc này đã có người đảm nhận!")

            # 1. Tìm nhân viên đang sẵn sàng
            danh_sach_tho = self.env['nhan_vien'].sudo().search([('trang_thai_lam_viec', '=', 'san_sang')])
            if not danh_sach_tho:
                raise exceptions.UserError("Hiện tại không có nhân viên nào sẵn sàng!")

            # 2. Chuẩn bị dữ liệu: Ép Odoo phải gửi kèm Chức vụ / Phòng ban cho AI
            info_tho = ""
            for tho in danh_sach_tho:
                # Cố gắng lấy chức vụ hoặc tên phòng ban (tùy theo bạn đang dùng trường nào trong bảng Nhân viên)
                vi_tri = getattr(tho, 'chuc_vu', '') or getattr(tho.phong_ban_id, 'name', 'Nhân viên')
                info_tho += f"- ID: {tho.id}, Tên: {tho.ho_ten_day_du}, Vị trí/Chuyên môn: {vi_tri}\n"

            # 3. Prompt xịn xò dặn dò AI cực kỳ cẩn thận
            # 3. SIÊU PROMPT: Ép AI trở thành Giám đốc Điều phối Nhân sự
            prompt = f"""
            Nhiệm vụ: Bạn là Giám đốc Điều phối Nhân sự cấp cao. Hãy phân tích nội dung yêu cầu của khách hàng và chọn ra 1 nhân viên phù hợp nhất để xử lý.
            
            THÔNG TIN YÊU CẦU:
            - Tên hạng mục: "{rec.name}"
            - Mô tả chi tiết: "{rec.mo_ta_loi}"
            
            DANH SÁCH NHÂN SỰ ĐANG SẴN SÀNG:
            {info_tho}
            
            HỆ THỐNG QUY TẮC PHÂN VIỆC BẮT BUỘC (Đọc kỹ và áp dụng chặt chẽ):
            
            1. PHÂN TÍCH CHUYÊN MÔN THEO TÌNH HUỐNG (Từ khóa & Ngữ cảnh):
               * NHÓM KỸ THUẬT / BẢO TRÌ:
                 - Dấu hiệu: Khách báo hỏng hóc, máy kêu to, rò rỉ, không lên nguồn, đứt dây, lỗi hệ thống, yêu cầu lắp đặt, sửa chữa, bảo dưỡng định kỳ, thay thế linh kiện, khảo sát kỹ thuật.
                 - Hành động: BẮT BUỘC chọn nhân viên có chuyên môn "Kỹ thuật", "Kỹ thuật viên", "Bảo trì".
               
               * NHÓM CHĂM SÓC KHÁCH HÀNG (CSKH):
                 - Dấu hiệu: Khách hỏi cách sử dụng, không biết thao tác, phàn nàn về thái độ nhân viên, khiếu nại dịch vụ, yêu cầu giải thích chính sách bảo hành, hoặc nội dung yêu cầu quá chung chung (chưa rõ bị gì cần gọi lại để hỏi thêm).
                 - Hành động: BẮT BUỘC chọn chuyên môn "Chăm sóc khách hàng", "CSKH".
               
               * NHÓM TƯ VẤN / SALE:
                 - Dấu hiệu: Khách xin bảng báo giá, hỏi giá tiền, muốn mua thêm gói bảo hành, muốn nâng cấp máy mới, hỏi về chương trình khuyến mãi, muốn ký hợp đồng.
                 - Hành động: BẮT BUỘC chọn chuyên môn "Tư vấn", "Sale", "Bán hàng".
                 
               * NHÓM LOGISTICS / VẬN CHUYỂN:
                 - Dấu hiệu: Khách giục giao hàng, hỏi bao giờ thợ đến nơi, sai địa chỉ, nhầm hàng, trả máy móc về kho, theo dõi đơn hàng.
                 - Hành động: BẮT BUỘC chọn chuyên môn "Logistics", "Vận chuyển", "Điều phối".
                 
               * NHÓM TÀI CHÍNH / KẾ TOÁN (Nếu trong danh sách có):
                 - Dấu hiệu: Khách yêu cầu xuất hóa đơn đỏ (VAT), khiếu nại sai lệch số tiền thanh toán, yêu cầu hoàn tiền, lỗi chuyển khoản.
                 - Hành động: BẮT BUỘC chọn chuyên môn "Tài chính", "Kế toán".

            2. QUY TẮC CÂN BẰNG TẢI (LOAD BALANCING) - BẮT BUỘC ÁP DỤNG SAU KHI LỌC CHUYÊN MÔN:
               - Sau khi tìm được nhóm nhân sự đúng chuyên môn ở Bước 1, BẠN PHẢI so sánh số lượng công việc "Đang làm" của họ.
               - ƯU TIÊN SỐ 1: Chốt ngay người đang có "0 việc" (Đang hoàn toàn rảnh rỗi).
               - Nếu tất cả người đúng chuyên môn đều đang có việc, PHẢI CHỌN người có số lượng việc ÍT NHẤT.
               - TUYỆT ĐỐI KHÔNG giao thêm việc cho người đang ôm nhiều việc nhất trong nhóm chuyên môn đó.

            3. XỬ LÝ TÌNH HUỐNG CHỒNG CHÉO (EDGE CASES):
               - Nếu nội dung vừa chửi mắng (khiếu nại) vừa đòi hoàn tiền -> Ưu tiên giao cho "Chăm sóc khách hàng" để xoa dịu trước.
               - Nếu nội dung vừa hỏi giá vừa báo lỗi máy -> Ưu tiên giao cho "Kỹ thuật" đi kiểm tra tình trạng hỏng hóc trước rồi mới báo giá.
               - Nếu danh sách KHÔNG CÓ AI đúng chuyên môn -> Chọn người rảnh nhất (0 việc) của bộ phận "Chăm sóc khách hàng" hoặc "Tư vấn" để họ tiếp nhận và xử lý tạm thời.

            ĐỊNH DẠNG TRẢ VỀ:
            - Chỉ trả về ĐÚNG 1 ĐOẠN JSON duy nhất, tuyệt đối không in ra markdown (```json), không có câu chào hỏi hay văn bản nào khác.
            - Định dạng chuẩn: {{"id_chon": <ID dạng số>, "ly_do": "<Viết 1 câu giải thích logic: Tại sao ngữ cảnh này cần chuyên môn đó, và tại sao chọn người này dựa trên số việc đang làm>"}}
            """
            try:
                response = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
                if response.status_code == 200:
                    result = response.json()
                    text_res = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Bộ lọc Regex siêu mạnh để moi bằng được chuỗi JSON ra (tránh lỗi ngớ ngẩn của AI)
                    match = re.search(r'\{.*\}', text_res.replace('\n', ''), re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                        id_duoc_chon = data.get('id_chon')
                        ly_do = data.get('ly_do', 'AI đề xuất.')

                        if id_duoc_chon:
                            # Kiểm tra xem ID AI chọn có thực sự tồn tại trong danh sách không
                            if int(id_duoc_chon) in danh_sach_tho.ids:
                                rec.nguoi_thuc_hien_id = id_duoc_chon
                                rec.trang_thai = 'dang_lam'
                                rec.message_post(body=f"🤖 <b>AI Phân Việc:</b> Đã chọn đúng người <b>{rec.nguoi_thuc_hien_id.ho_ten_day_du}</b>.<br/>💡 Lý do AI: {ly_do}")
                            else:
                                rec.message_post(body="⚠️ AI bị ngáo, chọn ID không tồn tại. Yêu cầu phân việc lại bằng tay.")
                        else:
                            rec.message_post(body="⚠️ AI không chốt được ID nào. Vui lòng phân việc bằng tay.")
                    else:
                        rec.message_post(body=f"⚠️ Lỗi định dạng AI trả về: {text_res}")
                else:
                    raise exceptions.UserError(f"Lỗi kết nối AI: {response.text}")
            except Exception as e:
                # Xóa cái trò "tự động gán cho người đầu tiên" đi để tránh giao nhầm cho Tư vấn viên
                rec.message_post(body=f"❌ <b>Sự cố AI:</b> {str(e)}.<br/>Hệ thống đã HỦY lệnh phân việc tự động để tránh giao nhầm cho Tư vấn viên. Sếp vui lòng chọn tay!")
    
    def action_ai_viet_bao_cao(self):
        """AI phân tích, tự tạo Phiếu, và CHỜ DUYỆT (Không tự động duyệt nữa)"""
        for rec in self:
            if not rec.ghi_chu_tho:
                raise exceptions.UserError("Kỹ thuật viên chưa nhập Ghi chú. AI không có dữ liệu để phân tích!")

            safe_note = rec._mask_pii_data(rec.ghi_chu_tho)
            html_content = rec._call_gemini_api(safe_note, rec.name)
            
            # ================= TÌM SẾP DUYỆT (ĐÚNG CHUYÊN MÔN) =================
            nguoi_duyet = False
            tho = rec.nguoi_thuc_hien_id
            phong_ban = tho.phong_ban_id

            # 1. Ưu tiên 1: Lấy đúng Trưởng phòng của phòng ban mà thợ đang làm
            if phong_ban and hasattr(phong_ban, 'truong_phong_id') and phong_ban.truong_phong_id:
                nguoi_duyet = phong_ban.truong_phong_id
            
            # 2. Ưu tiên 2: Nếu chưa gán Trưởng phòng, tìm 1 Quản lý (Cấp 2) CÙNG PHÒNG BAN với thợ
            if not nguoi_duyet and phong_ban:
                nguoi_duyet = self.env['nhan_vien'].sudo().search([
                    ('cap_bac', '=', '2'), 
                    ('phong_ban_id', '=', phong_ban.id)
                ], limit=1)
                
            # 3. Ưu tiên 3: Nếu phòng ban đó đen đủi không có quản lý nào, đẩy lên thẳng Giám Đốc (Cấp 1) duyệt
            if not nguoi_duyet:
                nguoi_duyet = self.env['nhan_vien'].sudo().search([('cap_bac', '=', '1')], limit=1)

            if not nguoi_duyet:
                raise exceptions.UserError("Hệ thống không tìm thấy Quản lý cùng chuyên môn hoặc Giám đốc để duyệt phiếu này!")
            # ===================================================================

            # 🤖 1. TẠO PHIẾU KIỂM DUYỆT MỚI
            phieu_moi = self.env['phieu_kiem_duyet'].sudo().create({
                'cong_viec_id': rec.id,
                'nguoi_duyet_id': nguoi_duyet.id,
                'ai_bao_cao': html_content,
                'ket_qua_duyet': 'cho_duyet'
            })
            
            # 2. CHỈ DỪNG Ở MỨC CHỜ DUYỆT, KHÔNG TỰ ĐỘNG DUYỆT
            rec.trang_thai = 'cho_duyet'
            rec.message_post(body=f"🤖 <b>AI Report:</b> Đã tạo thành công Phiếu kiểm duyệt. Đang chờ Sếp {nguoi_duyet.ho_ten_day_du} vào phê duyệt!")
            
    def write(self, vals):
        # Lưu dữ liệu ở bảng Công Việc như bình thường
        res = super(CongViec, self).write(vals)
        
        # Sau khi lưu xong, kiểm tra xem có thay đổi Tiền hoặc Bảo hành không
        for rec in self:
            if rec.tuong_tac_id and ('goi_bao_hanh_id' in vals or 'so_tien_thu' in vals):
                sync_data = {}
                
                # Nếu thợ đổi gói bảo hành
                if 'goi_bao_hanh_id' in vals:
                    sync_data['goi_bao_hanh_id'] = vals['goi_bao_hanh_id']
                    # Nếu thợ xóa bảo hành đi (chuyển sang thu tiền)
                    if not vals['goi_bao_hanh_id']:
                        sync_data['tu_choi_bao_hanh'] = True
                        
                # Nếu thợ sửa lại số tiền thu
                if 'so_tien_thu' in vals:
                    sync_data['so_tien_thanh_toan'] = vals['so_tien_thu']
                
                # Đẩy ngược dữ liệu về lại bảng Tương tác
                if sync_data:
                    rec.tuong_tac_id.sudo().write(sync_data)
                    
        return res