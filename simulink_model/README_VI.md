# Mô hình Simulink có đóng cắt: thiết kế RPC 11.5 MVA

Bộ script dưới đây dựng mô hình **Simulink / Simscape Electrical (Specialized Power Systems)**. Mô hình gồm một trạm Scott đồng pha có hai nhánh RPC, mỗi nhánh N_b cầu H IGBT, chung một DC-link. Script chạy các ca kiểm tra rồi so với mô hình Python đã dùng trong bài (OR2, mục S.31).

> **Lưu ý:** script được viết khi không có MATLAB nên **chưa từng chạy trong Simulink**. Riêng phần bộ điều khiển (`rpc_ctrl_fcn.m`) đã được thử trong GNU Octave với phương trình mạch của bản Python (`test_ctrl_reference_plant.m`). Kết quả thử trong Octave (dt = 2 µs; hệ số cộng hưởng bậc 3 = 0.05 như bản Python; ca S1 chạy 1.2 s, ca S4a chạy 1.4 s, mỗi ca gồm 0.6 s khởi động):

| Ca | Nguồn | v_dc min/max (V) | I_α1 / I_β1 (pu) | Đỉnh dòng cầu (pu) | Sai lệch v_dc so với Python |
|---|---|---|---|---|---|
| S1 | Python | 3287 / 3702 | 0.948 / 0.970 | 1.126 | – |
| S1 | Octave | 3288 / 3703 | 0.949 / 0.972 | 1.124 | rms 3.3 V, max 9.9 V |
| S4a | Python | 3323 / 3702 | 0.744 / 0.755 | 0.907 | – |
| S4a | Octave | 3315 / 3703 | 0.739 / 0.759 | 0.901 | rms 2.5 V, max 9.4 V |

Bản MATLAB đọc phép đo trễ một bước nên khác bản Python một chút. Như vậy phần điều khiển đã được kiểm tra. **Phần mạch Simscape chưa được kiểm tra**: lần chạy đầu trong MATLAB có thể cần sửa tên tham số hoặc thứ tự cực của một vài khối; xem mục 4. Chỉ đưa số liệu Simulink vào bài sau khi chạy thật và so khớp.

## 1. Yêu cầu

- MATLAB + Simulink + Simscape Electrical (thư viện `powerlib`), R2020b trở lên.
- Không cần toolbox nào khác.

## 2. Chạy

Đặt toàn bộ thư mục làm *Current Folder*, rồi gõ:

```matlab
R = run_rpc_checks;                          % S1, S4a, S6; 2 cầu/nhánh, f_c = 1 kHz, dt = 1 µs
R = run_rpc_checks({'S1_sustained'}, 1);     % 1 cầu/nhánh
R = run_rpc_checks('all', 2);                % cả 16 ca
```

`run_rpc_checks` làm lần lượt:

1. Tạo tham số (`rpc_params.m`, đọc `scenarios.json`).
2. Dựng mô hình `rpc_switching_Nb2.slx` (`build_rpc_switching_model.m`).
3. **Tự kiểm tra cực tính** bằng các lần chạy ngắn:

   | Kiểm tra | Chế độ | Điều kiện đúng |
   |---|---|---|
   | 0 | khóa van | v_dc bắt đầu ở +3.5 kV |
   | A | khóa van, không tải | điện áp thanh cái α có pha 0°, β có pha +90° |
   | C | tải trở 2 kA trên thanh cái α | điện áp α phải *chậm pha* (tải hút công suất) |
   | E | dòng 200 A rút khỏi tụ DC | v_dc giảm khoảng −4.1 kV/s |
   | D | hở mạch vòng, áp cầu = 0.97·v_bus/N | dòng cầu khoảng 0.3 pu, chậm pha khoảng 90° so với v_bus |

   Nếu sai, script tự sửa bằng các tham số `ph_a`, `ph_b`, `sgn_load`, `sgn_sink`, `sgn_tr`, `sgn_ib`, `sgn_vdc`, rồi lưu vào `rpc_fix_Nb2.mat`.
