# -*- coding: utf-8 -*-
{
    'name': "Quản lý Khách hàng & CRM (Tích hợp AI)",

    'summary': """Module quản lý khách hàng tích hợp AI Gemini""",

    'description': """
        Đề tài: Quản lý khách hàng và Quản lý công việc.
        Hệ thống hỗ trợ tự động hóa luồng tương tác, phân tích cảm xúc khách hàng 
        và chuyển hóa nội dung trao đổi thành các đầu việc (Task) cụ thể cho nhân sự.
    """,

    'author': "Bùi Khương Duy",
    'website': "http://www.yourcompany.com",

    'category': 'Sales',
    'version': '1.0',

    # ==========================================
    # FIX LỖI 1 & 2: KHAI BÁO THƯ VIỆN PHỤ THUỘC
    # ==========================================
    # 1. Bắt buộc phải có 'mail' vì tất cả model của ta đều có khung chat (mail.thread)
    # 2. Module nhân sự của bạn tên thư mục là 'quan_ly_nhan_su', phải ghi chính xác tên này!
    # Sửa lại thành 'nhan_su' như thiết kế ban đầu của bạn
    'depends': ['base', 'mail', 'nhan_su'],

    'data': [
        'security/ir.model.access.csv',
         
        
        # ==========================================
        # FIX LỖI 3: DANH SÁCH FILE GIAO DIỆN
        # ==========================================
        'views/khach_hang.xml',
        'views/tuong_tac.xml',
        'views/goi_bao_hanh.xml',
        
        # Menu luôn để cuối cùng
        'views/menu.xml',
    ],

    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}