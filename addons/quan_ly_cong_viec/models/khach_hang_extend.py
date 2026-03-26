# -*- coding: utf-8 -*-
from odoo import models, fields

class KhachHangExtend(models.Model):
    # Tìm đến bảng khach_hang gốc để cấy thêm dữ liệu
    _inherit = 'khach_hang'

    # Bơm thêm trường công việc từ module này sang
    cong_viec_ids = fields.One2many('cong_viec', 'khach_hang_id', string="Danh sách Công việc")