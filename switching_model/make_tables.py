"""Tables (Markdown) from res_val.json, res_main.json, res_dt.json, res_h8.json."""
import json
V = json.load(open('res_val.json')); Mn = json.load(open('res_main.json')); D = json.load(open('res_dt.json')); H = json.load(open('res_h8.json'))
emt = V['_emt']
from run_sw_cases import S
ORDER = ['S1_sustained', 'S1b_sustained_w22', 'S2_lowU', 'S3a_rev1s', 'S3b_rev5s', 'S3c_regen_plateau', 'S4a_step+10_seg', 'S4b_step-10_seg',
         'S4c_step+10_15MW', 'S4d_step-10_25MW', 'S5_lowpf', 'S7_up1s', 'S2b_lowU_sag5', 'S2c_lowU_weak500', 'S2d_overV', 'S6_step+20_pf90']
L = []
L.append('## Bảng A. Đối chiếu với mô hình trung bình emt.py của bài báo (C = 11.27 MVA, C_dc = 48.2 mF)\n')
L.append('| Ca | v_dc min/max emt.py (V) | v_dc min/max, khóa trung bình + điều khiển số (V) | v_dc min/max, đóng cắt 2 cầu/nhánh (V) | I_α1/I_β1 emt.py (pu) | I_α1/I_β1 đóng cắt (pu) |')
L.append('|---|---|---|---|---|---|')
for sc in ORDER:
    e = emt[sc]; a = V[f'{sc}|avg']; s = V[f'{sc}|sw']
    L.append(f"| {sc} | {e['Vmin_V']:.0f}/{e['Vmax_V']:.0f} | {a['Vmin_V']:.0f}/{a['Vmax_V']:.0f} | {s['Vmin_V']:.0f}/{s['Vmax_V']:.0f} | "
             f"{e['I_pu_max'][0]:.3f}/{e['I_pu_max'][1]:.3f} | {s['I1_pu_max'][0]:.3f}/{s['I1_pu_max'][1]:.3f} |")
L.append('\n## Bảng B. Thiết kế cuối C = 11.5 MVA, H_dc = 26.2 ms (C_dc = 49.2 mF), mô hình đóng cắt 2 cầu/nhánh, f_c = 1 kHz, dt = 1 µs\n')
L.append('| Ca | v_dc min (V) | v_dc max (V) | I_α1 (pu) | I_β1 (pu) | đỉnh dòng cầu (pu đỉnh định mức) | rms dòng cầu (pu) | TDD dòng nhánh (% định mức) | max \\|d\\| |')
L.append('|---|---|---|---|---|---|---|---|---|')
for sc in ORDER:
    r = Mn[f'{sc}|sw_Nb2_fc1k']
    tag = ' (stress)' if r['stress'] else ''
    L.append(f"| {sc}{tag} | {r['Vmin_V']:.0f} | {r['Vmax_V']:.0f} | {r['I1_pu_max'][0]:.3f} | {r['I1_pu_max'][1]:.3f} | {r['Ibr_peak_pu_max']:.3f} | "
             f"{r['Ibr_rms_pu_max']:.3f} | {max(r['Ileg_TDD_pct_of_rated']):.2f} | {r['d_max']:.3f} |")
L.append('\n## Bảng C. Giá trị xấu nhất theo cấu hình (12 ca thiết kế / 4 ca stress)\n')
L.append('| Cấu hình | nhóm | v_dc min–max (V) | I_α1 / I_β1 max (pu) | đỉnh dòng cầu (pu) | rms dòng cầu (pu) | TDD dòng nhánh (%) | THD điện áp thanh cái 27.5 kV (%)* | I_Cdc rms tổng / 100 Hz / >1 kHz (A) | max \\|d\\| |')
L.append('|---|---|---|---|---|---|---|---|---|---|')
names = {'avg': 'khóa trung bình, điều khiển số', 'sw_Nb1_fc1k': 'đóng cắt, 1 cầu/nhánh, 1 kHz', 'sw_Nb2_fc1k': 'đóng cắt, 2 cầu/nhánh xen kẽ, 1 kHz'}
for cfg in ('avg', 'sw_Nb1_fc1k', 'sw_Nb2_fc1k'):
    for grp, st in (('thiết kế', False), ('stress', True)):
        R = [v for k, v in Mn.items() if k.endswith('|' + cfg) and v['stress'] == st]
        L.append(f"| {names[cfg]} | {grp} | {min(r['Vmin_V'] for r in R):.0f}–{max(r['Vmax_V'] for r in R):.0f} | "
                 f"{max(r['I1_pu_max'][0] for r in R):.3f} / {max(r['I1_pu_max'][1] for r in R):.3f} | {max(r['Ibr_peak_pu_max'] for r in R):.3f} | "
                 f"{max(r['Ibr_rms_pu_max'] for r in R):.3f} | {max(max(r['Ileg_TDD_pct_of_rated']) for r in R):.2f} | {max(max(r['Vbus_THD_pct']) for r in R):.1f} | "
                 f"{max(r['ICdc_rms_A'] for r in R):.0f} / {max(r['ICdc_100Hz_rms_A'] for r in R):.0f} / {max(r['ICdc_above1k_rms_A'] for r in R):.0f} | {max(r['d_max'] for r in R):.3f} |")
L.append('\n*Lưới mô hình là tổng trở R–L thuần (không có điện dung đường dây tiếp xúc, không có bộ lọc) nên THD điện áp ở tần số đóng cắt chỉ có tính chỉ báo.\n')
L.append('## Bảng D. Hội tụ theo bước tích phân (2 cầu/nhánh, 1 kHz)\n')
L.append('| Ca | dt (µs) | v_dc min/max (V) | I_α1/I_β1 (pu) | đỉnh dòng cầu (pu) | rms dòng cầu (pu) |')
L.append('|---|---|---|---|---|---|')
for k, r in D.items():
    sc, dt = k.split('|')
    L.append(f"| {sc} | {dt[2:]} | {r['Vmin_V']:.0f}/{r['Vmax_V']:.0f} | {r['I1_pu_max'][0]:.3f}/{r['I1_pu_max'][1]:.3f} | {r['Ibr_peak_pu_max']:.3f} | {r['Ibr_rms_pu_max']:.3f} |")
nv = sum(1 for r in H.values() if not r['band_ok'])
L.append(f"\n## Bảng E. H_dc = 8 ms (C_dc = 15.0 mF), đóng cắt 2 cầu/nhánh: dải ±10 % bị vi phạm ở {nv}/{len(H)} ca; "
         f"v_dc min–max {min(r['Vmin_V'] for r in H.values()):.0f}–{max(r['Vmax_V'] for r in H.values()):.0f} V.\n")
open('results_tables.md', 'w').write('\n'.join(L))
print('\n'.join(L))
