# -*- coding: utf-8 -*-
"""phase5_fixtures.py — Phase 5R0: dữ liệu fixture SEMANTIC cho gate visual.

WLAY-010/011: fixture cũ (dummy_data_from_map) gắn "TEST" cho mọi field và
tick X mọi checkbox kể cả nhóm loại-trừ → không đại diện hồ sơ hợp lệ, che lỗi
layout và làm nhiễu census glue. Module này sinh 5 fixture tách biệt:

  empty-paper   mọi field trống hợp lệ (chỉ khung giấy);
  valid-minimal hồ sơ tối thiểu: định danh hồ sơ + MỖI grid active đúng 1 dòng;
  valid-full    mọi section active, giá trị phân biệt theo ngữ nghĩa từng field;
  long-boundary grid 25 dòng + giá trị dài → ép pagination sát mép trang;
  choice-variants  nhóm loại-trừ chọn ĐÚNG 1, checkbox độc lập chọn đồng thời.

Nguyên tắc:
- Giá trị phân biệt theo họ key (ten/địa chỉ/CCCD/ngày/tháng/số tiền…), mỗi
  giá trị mang đuôi số thứ tự riêng → hai field không bao giờ cùng chuỗi,
  detector glue/đổi-chỗ hoạt động được.
- Nhóm loại-trừ (EXCLUSIVE_GROUPS): pattern key + nhóm theo paragraph (các
  chk inline cùng block `p` = cùng câu hỏi). Validator từ chối payload có
  nhóm được chọn >1 — chống hồi quy WLAY-010.
- Không tự sáng tạo dữ liệu pháp lý: giá trị chỉ là ví dụ đại diện định dạng.

Chạy:  python3 -X utf8 tools/phase5_fixtures.py  (selftest nhanh)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIXTURES = ("empty-paper", "valid-minimal", "valid-full",
            "long-boundary", "choice-variants")

M72_VARIANTS = [
    ("DNTN", "loai_hinh_dntn"),
    ("TNHH_1TV", "loai_hinh_tnhh_1tv"),
    ("TNHH_2TV", "loai_hinh_tnhh_2tv"),
    ("CTCP", "loai_hinh_ctcp"),
    ("DHDN", "loai_hinh_dhdn"),
]

# ---------------------------------------------------------------------------
# Nhóm loại-trừ theo pattern key (phần shared-prefix của key chk).
# Mỗi entry: (tên nhóm, regex khớp key chk, lựa chọn mặc định của fixture
# choice-variants). Nhóm = các option tranh nhau MỘT lựa chọn pháp lý.
# Checkbox ĐỘC LẬP (không khớp nhóm nào) được phép chọn đồng thời.
# ---------------------------------------------------------------------------
EXCLUSIVE_GROUPS = [
    # kỳ báo cáo BHXH: hàng tháng / 3 tháng / 6 tháng (chọn 1 trong 3)
    ("ky_bao_cao", r"^chk_bc_(hang_thang|03_thang|06_thang)$", "chk_bc_03_thang"),
    # phương thức nộp GTGT: khấu trừ / trực tiếp GTGT / trực tiếp doanh số /
    # không phải nộp — chọn 1
    ("gtgt", r"^chk_gtgt_(khoan_tru|truc_tiep_tren_gtgt|truc_tiep_doanh_so|khong_phai_nop)$", "chk_gtgt_khoan_tru"),
    # hạch toán phụ thuộc / độc lập / hợp nhất — chọn 1
    ("hach_toan", r"^chk_ht_(doc_lap|hop_nhat|phu_thuoc)$", "chk_ht_doc_lap"),
    # loại thành lập: mới / chuyển đổi từ HKD / chuyển đổi CSBT — chọn 1
    ("loai_thanh_lap", r"^chk_tt_(thanh_lap_moi|chuyen_doi_tu_hkd|chuyen_doi_tu_csbt)$", "chk_tt_thanh_lap_moi"),
    # loại giấy tờ định danh: CMND / CCCD / hộ chiếu / khác — chọn 1 mỗi người
    ("giay_to_dd", r"^chk_gt_(cmnd|cccd|ho_chieu|loai_khac)$", "chk_gt_cccd"),
    # khu vị trí: CN / chế xuất / kinh tế / công nghệ cao — chọn 1
    ("khu_vuc", r"^chk_khu_(cong_nghiep|che_xuat|kinh_te|cong_nghe_cao)$", "chk_khu_cong_nghiep"),
    # cặp Có/Không (chk_co/chk_khong hoặc chk_auto_*_co/_khong) — chọn 1;
    # đuôi _2/_3 là lặp câu hỏi giống nhau trong cùng mẫu
    ("co_khong", r"^chk_(auto_)?(co|khong)(_\d+)?$", "chk_khong"),
]

_GROUP_CACHE: dict = {}


def _fold(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def load_vsic() -> list[dict]:
    """Danh mục ngành VSIC chính thức — dùng cho dòng grid ngành (tên thật)."""
    p = ROOT / "app" / "data" / "nganh_vsic.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("nganh", [])


# ---------------------------------------------------------------------------
# Value pools — giá trị đại diện theo NGỮ NGHĨA key, đuôi _n giữ tính phân biệt
# ---------------------------------------------------------------------------

_TEN_DN = ["CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ AN PHÁT {}",
           "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ PHÁT TRIỂN BÌNH MINH {}",
           "CÔNG TY TNHH SẢN XUẤT THƯƠNG MẠI HOÀNG GIA {}",
           "CÔNG TY TNHH MTV KỸ THUẬT - XÂY DỰNG TRƯỜNG THÀNH {}",
           "CÔNG TY CỔ PHẦN CHỨNG KHOÁN KINH ĐÔ {}"]
_HO_TEN = ["NGUYỄN VĂN ANH {}", "TRẦN THỊ BÌNH {}", "LÊ VĂN CƯỜNG {}",
           "PHẠM THỊ DUNG {}", "HOÀNG VĂN ĐẠT {}", "VŨ THỊ HẰNG {}",
           "ĐẶNG MINH HẢI {}", "BÙI NGỌC LAN {}", "NGÔ QUANG HUY {}",
           "DƯƠNG THỊ MAI {}"]
_DIA_CHI = ["Số {} đường Láng Hạ, phường Láng Hạ, quận Đống Đa, TP. Hà Nội",
            "Tầng {}, toà nhà Sunrise, số 25 Nguyễn Huệ, phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
            "Số {} đường Nguyễn Văn Linh, phường Vĩnh Niệm, quận Lê Chân, TP. Hải Phòng",
            "Thôn {}, xã Hoà Lâm, huyện Hoà Vang, TP. Đà Nẵng",
            "Số {} đại lộ Thăng Long, phường Mễ Trì, quận Nam Từ Liêm, TP. Hà Nội"]
_CO_QUAN = ["Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Hà Nội",
            "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Hồ Chí Minh",
            "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Hải Phòng",
            "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Đà Nẵ"]
_QUOC_TICH = ["Việt Nam", "Nhật Bản", "Hàn Quốc", "Singapore", "Pháp"]


class ValueFactory:
    """Sinh giá trị phân biệt theo họ key; đếm toàn cục để không trùng lặp."""

    def __init__(self, vsic: list[dict] | None = None):
        self.n = 0
        self.vsic = vsic if vsic is not None else load_vsic()
        self._vsic_i = 0

    def _next(self) -> int:
        self.n += 1
        return self.n

    def _vsic_row(self) -> tuple[str, str]:
        if self.vsic:
            row = self.vsic[self._vsic_i % len(self.vsic)]
            self._vsic_i += 1
            return str(row.get("ma") or "0112"), str(row.get("ten") or "Trồng ngô")
        return "0112", "Trồng ngô và cây lương thực có hạt khác"

    def value(self, key: str, label: str = "") -> str:
        n = self._next()
        k = _fold(key)
        if "ma_nganh" in k or k.endswith("ma_so_nganh"):
            return self._vsic_row()[0]
        if "ten_nganh" in k or "nganh_nghe" in k:
            return self._vsic_row()[1]
        if "quoc_tich" in k:
            return _QUOC_TICH[n % len(_QUOC_TICH)]
        if "ma_so_thue" in k or "ma_so_dn" in k or "ma_so_ho" in k:
            return "010%s%04d" % (n % 90 + 10, n)
        if "cccd" in k or "can_cuoc" in k or "so_dinh_danh" in k or "cmnd" in k:
            return "0%s%011d" % (n % 9 + 1, n)
        if "ho_chieu" in k:
            return "C%d%07d" % (n % 9 + 1, n)
        if "dien_thoai" in k:
            return "09%08d" % n
        if "fax" in k:
            return "024.%08d" % n
        if "email" in k or "thu_dien_tu" in k:
            return "contact%d@congty.example.vn" % n
        if "website" in k:
            return "https://congty%d.example.vn" % n
        if "ten_tieng_viet" in k or "ten_doanh_nghiep" in k or \
                k.endswith("ten_cn") or "ten_don_vi" in k:
            return _TEN_DN[n % len(_TEN_DN)].format(n)
        if "ho_ten" in k or "ten_chu" in k or "ten_nguoi" in k or \
                "ten_thanh_vien" in k or "ten_co_dong" in k or \
                "ten_dai_dien" in k or k.endswith("nguoi_uy_quyen"):
            return _HO_TEN[n % len(_HO_TEN)].format(n)
        if "dia_chi" in k:
            return _DIA_CHI[n % len(_DIA_CHI)].format(n * 3)
        if "co_quan_dkkd" in k or "co_quan_cap" in k:
            return _CO_QUAN[n % len(_CO_QUAN)]
        if "von_dieu_le" in k or "von_dang_ky" in k or "gia_tri" in k or \
                "menh_gia" in k or "so_tien" in k or "tong" in k or \
                "muc_von" in k or "so_von" in k:
            return str(n * 500000000)
        if "ty_le" in k or "phan_tram" in k:
            return str((n * 7) % 100 + 1)
        if k.endswith("ngay") or "ngay_sinh" in k or "ngay_cap" in k or \
                "ngay_ky" in k:
            return "%02d" % (n % 28 + 1)
        if k.endswith("thang"):
            return "%02d" % (n % 12 + 1)
        if k.endswith("nam"):
            return "20%d" % (20 + n % 7)
        if "nam_sinh" in k:
            return "19%d" % (70 + n % 30)
        if "so_nha" in k:
            return str(n * 3)
        if "chuc_danh" in k:
            return "Giám đốc" if n % 2 else "Kế toán trưởng"
        if "mo_ta" in k or "ghi_chu" in k or "noi_dung" in k:
            return "Nội dung kê khai số %d — mô tả đầy đủ, có dấu tiếng Việt" % n
        if "loai_giay_to" in k or "ten_giay_to" in k or "ten_tai_lieu" in k:
            return "Giấy chứng nhận đăng ký doanh nghiệp bản gốc số %d" % n
        if "so_ban" in k:
            return str(n % 3 + 1)
        if "so_trang" in k:
            return str(n % 10 + 1)
        if "so_van_ban" in k or "so_ho_so" in k or "so_cn" in k:
            return "%05d/%d" % (n, 2026)
        if "viet_tat" in k:
            return "ANPHAT%d" % n
        # mặc định: dùng nhãn để tránh hai field khác nhãn cùng một chuỗi
        base = _fold(label or key)[:24].upper().replace(" ", "_") or "GIATRI"
        return "%s_%d" % (re.sub(r"[^0-9A-Z_]", "", base), n)


# ---------------------------------------------------------------------------
# Nhóm loại-trừ: pattern + paragraph-level
# ---------------------------------------------------------------------------

def chk_groups(form_map: dict, blocks: dict | list) -> list[list[str]]:
    """Trả danh sách nhóm loại-trừ: mỗi nhóm là list key chk tranh nhau.

    Hai nguồn: (1) EXCLUSIVE_GROUPS theo pattern key; (2) mọi tập chk inline
    xuất hiện trong CÙNG một block `p` (cùng câu hỏi trên giấy). Nhóm pattern
    và nhóm paragraph có thể trùng member — dedupe giữ nhóm dài hơn."""
    fields = form_map.get("fields", [])
    chk_keys = [f["key"] for f in fields if f.get("type") == "chk"]
    keyset = set(chk_keys)
    groups: list[list[str]] = []

    # (1) theo pattern
    for _name, pat, _pick in EXCLUSIVE_GROUPS:
        rx = re.compile(pat)
        members = [k for k in chk_keys if rx.match(k)]
        if len(members) >= 2:
            groups.append(members)

    # (2) theo paragraph (chk inline cùng block p)
    for grp in _paragraph_groups(blocks):
        members = [k for k in grp if k in keyset]
        if len(members) >= 2:
            groups.append(members)
    return _merge_overlapping(groups)


def _merge_overlapping(groups: list[list[str]]) -> list[list[str]]:
    """Gộp các nhóm chia member (cùng một câu hỏi bị bắt bởi 2 nguồn) —
    tránh pick 2 lựa chọn cho cùng một câu."""
    merged: list[set[str]] = []
    for g in groups:
        gs = set(g)
        hit = [m for m in merged if m & gs]
        if hit:
            union = gs.union(*hit)
            merged = [m for m in merged if m not in hit]
            merged.append(union)
        else:
            merged.append(gs)
    return [sorted(m) for m in merged]


def _paragraph_groups(blocks) -> list[list[str]]:
    out: list[list[str]] = []
    items = blocks.get("blocks") if isinstance(blocks, dict) else blocks
    for b in items or []:
        if not isinstance(b, dict) or b.get("t") != "p":
            continue
        keys = []
        for r in b.get("runs") or []:
            if isinstance(r, dict) and isinstance(r.get("input"), dict):
                k = r["input"].get("key") or ""
                if k.startswith("chk"):
                    keys.append(k)
        if len(keys) >= 2:
            out.append(keys)
    return out


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def build_fixture(fid: str, form_map: dict, fixture: str,
                  blocks=None, factory: ValueFactory | None = None) -> dict:
    """Sinh data dict cho (form, fixture). Không đụng draft/validation —
    đây là dữ liệu export để gate visual xem bố cục."""
    if fixture not in FIXTURES:
        raise ValueError("fixture không hợp lệ: %r" % fixture)
    f = factory or ValueFactory()
    data: dict = {}
    if fixture == "empty-paper":
        return data
    is_minimal = fixture == "valid-minimal"
    is_long = fixture == "long-boundary"

    # ---- scalar fields ----
    for field in form_map.get("fields", []):
        key, ftype = field["key"], field.get("type", "text")
        if ftype == "chk":
            # chk xử lý ở chọn nhóm / choice fixture phía dưới; valid-full
            # KHÔNG tick tất (đó chính là bug WLAY-010).
            continue
        if is_minimal and not _minimal_key(key):
            continue
        data[key] = f.value(key, field.get("label") or "")
        if is_long and _stretchable(key):
            data[key] = "%s %s" % (data[key],
                                   "kèm theo phần mô tả mở rộng số %d để ép "
                                   "dòng văn bản xuống dòng nhiều lần trong ô"
                                   % f.n)

    # ---- chk: chỉ fixture choice tick ----
    if fixture == "choice-variants":
        groups = chk_groups(form_map, blocks or {})
        members_in_groups: set[str] = set()
        picked: set[str] = set()
        for members in groups:
            members_in_groups.update(members)
            pick = _group_pick(members)
            if pick:
                picked.add(pick)
        for field in form_map.get("fields", []):
            if field.get("type") != "chk":
                continue
            key = field["key"]
            if key in picked:
                data[key] = "X"
            elif key not in members_in_groups:
                # checkbox độc lập (không thuộc nhóm nào) chọn đồng thời
                data[key] = "X"

    # ---- dynamic tables (loop) ----
    rows_n = 1 if is_minimal else (25 if is_long else 3)
    for t in form_map.get("dynamic_tables", []):
        loop, cols = t["loop"], t.get("columns", [])
        data[loop] = [{c["tag"]: f.value(c["tag"], c.get("label") or "")
                       for c in cols} for _ in range(rows_n)]

    # ---- fixed-matrix cells (spec-driven) ----
    specs = [s for s in (form_map.get("section_specs") or [])
             if s.get("kind") == "fixed-matrix"]
    for spec in specs:
        sem = spec.get("semantic_key")
        editable = {r["id"] for r in spec.get("fixed_rows", [])
                    if not r.get("output_only")}
        for row_id in sorted(editable):
            for c in spec.get("columns", []):
                if c.get("tag") and not c.get("computed"):
                    if is_minimal and not _minimal_key(c["tag"]):
                        continue
                    data["%s.%s.%s" % (sem, row_id, c["tag"])] = \
                        f.value(c["tag"], c.get("label") or "")
    return data


def _group_pick(members: list[str]) -> str:
    """Chọn thành viên đại diện cho nhóm: ưu tiên pick khai báo trong
    EXCLUSIVE_GROUPS nếu còn trong members, nếu không thì member đầu."""
    for _name, pat, pick in EXCLUSIVE_GROUPS:
        rx = re.compile(pat)
        if pick in members and all(rx.match(m) for m in members):
            return pick
    return members[0]


def _minimal_key(key: str) -> bool:
    """Field bắt buộc cho hồ sơ tối thiểu: định danh + liên hệ + ngày ký."""
    k = _fold(key)
    return bool(re.search(
        r"(ten_tieng_viet|ten_chu_ho|ho_ten|ten_doanh_nghiep|ma_so_thue|"
        r"ma_so_dn|ma_so_ho|dia_chi_tru_so|dia_chi|ngay_ky|thang_ky|nam_ky|"
        r"dia_diem_ky|co_quan_dkkd|ngay|thang|nam$)", k))


def _stretchable(key: str) -> bool:
    k = _fold(key)
    return bool(re.search(r"(dia_chi|mo_ta|ghi_chu|ten_nganh|ten_doanh_nghiep|"
                          r"ten_tieng_viet|noi_dung)", k))


# ---------------------------------------------------------------------------
# Validator — chống hồi quy WLAY-010 (tick tràn nhóm loại-trừ)
# ---------------------------------------------------------------------------

def validate_fixture(form_map: dict, blocks, data: dict,
                     fixture: str) -> list[str]:
    """Trả list vi phạm (rỗng = hợp lệ). Kiểm:
    (V1) nhóm loại-trừ chọn đúng <=1;
    (V2) empty-paper không có giá trị nào;
    (V3) fixture khác: mỗi grid active có dữ liệu (trừ empty);
    (V4) không dùng chuỗi 'TEST' chung mọi field."""
    errs: list[str] = []
    if fixture == "empty-paper":
        if any(str(v).strip() for v in data.values()):
            errs.append("V2: empty-paper phải trống hoàn toàn")
        return errs
    # (V1)
    for members in chk_groups(form_map, blocks):
        chosen = [k for k in members if str(data.get(k) or "").strip()]
        if len(chosen) > 1:
            errs.append("V1: nhóm loại-trừ %s được chọn %d: %s"
                        % (members[0], len(chosen), ",".join(chosen)))
    # (V3)
    if fixture != "valid-minimal":
        for t in form_map.get("dynamic_tables", []):
            if not isinstance(data.get(t["loop"]), list) or \
                    not data[t["loop"]]:
                errs.append("V3: grid %s không có dòng dữ liệu" % t["loop"])
    # (V4)
    vals = [str(v) for v in data.values() if str(v).strip()]
    if vals and all(v == "TEST" for v in vals):
        errs.append("V4: fixture dùng chung chuỗi TEST cho mọi field")
    return errs


# ---------------------------------------------------------------------------
# CLI selftest
# ---------------------------------------------------------------------------
def _selftest() -> int:
    import sys
    sys.path.insert(0, str(ROOT))
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    ok = fail = 0
    for fid in sorted(maps):
        blocks_p = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
        blocks = (json.loads(blocks_p.read_text(encoding="utf-8"))
                  if blocks_p.exists() else {})
        for fixture in FIXTURES:
            f = ValueFactory()
            data = build_fixture(fid, maps[fid], fixture, blocks, f)
            errs = validate_fixture(maps[fid], blocks, data, fixture)
            if errs:
                fail += 1
                print("FAIL %s/%s: %s" % (fid, fixture, "; ".join(errs)))
            else:
                ok += 1
    # fixture cũ (dummy tick mọi chk) phải bị validator chặn
    from tools.docx_render import dummy_data_from_map
    old = dummy_data_from_map(maps["PLI_M01"])
    blocks = json.loads((ROOT / "app" / "data" / "blocks" / "PLI_M01.json")
                        .read_text(encoding="utf-8"))
    old_errs = validate_fixture(maps["PLI_M01"], blocks, old, "choice-variants")
    if any(e.startswith("V1") for e in old_errs):
        ok += 1
        print("PASS regression WLAY-010: dummy cũ bị chặn (V1)")
    else:
        fail += 1
        print("FAIL: dummy cũ KHÔNG bị chặn: %r" % old_errs)
    print("-" * 60)
    print("phase5_fixtures selftest: %d PASS / %d FAIL" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
