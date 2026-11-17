# Kiểm chứng thiết kế 11.5 MVA bằng mô hình có đóng cắt (PWM)

**Mục đích:** kiểm tra lại dải điện áp DC-link và dòng các nhánh RPC của thiết kế cuối, khi có đóng cắt của van. Thiết kế cuối gồm:
- C = 11.5 MVA/nhánh, ε_u = 1 %;
- H_dc = 26.2 ms, tức C_dc = 49.2 mF ở 3.5 kV;
- có feed-forward công suất nhánh α.

Đây là mô hình **Python (numba)**, không phải PSCAD/EMTDC hay Simulink. Kết quả không so với số đo thực tế.

## 1. Mô hình

Một trạm Scott đồng pha, lấy lại các phần sau của `emt.py` (mô hình trung bình dùng trong bài):
- nguồn hai feeder lệch 90°, Ssc = 750 MVA, Scott 40 MVA/nhánh, uk = 10.5 %;
- tải tàu công suất không đổi trên thanh cái α;
- luật (15) dùng điện áp thanh cái đo được, giới hạn dòng ưu tiên P;
- vòng năng lượng DC 15 Hz có notch 100 Hz và feed-forward.

**Khác với mô hình trung bình:**

| Hạng mục | Mô hình đóng cắt |
|---|---|
| Bộ biến đổi | Mỗi nhánh gồm N_b cầu H một pha, van lý tưởng, PWM đơn cực (3 mức), f_c = 1 kHz. Sóng mang các cầu lệch nhau T_c/(2N_b). Điện áp ra s·v_dc với s ∈ {−1, 0, +1}; dòng DC là s·i. |
| Biến áp ghép | Mỗi cầu có biến áp riêng 27.5/2.0 kV, công suất C/N_b, uk = 10 %, X/R = 30. |
| Điều khiển số | Lấy mẫu tại đỉnh và đáy sóng mang (2 kHz), trễ tính toán 1 mẫu, đo bằng giá trị trung bình trong chu kỳ mẫu. |
| Vòng dòng | PR với ω_c ứng với 150 Hz, có bù trễ (Yepes 2010). Thêm cộng hưởng bậc 3 (hệ số 0.05). Ước lượng trước v_dc tại tâm khoảng áp duty. |
| Tích phân | RK4, dt = 1 µs (kiểm tra hội tụ ở 2/1/0.5 µs: Bảng D). |

**Hai bổ sung điều khiển là cần thiết.** Nếu không bù, gợn 100 Hz trên DC-link (±5.9 %) cộng với trễ lấy mẫu sinh ra dòng bậc 3 khoảng 12 %. Ước lượng trước v_dc cùng khâu cộng hưởng bậc 3 đưa thành phần này xuống dưới khoảng 1 %. Khâu cộng hưởng bậc 5 làm vòng dòng mất ổn định nên không dùng.

**Mô hình chưa có:**
- thời gian chết, sụt áp và tổn hao van (tổn hao chỉ được gộp thành tải DC như `emt.py`);
- ESR của tụ;
- PLL (tần số cố định 50 Hz);
- điện dung đường dây tiếp xúc;
- bộ lọc đầu ra;
- dòng hài của tàu (dòng tàu được giả thiết hình sin);
- bảo vệ.

## 2. Cách chạy

Cần Python ≥ 3.10 với numpy, scipy, matplotlib và numba.

```
python run_sw.py val    # đối chiếu với emt.py ở 11.27 MVA (Bảng A)
python run_sw.py main   # thiết kế 11.5 MVA: 2 cầu/nhánh, 1 cầu/nhánh, khóa trung bình (Bảng B, C)
python run_sw.py dt     # hội tụ theo dt (Bảng D)
python run_sw.py h8     # H_dc = 8 ms (Bảng E)
python make_tables.py   # tạo results_tables.md
python make_fig_sw.py   # tạo fig_switching_check.pdf/png
```

Mỗi ca 3–4.6 s mô phỏng mất khoảng 1–3 s. Có 16 ca, lấy từ `scenarios.json`:
- 12 ca thiết kế, lấy từ các tuần thiết kế giống bài báo;
- 4 ca stress: S2b, S2c, S2d và S6.

## 3. Kết quả chính

Tất cả số liệu dưới đây lấy từ `results_tables.md`.

