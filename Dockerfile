# Bước 1: Chọn một môi trường gốc (base image) ổn định
# Chúng ta dùng Python 3.11 phiên bản "slim" để nhẹ và hiệu quả
FROM python:3.11-slim

# Bước 2: Đặt thư mục làm việc bên trong container
WORKDIR /app

# Bước 3: Sao chép file requirements.txt vào trước
# Tận dụng cơ chế cache của Docker: nếu file này không đổi, Docker sẽ không cần cài lại thư viện
COPY requirements.txt .

# Bước 4: Cài đặt các thư viện Python đã liệt kê
# --no-cache-dir giúp giảm kích thước của image cuối cùng
RUN pip install --no-cache-dir -r requirements.txt

# Bước 5: Sao chép toàn bộ code của bạn vào container
COPY . .

# Bước 6: Lệnh mặc định để chạy khi container khởi động
CMD ["python3", "forward_bot.py"]
