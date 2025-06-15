# GIAI ĐOẠN 1: "BUILDER" - Môi trường để biên dịch các thư viện
# Giai đoạn này sẽ cài đặt các công cụ cần thiết để build tgcrypto
FROM python:3.11-slim AS builder

# Cài đặt các gói hệ thống cần thiết cho việc biên dịch (gcc, python headers, etc.)
RUN apt-get update && apt-get install -y build-essential

# Tạo một virtual environment để quản lý các gói đã cài đặt
RUN python -m venv /opt/venv

# Kích hoạt virtual environment và cài đặt các thư viện Python
# Điều này đảm bảo các gói được biên dịch đúng cách
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# GIAI ĐOẠN 2: "FINAL" - Môi trường chạy ứng dụng cuối cùng
# Giai đoạn này tạo ra image cuối cùng, sạch sẽ và nhẹ, không chứa build-essential
FROM python:3.11-slim

# Đặt thư mục làm việc
WORKDIR /app

# Sao chép các thư viện đã được cài đặt ở virtual environment từ giai đoạn "builder" sang
COPY --from=builder /opt/venv /opt/venv

# Sao chép code của ứng dụng vào
COPY . .

# Kích hoạt virtual environment cho các lệnh tiếp theo
ENV PATH="/opt/venv/bin:$PATH"

# Lệnh mặc định để chạy khi container khởi động
CMD ["python3", "forward_bot.py"]
