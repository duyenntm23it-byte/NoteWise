# Chapter 04 Evidence

Thư mục này dùng để lưu ảnh chụp màn hình và ghi nhận kiểm thử UI cho toàn bộ 7 màn hình NoteWise. Các artifact đều nằm trong Chapter 04 và không cần backend/frontend của project.

## Đường dẫn xem artifact

- Prototype 7 màn hình: mở `../prototype/index.html` trực tiếp bằng trình duyệt.
- Auth: mở `../design/concepts/screen-1-auth-concept.html`.
- Materials: mở `../design/concepts/screen-2-materials-concept.html`.
- Q&A split-screen: mở `../design/concepts/screen-3-qa-concept.html`.
- Quiz setup/player: mở `../design/concepts/screen-4-quiz-concept.html`.
- Analytics: mở `../design/concepts/screen-5-analytics-concept.html`.
- Recommendations: mở `../design/concepts/screen-6-recommendations-concept.html`.
- Learning History: mở `../design/concepts/screen-7-history-concept.html`.
- User flow: mở `../design/user-flow.mmd` bằng Mermaid Live Editor hoặc Mermaid extension trong VS Code.

## Cách chụp evidence

1. Mở từng file HTML bằng trình duyệt hiện đại.
2. Chụp viewport desktop và mobile cho các trạng thái chính.
3. Đặt ảnh vào thư mục này, ví dụ `prototype-dashboard-desktop.png` hoặc `materials-error-mobile.png`.
4. Ghi ngày chụp, viewport, trình duyệt và thao tác đã kiểm tra.

| Màn hình        | Trạng thái cần chụp                                        | Ảnh evidence |
| --------------- | ---------------------------------------------------------- | ------------ |
| Auth            | Ready, inline error, password visibility                   | _chưa chụp_  |
| Materials       | Ready, processing, failed/retry, upload                    | _chưa chụp_  |
| Q&A             | Source, summary, citation highlight, insufficient evidence | _chưa chụp_  |
| Quiz            | Setup, player, result                                      | _chưa chụp_  |
| Analytics       | Accuracy chart, weak topic dưới 60%                        | _chưa chụp_  |
| Recommendations | Cards, data-limited banner                                 | _chưa chụp_  |
| History         | Filter, table, detail action                               | _chưa chụp_  |

Prototype dùng HTML/CSS/JS thuần và dữ liệu trong `../prototype/mock-data.js`; không cần build hoặc server riêng để mở thử.
