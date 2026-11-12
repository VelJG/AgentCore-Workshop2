# Kịch bản thuyết trình — AI Enterprise IT Helpdesk (30 phút)

> Phần trong ngoặc vuông là thao tác, không đọc thành lời. Giữ sẵn chat UI, AWS diagram và CloudFormation Console trước khi bắt đầu. Chỉ dùng dữ liệu giả lập; không đưa API key hoặc dữ liệu nội bộ thật lên màn hình.

## 0:00–2:00 — Mở đầu

“Khi đưa AI vào doanh nghiệp, gọi được một mô hình để trả lời câu hỏi mới chỉ là bước đầu. Hệ thống còn phải biết lấy thông tin từ đâu, được phép làm gì, hành động nào cần con người duyệt, và vận hành ra sao.

Hôm nay mình sẽ trình bày một trợ lý hỗ trợ IT. Trợ lý có ba nhiệm vụ: trả lời câu hỏi từ policy nội bộ, đề xuất tạo ticket, và tìm thông tin bên ngoài trên web. Mình sẽ demo hệ thống chạy thật trước, sau đó mở kiến trúc phía sau, rồi chuyển sang phương án hạ tầng AWS.”

**Câu dẫn vào demo:**

“Thông điệp chính là: *mô hình có thể đề xuất hành động, nhưng hệ thống mới quyết định hành động đó có được thực hiện hay không*.”

## 2:00–10:00 — Demo ba agent trên local

### Q&A Agent — khoảng 2 phút

