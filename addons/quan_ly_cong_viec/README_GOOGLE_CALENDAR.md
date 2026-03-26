# Tích hợp Google Calendar cho Module Quản lý Công việc

## Tổng quan
Module này đã được tích hợp với Google Calendar để tự động đồng bộ các công việc lên Google Calendar của người dùng.

## Tính năng

### 1. Tự động đồng bộ
- Khi tạo công việc mới với ngày bắt đầu, tự động tạo event trong Google Calendar
- Khi cập nhật công việc (tiêu đề, thời gian, mô tả), tự động cập nhật event
- Khi xóa công việc, tự động xóa event tương ứng

### 2. Thông tin đồng bộ
- **Ngày bắt đầu**: Thời gian bắt đầu của event
- **Ngày hoàn thành**: Thời gian kết thúc của event
- **Tiêu đề**: Hiển thị dưới dạng `[Mã công việc] Tiêu đề`
- **Mô tả**: Bao gồm thông tin chi tiết về công việc

### 3. Màu sắc theo mức độ ưu tiên
- **Khẩn cấp**: Đỏ
- **Cao**: Xanh dương đậm
- **Trung bình**: Vàng
- **Thấp**: Xanh lá

### 4. Nhắc nhở
- Email: 1 ngày trước
- Popup: 30 phút trước

## Cấu hình

### Bước 1: Cài đặt module Google Calendar
```bash
# Module google_calendar đã được thêm vào dependencies
# Đảm bảo module google_calendar được cài đặt trong hệ thống Odoo
```

### Bước 2: Cấu hình Google Calendar API

1. **Tạo Google Cloud Project**
   - Truy cập https://console.cloud.google.com/
   - Tạo project mới hoặc chọn project có sẵn

2. **Enable Google Calendar API**
   - Vào "APIs & Services" > "Library"
   - Tìm "Google Calendar API"
   - Click "Enable"

3. **Tạo OAuth 2.0 Credentials**
   - Vào "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Chọn "Web application"
   - Thêm Authorized redirect URIs:
     ```
     https://your-odoo-domain/google_account/authentication
     ```

4. **Cấu hình trong Odoo**
   - Vào Settings > General Settings
   - Tìm phần "Google Calendar"
   - Nhập Client ID và Client Secret từ Google Cloud Console
   - Click "Save"

### Bước 3: Kết nối Google Calendar cho User

1. **Cấp quyền Google Calendar**
   - Vào Settings > Users & Companies > Users
   - Chọn user cần kết nối
   - Vào tab "Preferences"
   - Tìm phần "Google Calendar" và click "Connect to Google"
   - Đăng nhập tài khoản Google và cấp quyền

2. **Kiểm tra kết nối**
   - Sau khi authorize, trạng thái sẽ hiển thị "Connected"
   - User này có thể đồng bộ công việc với Google Calendar

## Sử dụng

### Tạo công việc mới
1. Tạo công việc như bình thường
2. Đảm bảo checkbox "Đồng bộ với Google Calendar" được bật (mặc định là bật)
3. Nhập ngày bắt đầu (bắt buộc để đồng bộ)
4. Nhập ngày hoàn thành (tùy chọn, nếu không có sẽ dùng ngày bắt đầu)
5. Lưu công việc

Event sẽ tự động được tạo trong Google Calendar của user hiện tại.

### Cập nhật công việc
1. Chỉnh sửa công việc (tiêu đề, ngày bắt đầu, ngày hoàn thành, mô tả)
2. Lưu thay đổi

Event trong Google Calendar sẽ tự động được cập nhật.

### Đồng bộ thủ công
1. Mở công việc
2. Click button "Đồng bộ Google Calendar" trong header
3. Hệ thống sẽ đồng bộ và hiển thị thông báo thành công

### Tắt đồng bộ
1. Bỏ checkbox "Đồng bộ với Google Calendar"
2. Lưu công việc

Các thay đổi sau này sẽ không được đồng bộ lên Google Calendar.

## Các trường mới

### Model: cong_viec
- `google_calendar_event_id` (Char): ID của event trong Google Calendar
- `sync_to_google_calendar` (Boolean): Bật/tắt đồng bộ với Google Calendar
- `last_sync_date` (Datetime): Thời gian đồng bộ gần nhất

## Lưu ý

### Yêu cầu
- User phải được authorize Google Calendar trước khi có thể đồng bộ
- Công việc phải có ngày bắt đầu để có thể đồng bộ
- Module `google_calendar` phải được cài đặt

### Giới hạn
- Mỗi user chỉ đồng bộ với Google Calendar của chính họ
- Chỉ user đã authorize mới có thể tạo/cập nhật event
- Nếu xóa event trực tiếp trong Google Calendar, công việc trong Odoo vẫn tồn tại

### Xử lý lỗi
- Nếu không kết nối được Google Calendar, hệ thống sẽ ghi log warning
- Công việc vẫn được tạo/cập nhật bình thường trong Odoo
- Kiểm tra log để xem chi tiết lỗi

## Troubleshooting

### Không thể đồng bộ
1. Kiểm tra user đã authorize Google Calendar chưa
2. Kiểm tra module google_calendar đã được cài đặt
3. Kiểm tra Google Calendar API credentials
4. Xem log file để biết chi tiết lỗi

### Event bị trung lặp
1. Xóa event cũ trong Google Calendar
2. Click button "Đồng bộ Google Calendar" để tạo lại

### Thay đổi không được cập nhật
1. Kiểm tra checkbox "Đồng bộ với Google Calendar" có được bật
2. Click button "Đồng bộ Google Calendar" để đồng bộ thủ công
3. Kiểm tra log file

## API Methods

### Public Methods
- `action_sync_google_calendar()`: Đồng bộ thủ công với Google Calendar
- `_sync_google_calendar_event()`: Tự động đồng bộ (được gọi từ create/write)
- `_prepare_google_event_data()`: Chuẩn bị dữ liệu event
- `_create_google_event()`: Tạo event mới
- `_update_google_event()`: Cập nhật event
- `_get_google_calendar_service()`: Lấy Google Calendar service

## Support
Liên hệ: pnguyen
Email: [your-email]
