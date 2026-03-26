# -*- coding: utf-8 -*-
{
    'name': "Quản lý Công việc & Nhân sự (Tích hợp AI)",

    'summary': """Module quản lý nhân sự, dự án, công việc và phân công tự động bằng AI""",

    'description': """
        Đồ án: Hệ thống quản lý toàn diện cho doanh nghiệp.
        - Quản lý Khách hàng, Dự án
        - Quản lý Phòng ban, Nhân viên
        - Theo dõi Công việc, tự động đếm khối lượng công việc
        - Tích hợp Google Gemini AI tự động viết báo cáo và phân công công việc.
    """,

    'author': "Khương Duy Bùi", # Đồ án của bạn thì mạnh dạn để tên mình vào nhé!
    'website': "http://www.yourcompany.com",

    'category': 'Productivity',
    'version': '1.0',

    # Thư viện bắt buộc để hệ thống chạy được
    'depends': ['base', 'mail',],
    # THỨ TỰ CÁC FILE TRONG DATA CỰC KỲ QUAN TRỌNG:
    # 1. File phân quyền luôn đứng đầu
    # 2. File giao diện (Model nào không phụ thuộc thì load trước)
    # 3. File menu.xml BẮT BUỘC phải đứng CUỐI CÙNG
    'data': [
        'security/ir.model.access.csv',
        'views/nhan_vien.xml',
        'views/phong_ban.xml',
        'views/danh_gia_kpi.xml',
        'views/menu.xml', 
    ],
    
    
    'installable': True,
    'application': True, # Khai báo là True để nó hiện to đùng ngoài App Odoo
}