[Mở http://127.0.0.1:8000/. Chọn câu hỏi mẫu về trạng thái phiếu.]

“Đầu tiên là một câu hỏi về quy trình IT: ‘Phiếu hỗ trợ mới có trạng thái gì?’ Hệ thống định tuyến câu này sang **Q&A Agent**. Agent không chỉ dựa vào kiến thức có sẵn của model; nó tra kho policy của mình và đưa thông tin tìm được vào ngữ cảnh trước khi trả lời.

Ở câu trả lời, mọi người có thể thấy nhãn agent và nguồn tri thức. Đây là phần mình muốn nhấn mạnh: với thông tin nội bộ, câu trả lời phải có căn cứ từ tài liệu của tổ chức.”

[Chỉ vào nhãn Q&A Agent và nguồn. Model thật có thể diễn đạt khác giữa các lượt; không hứa một câu trả lời cố định.]

### Ticket Agent — khoảng 3 phút

[Nhập: “Hãy tạo phiếu hỗ trợ cho lỗi đăng nhập VPN.”]

“Bây giờ mình chuyển từ *hỏi thông tin* sang *yêu cầu hành động*. Router chuyển yêu cầu sang **Ticket Agent**. Agent tạo ra một bản nháp ticket, nhưng tại thời điểm này **chưa có ticket nghiệp vụ nào được tạo**.

Hệ thống hiển thị bước phê duyệt. Mình sẽ thử từ chối trước.”

[Bấm **Từ chối**.]

“Yêu cầu này dừng ở đây. Model không có quyền bỏ qua quyết định của người dùng để tự ghi ticket.”

[Nhập lại yêu cầu tạo ticket; lần này bấm **Phê duyệt**.]

“Lần này mình duyệt. Sau quyết định rõ ràng từ người dùng, ứng dụng mới ghi nhận ticket và trả về mã phiếu, với trạng thái xử lý **Pending**. Phần kiểm soát này nằm ở API và policy của ứng dụng, không nằm trong một lời hứa của prompt.

Cùng một quyết định phê duyệt được thiết kế để không tạo ticket trùng khi gửi lại. Đó là một yêu cầu vận hành quan trọng khi đưa agent vào workflow doanh nghiệp.”

### Research Agent — khoảng 3 phút

[Chọn câu hỏi mẫu: “Tìm trên web hướng dẫn bảo mật VPN mới nhất và dẫn nguồn.” Đợi phản hồi.]

“Nhánh thứ ba là **Research Agent**. Khác Q&A Agent chỉ dùng kho policy nội bộ, agent này được phép tìm web bên ngoài qua Tavily. Kết quả có các đường dẫn nguồn bấm được để mình kiểm tra lại.

Mình tách hai nhánh này vì *policy nội bộ* và *thông tin công khai trên Internet* có độ tin cậy và mục đích sử dụng khác nhau. Kết quả web là thông tin tham khảo, **không tự động trở thành policy của công ty**. Nội dung từ website cũng được xem là dữ liệu không tin cậy, không phải chỉ dẫn mà agent phải tuân theo.”

[Chỉ một citation. Không nhập dữ liệu khách hàng, mật khẩu hoặc thông tin nội bộ thật vào ô tìm web.]

“Vậy qua ba lượt vừa rồi, mọi người đã thấy cùng một giao diện nhưng ba trách nhiệm khác nhau: **trả lời — đề xuất hành động — nghiên cứu bên ngoài**.”

## 10:00–12:00 — Kiến trúc local nhìn từ trên xuống

[Chuyển sang sơ đồ local.]

“Giờ mình mở phần phía sau demo. Luồng bắt đầu ở chat UI, đi vào FastAPI. FastAPI gọi một graph của LangGraph. Trong graph có một **router** dùng model để chọn một trong ba nhánh Q&A, Ticket hoặc Research. Mỗi lượt chỉ đi qua nhánh phù hợp, không gọi cả ba agent.

Kết quả trả lại UI sẽ cho biết agent nào đã xử lý. Riêng nhánh Ticket còn đi qua approval và lưu trạng thái trong SQLite. Log của mỗi request có mã yêu cầu để mình theo dõi khi có lỗi.”

“Đây là multi-agent ở mức **các vai trò chuyên biệt, prompt và quyền công cụ khác nhau**. Nó không có nghĩa là mình đang chạy ba model provider khác nhau, và cũng không phải ba agent tự do trao đổi vô hạn với nhau.”

## 12:00–14:00 — LangGraph và điều phối

“LangGraph giúp mình biểu diễn luồng xử lý thành các node và đường chuyển tiếp rõ ràng. Node đầu tiên phân loại ý định. Nếu là câu hỏi policy thì chuyển sang Q&A; nếu người dùng yêu cầu tạo phiếu thì sang Ticket; nếu cần thông tin bên ngoài thì sang Research.

Lợi ích ở đây không phải làm cho sơ đồ phức tạp hơn. Lợi ích là mình nhìn được **ai chịu trách nhiệm cho bước nào**, công cụ nào được dùng ở nhánh nào, và chỗ nào phải chặn hành động. Nhánh Research thể hiện rõ vòng **ReAct**: agent quyết định gọi `SearchWeb`, Tavily trả kết quả, rồi agent đọc kết quả để trả lời. Vòng này chỉ cho phép một lượt tìm, không chạy vô hạn. Research không có quyền tạo ticket; Ticket có thể soạn `TicketDraft` nhưng không có quyền tự phê duyệt.”

## 14:00–18:00 — RAG và indexing

[Chỉ luồng Q&A trên sơ đồ.]

“Q&A Agent sử dụng RAG — *Retrieval-Augmented Generation*. Mình tách quá trình này thành hai thời điểm.

**Thứ nhất là indexing khi ứng dụng khởi động.** Hiện kho tri thức mẫu có ba mục ngắn về trạng thái ticket, VPN và mật khẩu. Ứng dụng lấy nội dung các mục này, gọi embedding model `text-embedding-3-small` để biến văn bản thành vector, rồi đưa các vector vào chỉ mục FAISS trong RAM.

**Thứ hai là lúc người dùng đặt câu hỏi.** Câu hỏi cũng được biến thành vector. FAISS tìm tối đa hai mục gần nhất; nội dung tìm được được đưa vào prompt làm context cho Q&A Agent. Sau đó chat model mới tạo câu trả lời bằng tiếng Việt. UI hiển thị ID nguồn để mình biết câu trả lời dựa vào mục nào.”

[Ngừng một nhịp để khán giả phân biệt indexing và querying.]

“Điểm tối ưu nhỏ nhưng quan trọng: mình **không embed lại toàn bộ kho tài liệu ở mỗi câu hỏi**. Chỉ mục được tạo khi khởi động; mỗi lượt hỏi chỉ cần embed câu truy vấn.”

**Nói rõ giới hạn:**

“Đây là RAG quy mô nhỏ để thể hiện đúng luồng kỹ thuật. Hiện chưa có pipeline nạp và chia đoạn tài liệu lớn; kho chỉ có ba mục. Việc tìm kiếm lấy top-2 nhưng chưa có ngưỡng loại kết quả kém liên quan. Nếu mở rộng thành hệ thống thực tế, mình sẽ bổ sung ingest tài liệu, versioning, đánh giá chất lượng retrieval và phân quyền theo tài liệu.”

## 18:00–21:00 — Tools, approval và các yêu cầu doanh nghiệp

“Với Ticket Agent, `TicketDraft` là một tool tạo **bản nháp**, không phải tool ghi thẳng vào database. API giữ yêu cầu chờ duyệt; quyết định phê duyệt được kiểm tra rồi mới làm ticket xuất hiện. Như vậy mình không đặt toàn bộ an toàn nghiệp vụ lên prompt của model.

Research Agent dùng `SearchWeb` gọi Tavily Search, sau đó model tổng hợp từ tối đa ba kết quả đã giới hạn độ dài. Tavily Search tiêu thụ credits; nguồn web được hiển thị thành link để người xem kiểm chứng. Nội dung web được coi là dữ liệu không tin cậy.”

“Nếu nhìn theo bốn trụ cột doanh nghiệp:

- **Bảo mật:** không nhập dữ liệu thật; quyền công cụ tách theo agent; ticket cần duyệt.
- **Tin cậy:** có health check, mã request, lỗi provider được báo rõ và bước duyệt chống tạo trùng.
- **Mở rộng:** bản local dùng SQLite và chỉ mục FAISS trong RAM; đó là giới hạn cần xử lý trước khi tăng nhiều instance.
- **Chi phí:** mỗi lượt có bước router; Q&A dùng embeddings, Research dùng web search. Vì vậy mình phải đo số lần gọi, latency và chi phí, chứ không chỉ nhìn giá của chat model.”

## 21:00–23:00 — Đối chiếu AgentCore

“Mình dùng AgentCore làm khung để nói về những năng lực cần có khi vận hành agent ở quy mô doanh nghiệp. **Ứng dụng local này không chạy trên AgentCore**; đây là đối chiếu trách nhiệm kiến trúc.

**Runtime:** hiện mình tự chạy FastAPI và LangGraph.  
**Identity:** app có cơ chế presenter token tùy chọn, nhưng chưa có định danh người dùng doanh nghiệp.  
**Gateway:** hiện công cụ được tích hợp trực tiếp và giới hạn theo từng nhánh; chưa dùng AgentCore Gateway.  
**Policy:** bước phê duyệt ticket hiện là logic ứng dụng, chưa phải AgentCore Policy.  
**Memory:** SQLite giữ trạng thái approval và ticket — đây là *dữ liệu nghiệp vụ*, không phải bộ nhớ hội thoại của AgentCore.  
**Observability:** hiện có request ID và log; chưa có tracing managed đầy đủ.  
**Evaluations:** có test cho luồng nghiệp vụ; chưa phải hệ thống đánh giá chất lượng model ở quy mô production.

Sự phân biệt này quan trọng: dùng một framework agent và chạy được demo **không đồng nghĩa** đã có đầy đủ lớp vận hành enterprise.”

## 23:00–26:00 — AWS architecture diagram

[Chuyển sang AWS diagram V3, đi theo luồng từ trái sang phải.]

“Sau local, đây là **kiến trúc AWS mục tiêu**, chưa phải lời khẳng định app vừa demo đã được đưa lên cloud.

Người dùng đi vào qua Internet Gateway và Application Load Balancer ở public subnets. Ứng dụng dự kiến chạy bằng ECS trên Fargate trong private subnets, trải trên hai Availability Zones. Image được lưu ở ECR. Secrets Manager giữ secret, IAM giới hạn quyền, CloudWatch thu log. Hai bảng DynamoDB là mô hình dữ liệu mục tiêu cho ticket và approval — không phải dữ liệu SQLite local đã được chuyển lên.

Private subnet cần đường đi ra ngoài thì dùng NAT Gateway. Với sơ đồ hai AZ, mỗi NAT Gateway public có một EIP; CloudFormation cũng có lựa chọn một NAT để giảm chi phí, đổi lại giảm khả năng chịu lỗi theo AZ.

Bedrock xuất hiện trong kiến trúc mục tiêu và IAM có quyền gọi model, nhưng **ứng dụng local hiện dùng OpenAI API**. Template này chưa chạy suy luận Bedrock.”

“Điểm cần nói thẳng: ALB trong template hiện chỉ cấu hình **HTTP**; trước khi phục vụ người dùng thật cần HTTPS và thiết kế xác thực phù hợp.”

## 26:00–29:00 — Walkthrough CloudFormation Console

[Chuyển đúng Region Singapore `ap-southeast-1`. Nếu stack đã deploy, mở stack đã chuẩn bị trước. **Không tạo stack live trên sân khấu.**]

“Đây là cách mình biến sơ đồ mục tiêu thành tài nguyên có thể xem được trên AWS. CloudFormation quản lý các resource như VPC, subnets, routes, NAT/EIP, ALB, ECS, ECR, DynamoDB, IAM và CloudWatch trong một stack.”

[Ở tab **Events**.]

“Events cho biết thứ tự tạo tài nguyên và là nơi mình xem đầu tiên nếu triển khai lỗi.”

[Ở tab **Resources**; chỉ vài mục đại diện, không đọc toàn bộ danh sách.]

“Đây là VPC và các subnet theo AZ; đây là NAT Gateway và EIP; đây là ALB, ECS cluster/service, ECR và các bảng DynamoDB. Mình có thể đối chiếu từng resource với diagram vừa rồi.”

[Ở **Parameters** và **Outputs**.]

“Parameters thể hiện lựa chọn như một hay hai NAT và cấu hình budget. Outputs trả các ID, tên và endpoint để kiểm tra hạ tầng. Budget là cảnh báo chi phí, **không phải nút tự động chặn chi tiêu**.”

**Chốt ranh giới triển khai:**

“ECS Service của template đang đặt `DesiredCount = 0`, ECR chưa có image ứng dụng để chạy. Vì vậy mình **không mở ALB để giả vờ đây là chat app trên AWS**. Phần Console chứng minh hạ tầng mục tiêu và Infrastructure as Code; phần chat live vừa rồi đang chạy local.”

[Nếu chưa có stack hoặc Console gặp lỗi: chỉ template và diagram, nói rõ chưa tạo resource; không nói rằng AWS app đã chạy.]

## 29:00–30:00 — Kết luận

“Từ demo này, mình muốn mọi người nhớ ba lớp.

Một là **năng lực AI**: router, các agent chuyên biệt, RAG và web research.  
Hai là **kiểm soát nghiệp vụ**: nguồn thông tin rõ ràng, giới hạn công cụ và con người phê duyệt hành động ghi dữ liệu.  
Ba là **vận hành**: identity, logging, đánh giá, mở rộng và chi phí — được thể hiện qua cách mình đối chiếu AgentCore và thiết kế AWS mục tiêu.

Tóm lại, AI trong doanh nghiệp không chỉ là model trả lời hay. Nó là một workflow mà mình có thể **kiểm soát, giải thích và vận hành**.”

## Ghi chú dự phòng (không đọc)

- Thử đủ ba câu hỏi demo trước giờ trình bày; model thật có thể chọn nhánh hoặc diễn đạt khác nhau.
- Nếu Research lỗi hoặc không trả citation, không nói đã tìm web thành công; chuyển sang giải thích kiến trúc và kiểm tra log sau.
- Nếu AWS stack chưa có `CREATE_COMPLETE`, chỉ walkthrough template/diagram. Không deploy tài nguyên tốn phí ngay trên sân khấu.
- Local đang dùng OpenAI API, SQLite và FAISS trong RAM; CloudFormation hiện chỉ là hạ tầng AWS mục tiêu.

## Tài liệu tham khảo

- [Amazon Bedrock AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
- [OpenAI Web Search Guide](https://developers.openai.com/api/docs/guides/tools-web-search)
