# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class DanhGiaController(http.Controller):

    # Tạo ra đường link để Gmail trỏ về (Giống như href trong file XML ở trên)
    @http.route('/danh-gia-dich-vu/<int:cong_viec_id>/<int:diem>', type='http', auth='public', website=True)
    def nhan_danh_gia_tu_gmail(self, cong_viec_id, diem, **kwargs):
        # 1. Tìm đúng cái Công việc đó trong Database
        cong_viec = request.env['cong_viec'].sudo().browse(cong_viec_id)
        
        # 2. Kiểm tra xem công việc có tồn tại không
        if cong_viec.exists():
            # 3. Ghi điểm số khách vừa click thẳng vào Database
            cong_viec.sudo().write({
                'diem_danh_gia': str(diem) # Cập nhật trường diem_danh_gia ở bài trước
            })
            
            # Ghi luôn vào lịch sử dưới dạng tin nhắn
            cong_viec.message_post(body=f"💌 <b>Khách hàng vừa click từ Gmail:</b> Đánh giá {diem} sao!")

            # 4. Trả về cho khách 1 câu cảm ơn trên trình duyệt
            return f"""
                <html>
                    <head>
                        <meta charset="utf-8"/>
                        <title>Đánh giá dịch vụ</title>
                    </head>
                    <body style="background-color: #f4f7f6; font-family: Arial, sans-serif; margin: 0; padding: 0;">
                        <div style="max-width: 600px; margin: 100px auto; background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center;">
                            <h1 style="color: #28a745; margin-bottom: 20px;">CẢM ƠN QUÝ KHÁCH! ❤️</h1>
                            
                            <p style="font-size: 16px; color: #333; line-height: 1.5;">
                                Quý khách đã đánh giá <b>{diem} sao</b> cho kỹ thuật viên <b>{cong_viec.nguoi_thuc_hien_id.ho_ten_day_du}</b>.
                            </p>
                            <p style="font-size: 16px; color: #333; line-height: 1.5;">
                                Sự phản hồi của Quý khách giúp chúng tôi không ngừng nâng cao chất lượng dịch vụ.
                            </p>
                            
                            <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;"/>
                            
                            <p style="font-size: 15px; color: #555;">
                                📞 <b>Nếu Quý khách có bất kỳ thắc mắc hoặc cần hỗ trợ thêm, xin vui lòng liên hệ với chúng tôi:</b>
                            </p>
                            <p style="font-size: 15px; color: #0056b3; font-weight: bold;">
                                Hotline: 1900 123456<br/>
                                Email: hotro@congtyodoo.com
                            </p>
                            
                            
                            </a>
                        </div>
                    </body>
                </html>
            """