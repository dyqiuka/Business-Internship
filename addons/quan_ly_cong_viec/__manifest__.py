# -*- coding: utf-8 -*-
{
    'name': "quan_ly_cong_viec",
    'summary': "Module quản lý công việc và Dự án (AI Tích hợp)",
    'description': """
        Module quản lý công việc và các hoạt động tương tác với khách hàng.
        Bao gồm: giao việc, theo dõi dự án, và AI hỗ trợ viết báo cáo.
    """,
    'author': "Duy Nguyen", 
    'website': "http://www.yourcompany.com",
    'category': 'Productivity',
    'version': '0.1',
    
    # ĐÃ THÊM 'mail' VÀO ĐÂY ĐỂ TRÁNH LỖI CHATTER
    'depends': ['base', 'mail', 'nhan_su', 'quan_ly_khach_hang'],
    'data': [
        'security/ir.model.access.csv',
        'views/cong_viec.xml',  # ĐƯA FILE NÀY LÊN TRÊN CÙNG!
        'views/du_an.xml' ,
        'views/kiem_duyet.xml', 
        'views/nhan_vien_extend_view.xml',
        'views/khach_hang_extend_view.xml',
        'views/dashboard_views.xml',
        'views/email_template.xml',    
        
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
}