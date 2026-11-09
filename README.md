# Trợ lý AI hỗ trợ doanh nghiệp quy mô nhỏ

**Đại học FPT · AI trong doanh nghiệp: Vượt ra ngoài mô hình**

Chạy **chế độ diễn tập** trước: ứng dụng có truy xuất tri thức, luồng LangGraph, kiểm soát phê duyệt và SQLite; phản hồi mô phỏng để buổi demo ổn định. Không cần API key, AWS hay Docker. Cài thư viện lần đầu cần internet.

## Chạy trên Windows

Mở PowerShell tại thư mục này:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m workshop serve
```

Mở terminal thứ hai, cũng tại thư mục này:

```powershell
.\.venv\Scripts\python -m workshop demo
```

Kịch bản sẽ kiểm tra health, trả lời FAQ kèm nguồn, từ chối một yêu cầu tạo phiếu, sau đó duyệt một yêu cầu khác và xác nhận duyệt lại không tạo phiếu trùng.

Có thể thao tác thủ công tại [tài liệu API](http://127.0.0.1:8000/docs). Chỉ sử dụng dữ liệu giả lập; không nhập thông tin khách hàng thật.

## Chạy bằng Docker

Trước tiên dừng máy chủ Python nếu đang dùng cùng cổng.

```powershell
docker compose up --build --wait
.\.venv\Scripts\python -m workshop demo
docker compose logs --tail 25
docker compose down
```

Compose chỉ mở cổng trên máy local và giữ volume dữ liệu sau khi dừng. Đổi cổng bằng `WORKSHOP_LOCAL_PORT`, đồng thời truyền URL tương ứng qua `--url`. Muốn dùng cơ sở dữ liệu sạch, hãy đặt `WORKSHOP_DB` sang một tệp mới.

## Chế độ AI thật (tùy chọn)

Chỉ bật sau khi đã chạy thử chế độ diễn tập và có API key được cấp phép, kèm ngân sách phù hợp. Truy vấn và kho tri thức giả lập sẽ được gửi tới nhà cung cấp mô hình.

1. Cài thêm `requirements-live.txt` vào môi trường ảo.
2. Đặt các biến `WORKSHOP_MODE=live`, `OPENAI_API_KEY`, `WORKSHOP_CHAT_MODEL`, `WORKSHOP_EMBEDDING_MODEL` cho tiến trình máy chủ. Chọn model ID tài khoản được phép dùng; chat model cần hỗ trợ gọi công cụ.
3. Khởi chạy lại cùng máy chủ. FAISS được lập chỉ mục một lần lúc khởi động; mỗi lượt hỏi chỉ cần nhúng truy vấn. Chỉ mục nằm trong RAM và được tạo lại khi khởi động lại. Không nạp chỉ mục đã tuần tự hóa.
4. Câu trả lời và việc chọn công cụ có thể khác nhau. Nếu dịch vụ lỗi, hãy chạy lại ở chế độ `demo`; ứng dụng không âm thầm thay câu trả lời AI thật bằng câu trả lời giả lập.

Image Docker mặc định không cài thư viện AI thật. Có thể tạo image tùy chọn bằng `docker build --build-arg INCLUDE_LIVE=1 .`; cấu hình nhà cung cấp được truyền lúc chạy, không đưa vào image.

## Tài liệu trình bày

- [Kịch bản trình bày 22 phút](docs/presenter.md): sơ đồ, bốn trụ cột và thứ tự đối chiếu AgentCore.
- [Hướng dẫn AWS](docs/aws.md): phương án triển khai tùy chọn; dự án không tự tạo tài nguyên AWS.
- `tests/test_workshop.py`: kiểm thử tình huống có kết quả xác định. Cài `requirements-test.txt`, sau đó chạy `python -m unittest discover -s tests -v` từ thư mục dự án.

