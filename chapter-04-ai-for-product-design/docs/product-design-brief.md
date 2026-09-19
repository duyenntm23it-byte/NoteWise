# NoteWise Product Design Brief

## 1. Tổng quan

NoteWise là web app học tập cá nhân hóa cho môn **AI Product Development End-to-End**. Người học tải lên tài liệu bài giảng PDF hoặc PPTX, sau đó dùng AI để chuyển nội dung dài thành các hoạt động học có cấu trúc: đọc tóm tắt, hỏi đáp theo ngữ cảnh, luyện quiz và nhận diện chủ đề còn yếu.

Mục tiêu thiết kế là biến một kho tài liệu tĩnh thành một không gian học tập có định hướng. Mọi câu trả lời của AI cần gắn với nguồn trích dẫn theo trang hoặc slide để người học có thể kiểm chứng, đồng thời sản phẩm phải cho thấy rõ trạng thái xử lý của tài liệu.

## 2. Đối tượng người dùng

- **Sinh viên tự học:** cần nắm nhanh bài giảng trước giờ học hoặc ôn thi.
- **Người học bận rộn:** muốn biết phần nào quan trọng thay vì đọc lại toàn bộ tài liệu.
- **Người học cần củng cố:** muốn đặt câu hỏi tự nhiên, luyện tập nhiều lần và nhìn thấy lỗ hổng kiến thức.

Người dùng có khả năng sử dụng các ứng dụng web phổ biến nhưng không nên phải hiểu RAG, embeddings hay pipeline AI để hoàn thành tác vụ học tập.

## 3. Tính năng cốt lõi

### 3.1. Tóm tắt AI

Sau khi tài liệu được xử lý, NoteWise tạo bản tóm tắt theo cấu trúc gồm ý chính, khái niệm, ví dụ và điểm cần nhớ. Người học có thể đi từ dashboard tới tài liệu gần đây, xem mức độ xử lý và mở phần tóm tắt mà không phải tìm kiếm thủ công.

### 3.2. Q&A bài giảng

Màn hình đọc tài liệu chia đôi không gian: vùng xem nội dung ở bên trái và trợ lý hỏi đáp ở bên phải. Câu trả lời hiển thị ngắn gọn, theo ngữ cảnh tài liệu hiện tại, kèm thẻ trích dẫn trang/slide có thể mở lại để đối chiếu.

### 3.3. Quiz AI

AI tạo bộ câu hỏi từ tài liệu hoặc một chủ đề cụ thể. Người học chọn số lượng và độ khó, làm bài tương tác, nhận phản hồi sau từng câu hoặc sau cả lượt làm bài, rồi xem điểm số cùng giải thích dựa trên nguồn tài liệu.

### 3.4. Analytics chủ đề yếu

NoteWise tổng hợp kết quả quiz và hoạt động hỏi đáp thành các chủ đề cần củng cố. Analytics ưu tiên hành động tiếp theo: xem lại trang liên quan, hỏi AI về khái niệm hoặc làm quiz ngắn theo chủ đề yếu.

## 4. Nguyên tắc thiết kế UI/UX

1. **Tối giản và tập trung:** một màn hình có một hành động chính rõ ràng; giảm trang trí không hỗ trợ việc học.
2. **Ưu tiên khả năng quét:** phân cấp typography rõ, khoảng trắng vừa đủ, nhãn trạng thái dễ nhận biết.
3. **Minh bạch với AI:** luôn hiển thị trạng thái `Đang xử lý`, `Sẵn sàng`, `Trống` hoặc `Có lỗi`; câu trả lời có citation và không trình bày suy đoán như sự thật.
4. **Điều hướng theo tiến trình:** dashboard trả lời được ba câu hỏi: đang học gì, đã tiến bộ ra sao, tiếp theo nên làm gì.
5. **Tương tác có thể phục hồi:** giữ lại câu hỏi, cho phép thử lại khi lỗi, không làm mất đáp án hoặc tiến độ quiz.
6. **Khả năng tiếp cận:** màu chữ đạt tương phản tốt, trạng thái không chỉ được biểu đạt bằng màu, vùng bấm đủ lớn và luồng dùng được bằng bàn phím.
7. **Responsive thực dụng:** màn hình đọc chuyển từ chia đôi sang tab hoặc xếp dọc trên viewport hẹp; nội dung tài liệu vẫn là trung tâm.

## 5. Tiêu chí thành công

- Người dùng mới hiểu được cách bắt đầu học trong lần truy cập đầu tiên.
- Từ một tài liệu đã tải, người dùng có thể đi tới tóm tắt, Q&A và quiz trong tối đa ba tương tác chính.
- Mọi câu trả lời kiến thức đều có nguồn trích dẫn hiển thị rõ.
- Analytics dẫn tới một hành động học cụ thể thay vì chỉ hiển thị biểu đồ.