4. Chạy các ca và tính các chỉ tiêu giống bản Python: v_dc min/max, dòng cơ bản I_α1 và I_β1, đỉnh và rms dòng cầu, TDD, max |d|, dòng tụ.
5. So với `python_reference.csv`, rồi ghi ra `simulink_vs_python_Nb2.csv` và `simulink_check_Nb2.png`.

Mỗi ca mô phỏng 2–4.6 s với bước 1 µs. Thời gian chạy phụ thuộc máy, có thể vài phút một ca; chế độ *Accelerator* chạy nhanh hơn.

## 3. Mô hình

| Thành phần | Mô hình Simulink | Giống bản Python? |
|---|---|---|
| Lưới + Scott | Nguồn AC 27.5 kV hai pha lệch 90° nối sau tổng trở R–L Thevenin (S_sc 750 MVA, Scott 40 MVA, uk 10.5 %). | có |
| Tải tàu | Nguồn dòng điều khiển trên thanh cái α, công suất không đổi, dòng hình sin. | có |
| Biến áp ghép | `Linear Transformer` 27.5/2 kV, C/N_b, x = 0.10 pu, r = x/30, một biến áp cho mỗi cầu. | có |
| Cầu | `Universal Bridge` 2 nhánh, IGBT/Diode lý tưởng (R_on = 0.1 mΩ, không sụt áp, không thời gian chết). | có |
| DC-link | Tụ 49.2 mF, nạp sẵn 3.5 kV; nguồn dòng tổn hao gộp. | có |
| Điều khiển + PWM | Khối MATLAB Function (mã `rpc_ctrl_fcn.m`): lấy mẫu 2 kHz, PR 150 Hz, cộng hưởng bậc 3, ước lượng trước v_dc, vòng năng lượng DC 15 Hz có notch 100 Hz và feed-forward, PWM đơn cực có sóng mang xen kẽ. | cùng thuật toán |
| Giải | powergui *Discrete*, bước 1 µs (SPS rời rạc hóa theo Tustin); bản Python dùng RK4. | khác phương pháp số |

Các phép đo được làm trễ một bước (Unit Delay) để cắt vòng đại số.

## 4. Nếu gặp lỗi khi dựng mô hình

- **`Could not set X = ... on block ...`:** tên tham số của khối khác theo phiên bản MATLAB. Thông báo lỗi liệt kê đúng tên tham số của khối đó; sửa tên tương ứng trong `build_rpc_switching_model.m`.
- **Không đặt được điện áp ban đầu của tụ:** mở khối `Cdc` và đặt điện áp ban đầu = `rpcP.VREF`.
- **Kiểm tra D vẫn báo dòng lớn sau khi đã đổi `sgn_tr`:** kiểm tra hai cực A/B và +/− của `Universal Bridge` (khi dựng, script in ra cách nối từng cực), và thứ tự xung (cầu 2 nhánh nhận [A_trên A_dưới B_trên B_dưới]).
- **MATLAB Function báo lỗi kích thước:** tham số `rpcP` của khối phải là *non-tunable* (Model Explorer → ctrl → rpcP → bỏ chọn Tunable).

## 5. Tệp

| Tệp | Nội dung |
|---|---|
| `rpc_params.m` | tham số (giống `sw_rpc.py`) |
| `rpc_ctrl_fcn.m` | bộ điều khiển, PWM, lệnh dòng tải (mã của khối MATLAB Function) |
| `build_rpc_switching_model.m` | dựng `.slx` |
| `run_rpc_checks.m` | tự kiểm tra cực tính, chạy ca, so với Python |
| `test_ctrl_reference_plant.m` | chạy bộ điều khiển với phương trình mạch của bản Python, không cần Simulink (để kiểm tra bộ điều khiển) |
| `scenarios.json`, `python_reference.csv` | các ca thử và kết quả của bản Python |
