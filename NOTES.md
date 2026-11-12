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

Lần eval_after cuối sau cải tiến tìm kiếm: 84.32/100, 22/22 scored, 0 unscored.
Lần này được chạy vào eval_candidate.json trước khi sao chép nguyên vẹn thành eval_after.json.
- H1 tăng 60 lên 80: đã đọc incident liên kết, nhưng vẫn cần trình bày chính xác
  khoảng thời gian ảnh hưởng và phân biệt nguyên nhân với mô tả ảnh hưởng.
- H2 đạt 100: đã phân biệt status hiện tại với incident lịch sử.
- H6 tăng 60 lên 80: luồng đọc incident liên kết đã hoạt động; vẫn cần kiểm tra
  độ chính xác của tổng hợp và giới hạn dữ liệu trong từng answer.
- A5 tăng 40 lên 100: lần cuối đạt đầy đủ yêu cầu chấm về giới hạn lịch sử.
- H5 từng đạt 0 do max_steps ở lần 78.41. Answer đã có ngày 2026-11-09T03:50:47.065020+00:00,
  nhưng validator chỉ nhận chữ “snapshot/captured_at/chụp”. Từ step 2 đến 8
  đều yêu cầu bổ sung snapshot, dù timestamp đã có. Đây là lỗi code, không phải
  agent không lấy được status. Bản sửa cuối chấp nhận ngày captured_at trong answer.
  Lần cuối H5 đạt 75, status completed, không còn mắc vòng validation timestamp.
- H7 từng đạt 55 ở lần 82.50: answer đã giữ GitHub operational và báo Cloudflare không thể xác minh
  do timeout. Nhận xét judge yêu cầu khác không khớp hoàn toàn với expected/answer;
  không làm theo user để bịa operational nhằm tăng điểm.
- Lần cuối H7 đạt 65; chưa thể coi timeout/khẳng định thiếu dữ liệu là vấn đề đã
  được giải quyết hoàn toàn chỉ nhờ điểm tăng. Cần tiếp tục đối chiếu trace và judge.
- H8 tăng từ 75 lên 100 so với lần OpenAI trước: giới hạn lịch sử được chấm đủ.
- E1 đạt 75: cần phân biệt snapshot với live và không coi updated_at là thời điểm
  khắc phục. Không suy ra chất lượng chỉ từ điểm judge.

Hai lỗi trước đó được xác minh và sửa: INCIDENT_NOT_FOUND của một details call
từng phủ định status GitHub thành công (H5); khi sửa Cloudflare timeout, model
từng xóa kết quả GitHub khỏi answer (H7).

## 3. Thay đổi đã thực hiện và kiểm chứng

Thử nghiệm tiếp sau kết quả 82.50, đã eval đạt 84.32: hướng dẫn tìm đúng component
trước khi đọc details, giảm đọc hàng loạt incident không liên quan, phân biệt số
kết quả hiển thị với tổng số khớp, giữ đúng khoảng ảnh hưởng và tránh liệt kê năm
ngoài yêu cầu. Validation phạm vi yêu cầu truy vấn sản phẩm trước khi chọn details
từ một danh sách tổng quan. Thêm regression test cho luồng này; 46/46 tests pass.
Giữ kết quả 82.50 trong eval_previous_openai.json để so sánh bổ sung cùng cấu hình
OpenAI với eval_candidate.json. Hai file là hai phiên bản code khác nhau; một lần
đo mỗi phiên bản chưa đủ chứng minh độ ổn định.

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
và timeout dưới tiêu đề. Bộ test cuối: 46 tests, tất cả OK.

## 4. So sánh hai lần chạy

| Chỉ số | eval_before.json | eval_after.json |
|---|---:|---:|
| Đã chấm | 22/22 | 22/22 |
| Điểm tổng | 78.64 | 84.32 |
| A5 | 40 | 100 |
| H1 | 60 | 80 |
| H6 | 60 | 80 |
| H7 | 50 | 65 |
| H5 | 65 | 75 |
| Model calls agent có usage | 56 | 65 |
| Token agent | 61,213 | 131,445 |
| Token judge | 45,025 | 45,674 |
| Chi phí agent USD (API trả về) | 0.0130554 | Không có trường cost |
| Chi phí judge USD (API trả về) | 0.00814065 | Không có trường cost |

Điểm tổng cao hơn baseline OpenRouter 5.68 điểm; cao hơn lần OpenAI 82.50 trước
cải tiến tìm kiếm 1.82 điểm. So với lần OpenAI trước, số calls giảm từ 70 xuống 65,
token agent tăng từ 125,442 lên 131,445, token judge giảm từ 52,220 xuống 45,674.
Không thể kết luận token hoặc chi phí luôn giảm nhờ đọc ít incident hơn.
H5 tăng từ 0 lên 75 và hoàn thành bình thường. A5/H1/H6/H7 cũng cao hơn baseline,
nhưng không thể quy toàn bộ chênh lệch cho code vì khác provider/judge và có dao động LLM.
Chi phí/token tăng do các lượt sửa và context được gửi lại.
Không có cost trong response không có nghĩa API miễn phí.
Khác provider/judge và chỉ một lần chạy nên chưa kết luận tác động nhân quả.

eval_after.json hiện là bản sao nguyên vẹn của eval_candidate.json, lần chạy code
mới nhất do người học chạy trong PowerShell cấu hình OpenAI. Cả 22 case được chấm,
không sửa điểm hay ghép case. E5 tăng 50 lên 75 và A5/H8 đạt 100; E3 giảm 75 xuống
65, E6 giảm 95 xuống 75, H3 giảm 100 xuống 70 so với lần OpenAI 82.50. Đây là các
case cần xem thêm nếu tiếp tục cải tiến; điểm tổng tăng không có nghĩa mọi case tăng.

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