1. **Mô hình mới khớp với emt.py** (Bảng A, ở 11.27 MVA, dt = 2 µs):
   - Ở 11 ca không có bước tải, v_dc min/max lệch ≤ 5 V với chế độ khóa trung bình và ≤ 11 V khi có đóng cắt. Dòng cơ bản lệch ≤ 0.02 pu.
   - Ở các ca có bước tải, điều khiển số (2 kHz) cho v_dc max cao hơn: ví dụ 3707 V so với 3665 V ở bước +10 MW. Lý do là `emt.py` lấy mẫu liên tục với băng thông 600 Hz.
2. **DC-link** (Bảng B, C), thiết kế 11.5 MVA, 2 cầu/nhánh:
   - 12 ca thiết kế: v_dc nằm trong **3286–3715 V**, tức trong dải 3150–3850 V với lề ≥ 135 V.
   - Đóng cắt chỉ thêm gợn khoảng 9 V đỉnh–đỉnh (18 V với 1 cầu/nhánh).
   - Với H_dc = 8 ms, dải bị vi phạm ở 15/16 ca, đúng như kết luận của bài.
   - **Kết luận về chọn tụ 49 mF của bài được giữ nguyên.**
3. **Dòng nhánh (thành phần cơ bản):** lớn nhất 0.963 pu (α) và 0.984 pu (β) ở các ca thiết kế. Bài đang viết "≤ 0.98" (từ emt.py ở 11.27 MVA); nên sửa thành "≤ 0.99".
4. **Dòng qua van (cầu):**
   - rms kể cả gợn đóng cắt ≤ 0.997 pu, nên công suất 11.5 MVA đủ về mặt nhiệt.
   - Đỉnh tức thời lên tới **1.16 pu** đỉnh định mức (2 cầu xen kẽ) và 1.09 pu (1 cầu). Gợn đỉnh–đỉnh của mỗi cầu khoảng 0.5 pu; với 2 cầu còn có dòng vòng giữa hai cầu khoảng 0.25 pu.
   - Hệ quả: van và ngưỡng bảo vệ quá dòng phải chọn cho khoảng 1.2 pu đỉnh. Nếu muốn giảm, có thể thêm cuộn kháng nối tiếp, tăng f_c, hoặc dùng cuộn kháng ghép cho các cầu xen kẽ.
5. **Ca stress S6** (bước +20 MW, cosφ 0.9):
   - v_dc max đạt 3838 V, chỉ còn 12 V tới giới hạn 3850 V.
   - Dòng cơ bản α vượt định mức tạm thời (1.017 pu); đỉnh van 1.38 pu.
   - Hiện tượng này cũng xuất hiện ở chế độ khóa trung bình có điều khiển số, nên nguyên nhân là trễ lấy mẫu chứ không phải đóng cắt. Ca này nằm ngoài tập thiết kế, nhưng cho thấy dự trữ khi có quá độ lớn rất mỏng.
6. **Sóng hài và tụ DC:**
   - TDD dòng nhánh: 2.6 % với 2 cầu xen kẽ (thành phần chính quanh 3.9 kHz); 10 % với 1 cầu (quanh 1.95 kHz). Cần thiết kế bộ lọc đầu ra; bài báo chưa tính phần này.
   - THD điện áp thanh cái 13–31 % chỉ có tính chỉ báo, vì lưới được mô hình hóa thuần R–L đến vài kHz.
   - Dòng rms qua tụ DC: khoảng 4.45 kA ở 100 Hz, cộng 2.0 kA (2 cầu) hoặc 3.0 kA (1 cầu) ở tần số đóng cắt; tổng 4.9–5.2 kA. Dàn tụ cần chọn theo giá trị này.

## 4. Tệp

| Loại | Tệp |
|---|---|
| Mô hình | `sw_rpc.py` |
| Chỉ tiêu | `sw_post.py` |
| Chạy ca | `run_sw.py`, `run_sw_cases.py` |
| Bảng, hình | `make_tables.py`, `make_fig_sw.py` |
| Dữ liệu ca | `scenarios.json`; giá trị tham chiếu emt.py ở `emt_A26_reference.json` |
| Kết quả | `res_val.json`, `res_main.json`, `res_dt.json`, `res_h8.json`, `*.log`, `results_tables.md`, `fig_switching_check.pdf/png` |
