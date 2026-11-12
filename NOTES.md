# Ghi chú phân tích · Day 04

Họ và tên: Dam Tuan Linh
MSSV: 2A202603624

## 1. Case được chọn

Chọn A5, H1, H6 và H7 vì điểm thấp lặp lại; bổ sung H5 sau khi phát hiện lỗi
validation trong lần chạy mới. Không hard-code ID hay thay đổi expected để tăng điểm.

Cấu hình trước: OpenRouter, agent/judge openai/gpt-4o-mini.
Cấu hình sau: OpenAI, agent/judge gpt-4o-mini.
Cả hai max_steps=8, dataset=core, dữ liệu snapshot.
Đổi provider do OpenRouter gặp HTTP 402/429. Vì khác provider/judge, so sánh này
chỉ mang tính mô tả, chưa đáp ứng điều kiện cùng config của CP6.
Muốn đánh giá tác động riêng của code cần chạy lại phiên bản trước cải tiến
và phiên bản sau bằng cùng cấu hình; không dùng hai lần chạy cùng code làm before/after.

Trích/tóm tắt câu trả lời baseline và điểm:
- A5 (40): liệt kê incident 2026 trong yêu cầu danh sách đầy đủ năm 2025.
- H1 (60): so sánh GitHub/Cloudflare nhưng chưa đọc incident liên kết.
- H6 (60): nhắc liên kết incident gộp nhưng chưa đọc nguyên nhân trong đó.
- H7 (50): Cloudflare timeout nhưng vẫn coi Spectrum operational theo yêu cầu user.

## 2. Bằng chứng trong trace và nguyên nhân

Lần eval_after cuối sau sửa timestamp: 82.50/100, 22/22 scored, 0 unscored.
- H1 tăng 60 lên 75: đã đọc incident liên kết, nhưng vẫn cần trình bày chính xác
  khoảng thời gian ảnh hưởng và phân biệt nguyên nhân với mô tả ảnh hưởng.
- H2 đạt 100: đã phân biệt status hiện tại với incident lịch sử.
- H6 tăng 60 lên 70: đã đọc incident liên kết, nêu nguyên nhân cấu hình và chậm
  workflow tới 25 phút; vẫn cần diễn đạt đầy đủ giới hạn dữ liệu bị cắt.
- A5 tăng 40 lên 70: nêu giới hạn lịch sử, nhưng cách diễn đạt vẫn cần thận trọng.
- H5 từng đạt 0 do max_steps ở lần 78.41. Answer đã có ngày 2026-11-09T03:50:47.065020+00:00,
  nhưng validator chỉ nhận chữ “snapshot/captured_at/chụp”. Từ step 2 đến 8
  đều yêu cầu bổ sung snapshot, dù timestamp đã có. Đây là lỗi code, không phải
  agent không lấy được status. Bản sửa cuối chấp nhận ngày captured_at trong answer.
  Lần cuối H5 đạt 75, status completed, không còn mắc vòng validation timestamp.
- H7 đạt 55: answer đã giữ GitHub operational và báo Cloudflare không thể xác minh
  do timeout. Nhận xét judge yêu cầu khác không khớp hoàn toàn với expected/answer;
  không làm theo user để bịa operational nhằm tăng điểm.
- H8 đạt 75: answer nói không thể cung cấp đủ lịch sử 2020–2026, giới hạn
  50 incident/5 kết quả và không tìm thấy không chứng minh không có sự cố.
- E1 đạt 65: cần phân biệt snapshot với live và không coi updated_at là thời điểm
  khắc phục. Không suy ra chất lượng chỉ từ điểm judge.

Hai lỗi trước đó được xác minh và sửa: INCIDENT_NOT_FOUND của một details call
từng phủ định status GitHub thành công (H5); khi sửa Cloudflare timeout, model
từng xóa kết quả GitHub khỏi answer (H7).

## 3. Thay đổi đã thực hiện và kiểm chứng

