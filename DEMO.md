# Kịch bản demo 3 phút và danh sách kiểm tra trước khi quay

Câu chuyện: **bị chặn, được vá, được qua.** Một launchpad từ chối vault có lỗi vì điểm audit trên chain thấp,
rồi chấp nhận vault đã sửa vì điểm cao. Không có người duyệt, chính blockchain quyết định.

## Số liệu thật đã có

| Mục | Giá trị |
|---|---|
| VulnerableVault (lần chạy 21/11, model `gemini-3.8-flash`) | điểm 12, AI báo 3 lỗi critical: `emergencyWithdraw` không có kiểm soát quyền, `setOwner` không có kiểm soát quyền, reentrancy ở `withdraw` |
| VulnerableVault (lần đóng dấu 20/11) | điểm 16; sau khi đóng dấu lại ở lần quay thì điểm mới nhất trên chain là 12 |
| FixedVault | điểm 100, đã đóng dấu, cổng cho qua (`Safe`) |
| Đóng dấu lên chain | xác nhận sau 2,49 và 2,1 giây, gas 95.188 (testnet Fuji) |
| Phí đóng dấu | đọc số hiển thị trên giao diện và đối chiếu với dòng Transaction Fee trên Snowtrace trước khi nói ra; không so sánh với mainnet |
| Bản vá AI cho VulnerableVault | lần trước: điểm 12 lên 65, vẫn dưới ngưỡng 70, nên vẫn bị chặn (đọc đúng số hiện trên màn hình khi quay) |
| Benchmark (model `gemini-3.6-flash`) | 8/8 loại lỗi được phát hiện, contract sạch 100 điểm (1 lần chạy mỗi contract) |

## Trước khi quay (làm một lần, rồi tập một lần có bấm giờ)

1. Hai terminal đang chạy: backend `python -m uvicorn app:app --reload` và web `python -m http.server 5500`. Mở `http://127.0.0.1:5500/UI.html` rồi nhấn Ctrl+F5.
2. `.env` đã đặt `GEMINI_MODEL=gemini-3.8-flash` và `GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite`. Hạn mức free của 3.8 là khoảng 20 lượt mỗi ngày và 5 lượt mỗi phút, nên mỗi đoạn audit chỉ làm một lần và chờ khoảng 15 giây giữa hai thao tác. Không dán `.env` ra màn hình hay vào chat.
3. Ví agent còn AVAX testnet. Ví MetaMask ở mạng Fuji, đúng Account 1.
4. Mở sẵn các tab: (a) giao diện web, (b) Remix với `GuardedLaunchpad` đã nạp bằng **+ Add Contract**
   (địa chỉ `0x416001B4cbe88352531F41854A8AeBde8Fb0A8bD`), (c) Snowtrace trang `AuditGate`, tab Read Contract.
5. Sao chép sẵn hai địa chỉ vault: `VulnerableVault` `0x67F23Ed0410ABc1B6FC6fCE7FEEc9c58ff7C346A`,
   `FixedVault` `0x9Ba8E1eBb127510E8881440105254955D3bf1691`.
6. **Quay thành từng đoạn riêng** rồi ghép lại, để hỏng đoạn nào chỉ quay lại đoạn đó.
7. **Thứ tự quay quan trọng:** quay đoạn audit và đóng dấu VulnerableVault (0:20 đến 1:10) TRƯỚC đoạn Remix (1:30). Lần đóng dấu mới làm điểm mới nhất trên chain thành 12, nên lỗi `NotSafe` trong Remix sẽ ghi 12 và khớp với lời đọc. Nếu audit mà không đóng dấu, badge sẽ báo "Không khớp".
8. Không bao giờ để lộ `.env` hay khóa riêng trên màn hình. Đọc chậm, mỗi đoạn một hơi, nhìn vào màn hình khi chỉ chuột.

## Kịch bản (lời đọc nguyên văn, khoảng 330 chữ)

