# Trợ lý AI hỗ trợ doanh nghiệp quy mô nhỏ

**Đại học FPT · AI trong doanh nghiệp: Vượt ra ngoài mô hình**

Ứng dụng chạy **một chế độ AI thật** với LangGraph router và ba agent: **Q&A** dùng embeddings/FAISS để trả lời policy nội bộ, **Ticket** chỉ đề xuất phiếu để người dùng duyệt trước khi ghi SQLite, **Research** theo vòng ReAct: model chọn `SearchWeb` → Tavily tìm nguồn → model đọc kết quả và trả lời kèm link. Cần OpenAI API key, Tavily API key, internet và ngân sách API; Tavily Search tiêu thụ credits. Chỉ dùng dữ liệu giả lập; câu hỏi và kho tri thức được gửi tới nhà cung cấp model, truy vấn Research còn được gửi tới Tavily.

## Chạy trên Windows

Mở PowerShell tại thư mục này:

```powershell
python -m pip install -r requirements-live.txt
python -m workshop serve
```

Trước khi chạy, điền `OPENAI_API_KEY`, `WORKSHOP_CHAT_MODEL`, `WORKSHOP_EMBEDDING_MODEL` và `TAVILY_API_KEY` vào cấu hình local. Không đưa key vào Git hoặc trình chiếu. Ứng dụng luôn chạy AI thật và dừng với thông báo rõ ràng nếu thiếu cấu hình.

Research có timeout riêng mặc định **120 giây mỗi cuộc gọi ngoài**. Có thể đặt `WORKSHOP_RESEARCH_TIMEOUT_SECONDS` từ 10 đến 300 rồi khởi động lại server; Tavily SDK giới hạn timeout tìm kiếm ở 120 giây. Giá trị này không ảnh hưởng Q&A/Ticket.

Mở terminal thứ hai, cũng tại thư mục này:

```powershell
python -m workshop demo
```

Hoặc mở **[giao diện chat](http://127.0.0.1:8000/)** trên trình duyệt. Chọn câu hỏi mẫu để xem nguồn tri thức, sau đó thử đề xuất tạo phiếu và nhấn **Phê duyệt** hoặc **Từ chối**. Trang chat chỉ phục vụ chế độ local không có token; khi bật `WORKSHOP_HOSTED=1` hoặc đặt `WORKSHOP_TOKEN`, giao diện không được mở để tránh dùng token người trình bày trong trình duyệt.

Để xuất sơ đồ từ **LangGraph đã compile** (không gọi OpenAI/Tavily API), chạy `python -m workshop graph`. Lệnh tạo `graph_visualization.png` tại thư mục dự án; bộ dựng ảnh Mermaid có thể cần internet. Nhánh Research có vòng `research_agent → research_web_tool → research_agent` đúng với lần gọi tool và quan sát kết quả; vòng bị giới hạn một lần tìm. Phê duyệt ticket vẫn do FastAPI xử lý sau khi graph kết thúc, không phải LangGraph interrupt.

Thử câu “Tìm trên web hướng dẫn bảo mật VPN mới nhất và dẫn nguồn” để thấy Research Agent cùng các citation. Router dùng model để chọn một trong ba agent; Research cần thêm lượt model chọn tool, một lượt Tavily Search và một lượt model tổng hợp. Không nhập dữ liệu nội bộ/khách hàng thật vào yêu cầu tìm web.

Lệnh `workshop demo` chạy kịch bản HTTP trên server đang chạy (không chọn chế độ model): health check, FAQ kèm nguồn, từ chối một yêu cầu tạo phiếu, rồi duyệt yêu cầu khác và xác nhận duyệt lại không tạo phiếu trùng. Kịch bản gọi model thật và có thể phát sinh phí API.

Có thể thao tác thủ công tại [tài liệu API](http://127.0.0.1:8000/docs). Chỉ sử dụng dữ liệu giả lập; không nhập thông tin khách hàng thật.

## Chạy bằng Docker

Trước tiên dừng máy chủ Python nếu đang dùng cùng cổng.

```powershell
docker compose up --build --wait
python -m workshop demo
docker compose logs --tail 25
docker compose down
```

Compose chỉ mở cổng trên máy local và giữ volume dữ liệu sau khi dừng. Đổi cổng bằng `WORKSHOP_LOCAL_PORT`, đồng thời truyền URL tương ứng qua `--url`. Muốn dùng cơ sở dữ liệu sạch, hãy đặt `WORKSHOP_DB` sang một tệp mới.

## Cấu hình và vận hành AI thật

Chọn model ID được tài khoản cho phép; chat model cần hỗ trợ gọi công cụ. Không đưa `.env` lên Git hoặc chia sẻ key. Biến môi trường đặt trực tiếp trong tiến trình được ưu tiên hơn `.env`. FAISS lập chỉ mục một lần lúc khởi động; mỗi lượt hỏi embed câu truy vấn và lấy tối đa hai kết quả. Chỉ mục nằm trong RAM và được tạo lại khi khởi động. Lỗi provider hiển thị rõ; ứng dụng không fallback sang phản hồi giả lập.

Docker image luôn có thư viện AI thật; Compose đọc `.env` lúc chạy, không đóng gói key vào image.

## Tài liệu trình bày

- [Kịch bản trình bày 30 phút](docs/presenter.md): sơ đồ, bốn trụ cột và thứ tự đối chiếu AgentCore.
- [Hướng dẫn AWS](docs/aws.md): phương án triển khai tùy chọn; dự án không tự tạo tài nguyên AWS.
- `tests/test_workshop.py`: kiểm thử tình huống có kết quả xác định. Cài `requirements-test.txt`, sau đó chạy `python -m unittest discover -s tests -v` từ thư mục dự án.