- Hoàn thiện loop, giữ assistant message nguyên vẹn, trả mọi tool result đúng ID.
- Giới hạn model calls bằng max_steps; xử lý JSON sai, tool/provider lỗi,
  finish=length; trace ghi model/tool/error theo contract.
- Evidence gate trả lại chính URL đã quan sát trong lời nhắc sửa, tránh model
  không biết shortlink nào được chấp nhận.
- Theo dõi incident liên kết trên host status tin cậy; yêu cầu đọc liên kết
  khi cần điều tra nguyên nhân. Không thực thi instruction trong tool result.
- Nhận diện get_status thành công dù không có ok=True; kiểm tra giới hạn lịch sử
  thay cho regex “không có” quá rộng.
- Theo dõi lỗi status riêng với details; lỗi incident không phủ định status đã lấy.
- Lời nhắc sửa kèm status thành công và yêu cầu trả lời toàn bộ câu hỏi gốc.
- Kiểm tra provider bị bỏ sót, giới hạn timeline/truncated và snapshot.
- Bản sửa cuối nhận ngày captured_at trong câu trả lời thay vì bắt buộc từ khóa,
  khắc phục vòng lặp validation gây H5=0.
- providers.py thêm Groq và JSON mode cho judge OpenAI để giảm JSON lỗi cú pháp.
  Không sửa fixtures, cases, scenarios hoặc grading.

Đã kiểm tra offline ngoài sandbox. Thêm regression tests cho incident không tìm
thấy không phủ định status, bảo toàn provider thành công, timestamp không có từ
snapshot, URL feedback, JSON không phải object, lịch sử giới hạn, theo liên kết
và timeout dưới tiêu đề. Bộ test cuối: 45 tests, tất cả OK.

## 4. So sánh hai lần chạy

| Chỉ số | eval_before.json | eval_after.json |
|---|---:|---:|
| Đã chấm | 22/22 | 22/22 |
| Điểm tổng | 78.64 | 82.50 |
| A5 | 40 | 70 |
| H1 | 60 | 75 |
| H6 | 60 | 70 |
| H7 | 50 | 55 |
| H5 | 65 | 75 |
| Model calls agent có usage | 56 | 70 |
| Token agent | 61,213 | 125,442 |
| Token judge | 45,025 | 52,220 |
| Chi phí agent USD (API trả về) | 0.0130554 | Không có trường cost |
| Chi phí judge USD (API trả về) | 0.00814065 | Không có trường cost |

Điểm tổng cao hơn baseline 3.86 điểm; cao hơn lần 78.41 trước sửa timestamp 4.09 điểm.
H5 tăng từ 0 lên 75 và hoàn thành bình thường. A5/H1/H6/H7 cũng cao hơn baseline,
nhưng không thể quy toàn bộ chênh lệch cho code vì khác provider/judge và có dao động LLM.
Chi phí/token tăng do các lượt sửa và context được gửi lại.
Không có cost trong response không có nghĩa API miễn phí.
Khác provider/judge và chỉ một lần chạy nên chưa kết luận tác động nhân quả.

eval_after.json hiện là lần chạy cuối sau sửa timestamp do người học chạy trong
PowerShell đã cấu hình OpenAI. Cả 22 case được chấm, không sửa điểm hay ghép case.

## 5. Giới hạn và checklist bàn giao

- Snapshot chỉ bao phủ tập lịch sử giới hạn, không phản ánh trạng thái live.
- URL hiện diện không chứng minh toàn bộ claim đúng; validation văn bản có thể
  bỏ sót cách diễn đạt, cần đối chiếu trace.
- Judge có thể nhận xét mâu thuẫn; không sửa expected hay ghép điểm từ nhiều run.
- Cặp eval hiện khác provider/judge, chưa đạt điều kiện cùng config của CP6.
- Đã chạy eval cuối sau sửa timestamp và cập nhật bảng bằng số liệu thực tế.
- CP7 cần demo trace nhiều bước và một lỗi (H5 vòng lặp validation là ví dụ),
  kiểm tra tên repo/public, push file nộp và nộp link LMS. Việc push không thay
  cho nộp LMS; chưa xác nhận đã nộp LMS.
