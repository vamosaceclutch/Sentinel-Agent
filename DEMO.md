# Kịch bản demo 3 phút và danh sách kiểm tra trước khi quay

Câu chuyện: **bị chặn, được vá, được qua.** Một launchpad từ chối vault có lỗi vì điểm audit trên chain thấp,
rồi chấp nhận vault đã sửa vì điểm cao. Không có người duyệt, chính blockchain quyết định.

## Số liệu thật đã có (ngày 20/11/2026)

| Mục | Giá trị |
|---|---|
| VulnerableVault | điểm 16 khi đóng dấu (AI báo 2 critical + 1 high), đã đóng dấu trên Fuji, cổng chặn (`ScoreTooLow`) |
| FixedVault | điểm 100, đã đóng dấu, cổng cho qua (`Safe`) |
| Đóng dấu lên chain | xác nhận sau 2,49 và 2,1 giây, gas 95.188, phí khoảng 1,5e-11 AVAX (testnet Fuji, đã đối chiếu trên Snowtrace) |
| Bản vá AI cho VulnerableVault | điểm 12 lên 65, vẫn dưới ngưỡng 70, nên vẫn bị chặn |
| Benchmark | 8/8 loại lỗi được phát hiện, contract sạch 100 điểm (1 lần chạy mỗi contract) |

## Trước khi quay (làm một lần, rồi tập hai lần có bấm giờ)

1. Backend đang chạy (`python -m uvicorn app:app --reload`), trang web mở ở `http://127.0.0.1:5500/UI.html` (Ctrl+F5).
2. Ví agent còn AVAX testnet. Ví MetaMask của bạn ở mạng Fuji, đúng Account 1.
3. **Dự phòng hạn mức Gemini:** gói miễn phí chỉ có khoảng 20 lượt mỗi model mỗi ngày. Hôm nay bạn đã dùng gần hết. Thêm dòng
   `GEMINI_FALLBACK_MODEL=gemini-3.5-flash` vào file `.env` rồi khởi động lại backend để có model thứ hai. Không dán `.env` ra màn hình hay vào chat.
4. Mở sẵn các tab: (a) giao diện web, (b) Remix với `GuardedLaunchpad` đã nạp bằng **+ Add Contract** (địa chỉ `0x416001B4cbe88352531F41854A8AeBde8Fb0A8bD`),
   (c) Snowtrace trang `AuditGate`, tab Read Contract.
5. Sao chép sẵn hai địa chỉ vault: `VulnerableVault` `0x67F23Ed0410ABc1B6FC6fCE7FEEc9c58ff7C346A`, `FixedVault` `0x9Ba8E1eBb127510E8881440105254955D3bf1691`.
6. **Quay thành từng đoạn riêng** rồi ghép lại, để không phải làm lại cả video khi hỏng một đoạn.
7. Không bao giờ để lộ `.env` hay khóa riêng trên màn hình.

## Kịch bản

| Giờ | Làm gì | Nói gì |
|---|---|---|
| 0:00 | Slide mở đầu (hoặc giao diện web) | "Báo cáo audit bằng AI thường là một file PDF. Smart contract không đọc được PDF. SentinelAgent đưa kết luận lên Avalanche, nơi contract khác đọc được." |
| 0:20 | Giao diện: dán địa chỉ `VulnerableVault`, tick đóng dấu, bấm Audit | "Agent lấy source đã verify, AI tìm lỗi, còn điểm do một công thức cố định tính." |
| 0:50 | Chỉ vào điểm, danh sách lỗi, rồi dòng đóng dấu | "Có hai lỗi critical và một lỗi high. Đóng dấu lên Fuji mất vài giây và phí cực nhỏ, số liệu lấy từ biên lai thật." (đọc số hiển thị trên màn hình) |
| 1:10 | Mục Badge on-chain: "Khớp" và "Bị chặn" | "Trang đọc thẳng chain và tính lại hash của báo cáo. Khớp nghĩa là không ai sửa được điểm. Cổng báo bị chặn vì điểm dưới 70." |
| 1:30 | Remix: `listProject(VulnerableVault)` | "Một launchpad thử niêm yết vault này. Giao dịch bị từ chối với lỗi `NotSafe`, và con số 16 nằm ngay trong dữ liệu lỗi. Không có người nào quyết định." |
| 1:50 | Giao diện: bấm "Đề xuất bản vá bằng AI" (nếu còn lượt) | "AI đề xuất bản vá và tự audit lại: 12 lên 65. Nhưng 65 vẫn dưới ngưỡng, nên cổng vẫn chặn. Bản vá AI chỉ là gợi ý và cần người xem xét." |
| 2:10 | Giao diện: audit `FixedVault` (đã đóng dấu từ trước, hoặc đóng dấu lại), badge "Qua cổng" | "Bản vá viết tay đã bỏ hẳn hàm rút tiền nguy hiểm, được 100 điểm và qua cổng." |
| 2:25 | Remix: `listProject(FixedVault)` thành công, `listedCount` tăng | "Cùng một launchpad, lần này chấp nhận." |
| 2:40 | Snowtrace: Read Contract, `check` với `FixedVault` | "Giám khảo tự kiểm tra được, không cần tin video." |
| 2:50 | Slide giới hạn | "Hiện chỉ một khóa agent ký điểm, AI có thể sai, mới thử trên contract nhỏ. Tiếp theo: nhiều auditor độc lập và đối chiếu với Slither." |

## Nếu có sự cố khi quay

- Gemini báo quá tải (503) hoặc hết lượt (429): chờ tối đa 40 giây, hoặc dùng audit đã đóng dấu từ trước và đọc badge on-chain (không tốn lượt).
- Bản vá AI chưa đủ tốt: nói thẳng, đó chính là thông điệp "bản vá AI cần người xem xét".
- Nếu audit lại `VulnerableVault` mà không đóng dấu, badge sẽ báo "Không khớp" vì báo cáo mới khác báo cáo đã đóng dấu. Đó là hành vi đúng, nhưng tránh để xuất hiện trong video.
- Điểm có thể khác một chút giữa các lần (ví dụ 16 hoặc 12): AI có thể đổi mức nghiêm trọng, công thức thì cố định.
