# -*- coding: utf-8 -*-
"""Contract test release (Agent 1C qa-contract) — file kiểm toán độc lập.

Ba check độc lập, KHÔNG sửa production, chỉ đọc dữ liệu/template và render ra
thư mục kết quả riêng:

a. CONTRACT_PLII_M01_STT_X
   Render DOCX PLII_M01 với ds_nganh 3 dòng (data dựng từ form_maps fields),
   mở bằng python-docx và assert: bảng ngành có STT '1','2','3' ở cột 0 và
   đúng MỘT ô 'X' ở cột "Ngành, nghề kinh doanh chính".
   HIỆN TẠI FAIL (template chưa có {_stt}/{la_nganh_chinh} ở hàng khuôn) —
   đây là chủ đích: test đỏ phát hiện bug, sẽ xanh sau khi Agent 1A merge.
   Khi FAIL, in rõ trạng thái EXPECTED-RED-BEFORE-1A.

b. CONTRACT_FORMS_METADATA
   Quét use_cases.json: mọi case có forms phải khai đủ bat_buoc (bool) trên
   từng form; ít nhất case chuyen_doi_hkd_sang_dn phải có metadata nhóm
   loại-trừ (oneOf). HIỆN TẠI phần oneOf CHƯA có -> FAIL với thông điệp rõ
   (sẽ xanh sau khi Agent 1B merge). Khi FAIL, in EXPECTED-RED-BEFORE-1B.

c. INVENTORY_DS_NGANH (PASS-thông tin)
   Quét toàn bộ app/data/blocks/*.json (87 mẫu): liệt kê mẫu chưa có block
   loop tên ds_nganh, đối chiếu danh sách 13 mẫu trong PLAN.md, in bảng phân
   nhóm formation(4)/change(7)/household(2); phát hiện và LIỆT KÊ RIÊNG các
   loop tên nganh_* khác nghĩa (bo_sung/xoa_bo/truoc_thay_doi...) — không
   đề xuất gộp với canonical ds_nganh.

Chạy:  python -X utf8 -m tools.test_contract_release
Exit:  0 nếu tất cả check đạt; 1 nếu có check đỏ (hiện tại kỳ vọng 1 vì a,b đỏ).
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import docx  # python-docx

from tools.docx_render import LEFTOVER_RE, write_rendered

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
OUT_DIR = ROOT / "generated_ho_so" / "_contract_release"

PLAN13 = [
    "PLI_M01", "PLI_M03", "PLI_M04", "PLI_M05", "PLI_M12", "PLI_M17",
    "PLI_M19", "PLI_M21", "PLI_M23", "PLI_M25", "PLI_M72",
    "PLII_M02", "PLII_M07",
]
GROUP_OF = {
    "formation": ["PLI_M01", "PLI_M03", "PLI_M04", "PLI_M05"],
    "change": ["PLI_M12", "PLI_M17", "PLI_M19", "PLI_M21", "PLI_M23",
               "PLI_M25", "PLI_M72"],
    "household": ["PLII_M02", "PLII_M07"],
}
CANONICAL_LOOP = "ds_nganh"

# Tên metadata oneOf CHÍNH THỨC (chốt tại Integrate 1): `forms_oneOf` cấp case
# theo schema Agent 1B đã triển khai + test (app_web/test_form_flow.js);
# các tên cũ vẫn được nhận diện để tương thích ngược, không nới ngữ nghĩa.
ONEOF_CASE_KEYS = ("forms_oneOf", "one_of", "oneOf", "form_groups", "nhom_loai_tru")
ONEOF_FORM_KEYS = ("forms_oneOf", "one_of", "one_of_group", "oneOfGroup", "nhom_loai_tru")

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def fold(text: str) -> str:
    """'Tên ngành' -> 'ten nganh': bỏ dấu, lowercase, gộp khoảng trắng."""
    nfkd = unicodedata.normalize("NFD", text or "")
    plain = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", plain.replace("đ", "d").lower()).strip()


def load_form_maps() -> dict:
    return json.loads((APP / "data" / "form_maps.json").read_text(encoding="utf-8"))


def build_data_from_form_map(fmap: dict) -> tuple[dict, list[dict]]:
    """Dựng data render từ form_maps fields: field thường -> giá trị dummy,
    loop ds_nganh -> 3 dòng có đúng dòng đầu là ngành chính."""
    data: dict = {}
    for f in fmap.get("fields", []):
        key = f.get("key", "")
        if "." in key:
            continue  # key lồng nhau/thuộc loop: xử lý riêng bên dưới
        data[key] = "X" if f.get("type") == "chk" else "TEST"
    rows = [
        {"ma_nganh": "0111", "ten_nganh": "Trồng lúa nước TEST",
         "chi_tiet": "", "la_nganh_chinh": "X"},
        {"ma_nganh": "4711", "ten_nganh": "Bán lẻ thực phẩm TEST",
         "chi_tiet": "", "la_nganh_chinh": ""},
        {"ma_nganh": "4101", "ten_nganh": "Xây dựng công trình TEST",
         "chi_tiet": "", "la_nganh_chinh": ""},
    ]
    data[CANONICAL_LOOP] = rows
    return data, rows


def find_industry_table(document) -> "docx.table.Table | None":
    """Tìm bảng ngành: hàng tiêu đề có 'STT' và 'Ten nganh'."""
    for tbl in document.tables:
        if not tbl.rows:
            continue
        head = [fold(c.text) for c in tbl.rows[0].cells]
        if "stt" in head and any(h.startswith("ten nganh") for h in head):
            return tbl
    return None


@check("CONTRACT_PLII_M01_STT_X: STT 1/2/3 + dung MOT o X cot nganh chinh")
def t_plii_m01_stt_x():
    fmap = load_form_maps()["PLII_M01"]
    tpl = APP / fmap["template"]
    data, rows = build_data_from_form_map(fmap)
    out = OUT_DIR / "PLII_M01_contract.docx"
    write_rendered(tpl, data, out)

    leftovers = sorted(set(LEFTOVER_RE.findall(zipfile_safe_read(out))))
    assert not leftovers, \
        "render còn tag sót: %s" % ", ".join(leftovers[:10])

    document = docx.Document(str(out))
    tbl = find_industry_table(document)
    assert tbl is not None, "không tìm thấy bảng ngành nghề trong file render"

    head = [c.text.strip() for c in tbl.rows[0].cells]
    head_fold = [fold(h) for h in head]
    ten_col = next(i for i, h in enumerate(head_fold)
                   if h.startswith("ten nganh"))
    # Cột ngành chính: 'Ngành chính' hoặc 'Ngành, nghề kinh doanh chính'
    # (gộp dấu/khoảng trắng nên so theo từ, không theo chuỗi liền).
    def _is_primary_col(h: str) -> bool:
        return h == "nganh chinh" or (
            h.endswith("chinh") and "nganh" in h)
    primary_cols = [i for i, h in enumerate(head_fold) if _is_primary_col(h)]
    assert primary_cols, (
        "template PLII_M01 chưa có cột 'Ngành, nghề kinh doanh chính' "
        "(chưa map {la_nganh_chinh} vào bảng ngành) — EXPECTED-RED-BEFORE-1A"
    )
    pcol = primary_cols[0]

    planted = {r["ten_nganh"] for r in rows}
    data_rows = []
    for ri, row in enumerate(tbl.rows[1:], start=1):
        if row.cells[ten_col].text.strip() in planted:
            data_rows.append((ri, row))
    assert len(data_rows) == 3, (
        "mong đợi 3 dòng dữ liệu ds_nganh, thấy %d — EXPECTED-RED-BEFORE-1A"
        % len(data_rows)
    )

    stt_bad = []
    for i, (_, row) in enumerate(data_rows, start=1):
        got = row.cells[0].text.strip()
        if got != str(i):
            stt_bad.append((i, got))
    assert not stt_bad, (
        "ô STT sai/không được tự sinh: %s (template chưa có {_stt} ở hàng "
        "khuôn) — EXPECTED-RED-BEFORE-1A" % stt_bad
    )

    marks = [(i, row.cells[pcol].text.strip())
             for i, (_, row) in enumerate(data_rows, start=1)]
    x_rows = [i for i, v in marks if v == "X"]
    assert x_rows == [1], (
        "cột '%s' phải có đúng MỘT ô 'X' ở dòng 1, thấy %s (template chưa "
        "có {la_nganh_chinh}) — EXPECTED-RED-BEFORE-1A" % (head[pcol], marks)
    )
    print("   -> bảng ngành: %d cột, cột ngành chính = col %d (%r)"
          % (len(head), pcol, head[pcol]))


def zipfile_safe_read(path: Path) -> str:
    import zipfile
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, "zip hỏng (testzip != None)"
        return z.read("word/document.xml").decode("utf-8")


def _doc_id_to_ref(s: str):
    """'PLII_M01' -> ('II', 1); trả None nếu không khớp mẫu PL<pl>_M<mau>."""
    m = re.fullmatch(r"PL([IVX]+)_M(\d+)", str(s or "").strip())
    if not m:
        return None
    return (m.group(1), int(m.group(2)))


def oneof_groups_of_case(case: dict) -> list[list[tuple[int, int]]]:
    """Trả danh sách nhóm oneOf của case theo metadata (nếu đã khai).
    Hỗ trợ: case-level list nhóm; form-level tên nhóm gom lại.
    Contract chính thức (Integrate 1): forms_oneOf = [{ids:['PL.._M..',...], max:N}]."""
    for k in ONEOF_CASE_KEYS:
        v = case.get(k)
        if isinstance(v, list) and v:
            groups = []
            for g in v:
                refs = []
                if isinstance(g, dict) and isinstance(g.get("ids"), list):
                    # shape chính thức của Agent 1B: {ids:[doc_id...], max}
                    for s in g["ids"]:
                        ref = _doc_id_to_ref(s)
                        if ref:
                            refs.append(ref)
                else:
                    for item in (g if isinstance(g, list) else [g]):
                        if isinstance(item, dict) and "pl" in item and "mau" in item:
                            refs.append((item["pl"], item["mau"]))
                        elif isinstance(item, list) and len(item) >= 2:
                            refs.append((item[0], item[1]))
                if refs:
                    groups.append(refs)
            if groups:
                return groups
    by_name: dict[str, list[tuple[int, int]]] = {}
    for f in case.get("forms", []):
        for k in ONEOF_FORM_KEYS:
            g = f.get(k)
            if isinstance(g, str) and g:
                by_name.setdefault(g, []).append((f.get("pl"), f.get("mau")))
                break
    return [g for g in by_name.values() if len(g) >= 2]


@check("CONTRACT_FORMS_METADATA: bat_buoc(bool) day du + oneOf chuyen_doi_hkd_sang_dn")
def t_forms_metadata():
    uc = json.loads((APP / "data" / "use_cases.json").read_text(encoding="utf-8"))
    cases = uc.get("cases", [])
    assert cases, "use_cases.json không có case nào"

    missing_batbuoc: list[str] = []
    multi_optional_no_group: list[str] = []
    target_ok = False
    for cs in cases:
        forms = cs.get("forms", [])
        if not forms:
            continue
        for f in forms:
            if not isinstance(f.get("bat_buoc"), bool):
                missing_batbuoc.append("%s: PL%s-M%s"
                                       % (cs.get("id"), f.get("pl"), f.get("mau")))
        groups = oneof_groups_of_case(cs)
        n_opt = sum(1 for f in forms if f.get("bat_buoc") is False)
        if cs.get("id") == "chuyen_doi_hkd_sang_dn":
            target_ok = bool(groups) and any(
                len({ref for ref in g}) >= 2 for g in groups)
            if not target_ok:
                print("   -> case chuyen_doi_hkd_sang_dn có %d form "
                      "(pl,mau)=%s nhưng CHƯA khai nhóm loại-trừ (oneOf); "
                      "các key tìm kiếm: %s / %s"
                      % (len(forms),
                         [(f["pl"], f["mau"]) for f in forms],
                         ONEOF_CASE_KEYS, ONEOF_FORM_KEYS))
        elif n_opt >= 2 and not groups:
            multi_optional_no_group.append(cs.get("id"))

    assert not missing_batbuoc, (
        "các form thiếu khai báo bat_buoc (bool): %s" % missing_batbuoc)
    assert target_ok, (
        "case chuyen_doi_hkd_sang_dn phải có metadata nhóm loại-trừ (oneOf) "
        "trong use_cases.json/schema để UI chỉ cho chọn ĐÚNG MỘT loại hình "
        "sau chuyển đổi — HIỆN CHƯA CÓ — EXPECTED-RED-BEFORE-1B"
    )
    if multi_optional_no_group:
        # Cảnh báo thông tin (không fail): các case khác cũng có nhiều form
        # bat_buoc=false nhưng chưa có nhóm — Lead/Agent 1B xem xét.
        print("   -> CANH BAO: case khác có nhiều bat_buoc=false mà chưa có "
              "nhóm oneOf: %s" % multi_optional_no_group)


@check("INVENTORY_DS_NGANH: quet 87 blocks, doi chieu 13 mau PLAN.md (thong tin)")
def t_inventory_ds_nganh():
    blocks_dir = APP / "data" / "blocks"
    files = sorted(blocks_dir.glob("*.json"))
    assert len(files) == 87, "mong đợi 87 block file, thấy %d" % len(files)

    loops_by_form: dict[str, list[str]] = {}
    structural_err: list[str] = []
    for p in files:
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            structural_err.append("%s: parse lỗi %r" % (p.name, exc))
            continue
        fid = b.get("id", p.stem)
        names: list[str] = []
        for blk in b.get("blocks", []):
            if blk.get("t") != "loop":
                continue
            name = blk.get("loop")
            if not name:
                structural_err.append("%s: block loop thiếu tên loop" % p.name)
                continue
            if not blk.get("cols"):
                structural_err.append("%s: loop %s thiếu cols" % (p.name, name))
            names.append(name)
        loops_by_form[fid] = names
    assert not structural_err, "lỗi cấu trúc blocks: %s" % structural_err

    has_canonical = {f for f, ns in loops_by_form.items()
                     if CANONICAL_LOOP in ns}
    missing = [f for f in PLAN13 if f not in has_canonical]

    print("   -> mẫu có loop %s: %s" % (CANONICAL_LOOP, sorted(has_canonical)))
    print("   -> thiếu %s: %d/%d mẫu theo PLAN.md"
          % (CANONICAL_LOOP, len(missing), len(PLAN13)))
    for grp in ("formation", "change", "household"):
        ids = GROUP_OF[grp]
        mark = ["%-9s:%s" % (f, "THIEU" if f in missing else "co") for f in ids]
        print("      %-10s(%d): %s" % (grp, len(ids), "; ".join(mark)))

    unexpected_lost = sorted(set(has_canonical) & set(missing))
    assert not unexpected_lost, "mâu thuẫn nội bộ: %s" % unexpected_lost
    assert set(missing) <= set(PLAN13), (
        "có mẫu ngoài danh sách PLAN.md bị thiếu %s: %s"
        % (CANONICAL_LOOP, sorted(set(missing) - set(PLAN13))))
    assert set(PLAN13) <= set(loops_by_form), (
        "các mẫu PLAN.md không tồn tại trong blocks: %s"
        % sorted(set(PLAN13) - set(loops_by_form)))

    # Các loop khác nghĩa với ds_nganh — LIỆT KÊ RIÊNG, không đề xuất gộp.
    other: dict[str, list[str]] = {}
    for fid, ns in sorted(loops_by_form.items()):
        for n in ns:
            if n != CANONICAL_LOOP:
                other.setdefault(n, []).append(fid)
    print("   -> các loop khác (liệt kê riêng, KHÔNG gộp với ds_nganh):")
    for n, fs in sorted(other.items()):
        print("      %-20s -> %d mẫu: %s" % (n, len(fs), ", ".join(fs)))
    industry_named = {n: fs for n, fs in other.items() if "nganh" in n}
    if not industry_named:
        print("      -> KHÔNG phát hiện loop tên nganh_* (bo_sung/xoa_bo/"
              "truoc_thay_doi) trong dữ liệu hiện tại — chỉ PLAN.md dự liệu "
              "cho Wave 2B, cần tạo mới khi có căn cứ nghiệp vụ.")
    else:
        print("      -> loop chứa 'nganh' khác nghĩa: %s"
              % {k: v for k, v in sorted(industry_named.items())})


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        t_plii_m01_stt_x,
        t_forms_metadata,
        t_inventory_ds_nganh,
    ):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("Contract release: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    red_expected = ("(a) CONTRACT_PLII_M01_STT_X va (b) CONTRACT_FORMS_METADATA "
                    "duoc THIET KE de DO truoc khi merge Agent 1A (docx-plii-m01) "
                    "va Agent 1B (form-flow-state); phai XANH sau Integrate 1.")
    print("GHI CHU:", red_expected)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