| Giờ | Làm gì | Nói gì |
|---|---|---|
| 0:00 | Slide mở đầu hoặc giao diện web | "Xin chào ban giám khảo. Báo cáo audit bằng AI thường chỉ là một văn bản, và smart contract thì không đọc được văn bản. SentinelAgent đưa kết luận lên Avalanche, để contract khác đọc được và tự quyết định." |
| 0:20 | Giao diện: dán địa chỉ `VulnerableVault`, tick đóng dấu, bấm Audit | "Mình thử với một vault có lỗi. Agent lấy mã nguồn đã verify, AI tìm lỗi, còn điểm số do một công thức cố định tính." |
| 0:50 | Chỉ vào điểm 12, ba lỗi critical, rồi dòng đóng dấu | "Vault này bị chấm 12 trên 100. AI báo ba lỗi critical: ai cũng rút được tiền, ai cũng đổi được chủ sở hữu, và lỗi reentrancy ở hàm rút. Kết quả được đóng dấu lên Fuji, và đây là thời gian xác nhận, gas đo từ biên lai giao dịch thật." (Chỉ đọc các con số đang hiện trên màn hình.) |
| 1:10 | Mục Badge on-chain: "Khớp" và "Bị chặn" | "Trang này đọc thẳng từ chain và tính lại hash của báo cáo. Khớp nghĩa là báo cáo không bị sửa. Cổng báo bị chặn vì điểm dưới 70." |
| 1:30 | Remix: `listProject(VulnerableVault)` | "Bây giờ một launchpad thử niêm yết vault này. Giao dịch bị từ chối với lỗi NotSafe, và điểm số nằm ngay trong dữ liệu lỗi. Không có ai duyệt tay, blockchain quyết định." |
| 1:50 | Giao diện: "Đề xuất bản vá bằng AI" (chỉ làm nếu còn lượt Gemini) | "AI đề xuất bản vá và tự audit lại, điểm tăng lên, nhưng vẫn dưới ngưỡng 70 nên cổng vẫn chặn. Bản vá AI chỉ là gợi ý, cần người xem xét." (Đọc số điểm mới đang hiện trên màn hình.) |
| 2:10 | Giao diện: audit `FixedVault`, badge "Qua cổng" | "Đây là bản sửa viết tay, đã bỏ hẳn hàm rút tiền nguy hiểm. Vault này được 100 điểm và qua cổng." |
| 2:25 | Remix: `listProject(FixedVault)` thành công, `listedCount` tăng | "Cùng launchpad đó, lần này chấp nhận. Số vault đã niêm yết tăng lên một." |
| 2:40 | Snowtrace: Read Contract, `check` với `FixedVault` | "Giám khảo tự kiểm tra được trên Snowtrace, không cần tin video." |
| 2:50 | Slide giới hạn | "Hạn chế hiện tại: chỉ một khóa agent ký điểm, AI có thể sai, và mới thử trên contract nhỏ. Hướng tiếp theo là nhiều auditor độc lập và đối chiếu với Slither. Cảm ơn ban giám khảo." |

Nếu phải cắt cho kịp 3 phút, bỏ đoạn 1:50 (đề xuất bản vá) trước. Nếu `listedCount` vừa đọc ra 0 sau giao dịch, đợi vài giây rồi gọi lại, vì lần đọc đầu có thể chưa cập nhật.

## Nếu có sự cố khi quay

- Gemini báo quá tải (503) hoặc hết lượt (429): chờ tối đa 40 giây. Backend sẽ tự chuyển sang model dự phòng. Hoặc dùng audit đã đóng dấu từ trước và đọc badge on-chain (không tốn lượt).
- Bản vá AI chưa đủ tốt: nói thẳng, đó chính là thông điệp "bản vá AI cần người xem xét".
- Điểm có thể khác một chút giữa các lần (ví dụ 12 hoặc 16): AI có thể đổi danh sách hoặc mức nghiêm trọng của lỗi, công thức thì cố định. Luôn đọc đúng số hiện trên màn hình.
- Giao dịch đóng dấu thất bại: kiểm tra ví agent còn AVAX testnet (faucet của Avalanche).

## Nếu giám khảo hỏi về Slither

"Slither mạnh về phân tích tĩnh, ổn định và miễn phí. SentinelAgent không thay thế nó. Điểm khác là kết quả được đóng dấu trên Avalanche để contract khác tự đọc và tự chặn. Bước tiếp theo là kết hợp cả hai."
