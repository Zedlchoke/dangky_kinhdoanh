# -*- coding: utf-8 -*-
"""Wave X1 — test lớp questionnaire (PLAN.md mục 4, gate: "khung khớp 100%
data-key có trong registry; question chưa có data-key = fail build").

[Q1] Artifact generated `app/data/questionnaire/PLI_M72.json`:
     - đúng schema v1, cluster cụm đầu owner duyệt (E6, 2026-08-28);
     - 24 câu (draft 23 + tách "ngày cấp / nơi cấp" thành 2 câu theo nguyên
       tắc "một câu một ý"), 4 nhóm đời thường, row_group `nganh` 3 câu;
     - 100% data_key thuộc form_maps[PLI_M72].fields (hoặc SELECTOR_ALLOW
       cho metadata hồ sơ dn.loai_hinh — FORM_SELECTOR_META).

[Q2] Registry fail-loud (validate() raise QuestionnaireError mã lỗi đúng):
     thiếu data_key / key lạ / question_id trùng / type lạ / when trỏ câu
     hỏi không tồn tại / select không có options / doc không có trong
     form_maps / questionnaire_version lạ.

[Q3] Builder: artifact regenerate ×2 zero-diff (generated hygiene);
     cluster nguồn hỏng (key lạ) → exit 1 và KHÔNG ghi artifact.

[Q4] When-target phủ đủ 5 biến thể loai_hinh cho 3 câu ngành và đúng tách
     von_dau_tu_so (DNTN) vs von_dieu_le (còn lại) theo blocks PLI_M72.

Chạy:  python3 -X utf8 -m tools.test_questionnaire      (exit 0 = PASS)
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.questionnaire.build_questionnaire import build_one  # noqa: E402
from tools.questionnaire.schema import (  # noqa: E402
    QuestionnaireError, load_form_maps, validate)

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


FORM_MAPS = load_form_maps(ROOT)
ARTIFACT = ROOT / "app" / "data" / "questionnaire" / "PLI_M72.json"
CLUSTER = ROOT / "tools" / "questionnaire" / "clusters" / "thanh_lap_doanh_nghiep.json"


def load_q() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def must_raise(code: str, q: dict) -> None:
    try:
        validate(q, FORM_MAPS)
    except QuestionnaireError as exc:
        assert exc.code == code, "đòi mã %s, nhận %s (%s)" % (
            code, exc.code, exc)
        return
    raise AssertionError("không raise (đòi mã %s)" % code)


@check("[Q1a] artifact đúng schema + validate sạch đối chiếu registry")
def q1a():
    q = load_q()
    assert q["doc_id"] == "PLI_M72" and q["questionnaire_version"] == 1
    assert validate(q, FORM_MAPS) == []


@check("[Q1b] đủ 24 câu cụm đầu, 4 nhóm, row_group nganh 3 câu, id duy nhất")
def q1b():
    q = load_q()
    ids = [x["question_id"] for x in q["questions"]]
    assert len(ids) == 24 and len(set(ids)) == 24, "có %d câu" % len(ids)
    groups = []
    for x in q["questions"]:
        if x["group"] not in groups:
            groups.append(x["group"])
    assert len(groups) == 4, groups
    nganh = [x["question_id"] for x in q["questions"]
             if x.get("row_group") == "nganh"]
    assert sorted(nganh) == ["q_nganh_chinh", "q_nganh_ma", "q_nganh_ten"]
    assert all(x.get("repeatable") for x in q["questions"]
               if x.get("row_group") == "nganh")


@check("[Q1c] 100% data_key thuộc form_maps[PLI_M72] (dn.loai_hinh = selector)")
def q1c():
    q = load_q()
    allowed = {f.get("key") for f in FORM_MAPS["PLI_M72"]["fields"] if f.get("key")}
    allowed.add("dn.loai_hinh")  # SELECTOR_ALLOW — metadata hồ sơ D-M72-ACT
    for x in q["questions"]:
        dk = x["data_key"]
        targets = dk if isinstance(dk, list) else [{"key": dk}]
        for t in targets:
            assert t["key"] in allowed, "%s: %s" % (x["question_id"], t["key"])


@check("[Q2a] thiếu data_key -> fail-loud (MISSING_FIELD/NO_DATA_KEY)")
def q2a():
    q = load_q()
    bad = copy.deepcopy(q)
    del bad["questions"][1]["data_key"]
    must_raise("MISSING_FIELD", bad)
    bad2 = copy.deepcopy(q)
    bad2["questions"][1]["data_key"] = []
    must_raise("NO_DATA_KEY", bad2)


@check("[Q2b] key lạ -> KEY_NOT_IN_REGISTRY (không có trong form_maps)")
def q2b():
    q = load_q()
    bad = copy.deepcopy(q)
    bad["questions"][1]["data_key"] = "dn.khong_ton_tai"
    must_raise("KEY_NOT_IN_REGISTRY", bad)


@check("[Q2c] question_id trùng -> DUP_ID; type lạ -> BAD_TYPE; "
       "select thiếu options -> NO_OPTIONS")
def q2c():
    q = load_q()
    bad = copy.deepcopy(q)
    bad["questions"][2]["question_id"] = bad["questions"][1]["question_id"]
    must_raise("DUP_ID", bad)
    bad2 = copy.deepcopy(q)
    bad2["questions"][1]["type"] = "sobolan"
    must_raise("BAD_TYPE", bad2)
    bad3 = copy.deepcopy(q)
    del bad3["questions"][0]["options"]
    must_raise("NO_OPTIONS", bad3)


@check("[Q2d] when trỏ câu hỏi không tồn tại -> BAD_WHEN; "
       "doc lạ -> DOC_NOT_FOUND; version lạ -> BAD_VERSION")
def q2d():
    q = load_q()
    bad = copy.deepcopy(q)
    bad["questions"][1]["data_key"] = [
        {"key": "dn.ten_viet_tat", "when": {"vn.khong_co": ["X"]}}]
    must_raise("BAD_WHEN", bad)
    bad2 = copy.deepcopy(q)
    bad2["doc_id"] = "PLI_M99"
    must_raise("DOC_NOT_FOUND", bad2)
    bad3 = copy.deepcopy(q)
    bad3["questionnaire_version"] = 99
    must_raise("BAD_VERSION", bad3)


@check("[Q3a] builder regenerate ×2 zero-diff (generated hygiene)")
def q3a():
    out1 = build_one(CLUSTER, FORM_MAPS, write=False)[1]
    out2 = build_one(CLUSTER, FORM_MAPS, write=False)[1]
    assert out1 == out2, "hai lần build khác nhau"
    assert out1 + "\n" == ARTIFACT.read_text(encoding="utf-8"), \
        "artifact trên đĩa lệch nguồn cluster (cần regen?)"


@check("[Q3b] cluster nguồn hỏng -> QuestionnaireError, không ghi artifact")
def q3b():
    import tempfile
    bad = load_q()
    bad["questions"][1]["data_key"] = "vung.khong.thuc"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "bad_cluster.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        try:
            build_one(p, FORM_MAPS, write=True)
        except QuestionnaireError as exc:
            assert exc.code == "KEY_NOT_IN_REGISTRY", exc.code
        else:
            raise AssertionError("builder không fail-loud")
        assert not (Path(tmp) / "PLI_M72.json").exists(), "đã ghi artifact hỏng"


@check("[Q4] 3 câu ngành phủ đủ 5 biến thể; von tách đúng DNTN/còn lại")
def q4():
    q = load_q()
    by_id = {x["question_id"]: x for x in q["questions"]}
    variants = ["DNTN", "TNHH_1TV", "TNHH_2TV", "CTCP", "DHDN"]
    for qid in ("q_nganh_ten", "q_nganh_ma", "q_nganh_chinh"):
        whens = [t["when"]["dn.loai_hinh"][0]
                 for t in by_id[qid]["data_key"]]
        assert sorted(whens) == sorted(variants), "%s: %s" % (qid, whens)
    von = {t["key"]: t["when"]["dn.loai_hinh"] for t in by_id["q_von"]["data_key"]}
    assert von["von_dau_tu_so"] == ["DNTN"]
    assert sorted(von["von_dieu_le"]) == sorted(variants[1:])
    # person: DNTN+TNHH_1TV qua chu_hkd/ho_ten_in_hoa, còn lại qua ndd.*
    ht = {t["key"]: t["when"]["dn.loai_hinh"] for t in by_id["q_ho_ten"]["data_key"]}
    assert sorted(ht["ho_ten_in_hoa"]) == ["DNTN", "TNHH_1TV"]
    assert sorted(ht["ndd.ho_ten"]) == ["CTCP", "DHDN", "TNHH_2TV"]


# ---------------------------------------------------------------------------
# [O7 2026-09-06] P6=C rollout cụm 1 (hộ kinh doanh) + cụm 3 (thuế):
# 4 questionnaire mới + manifest blocked-chờ-migration (TT121/2026).
# ---------------------------------------------------------------------------

CLUSTER_DIR = ROOT / "tools" / "questionnaire" / "clusters"
OUT_DIR = ROOT / "app" / "data" / "questionnaire"
NEW_CLUSTER_DOCS = {
    "hkd_dang_ky_moi.json": "PLII_M01",
    "hkd_thay_doi_noi_dung.json": "PLII_M02",
    "hkd_tam_ngung_tiep_tuc.json": "PLII_M03",
    "hkd_cham_dut.json": "PLII_M04",
    # [P6=C 2026-09-06] cụm thay đổi ngành (M12) + cụm thuế (M27)
    "thay_doi_nganh.json": "PLI_M12",
    "thue_dang_ky.json": "PLI_M27",
}
BLOCKED_MANIFEST = CLUSTER_DIR / "blocked_tt121_migration.json"


@check("[Q5a] O7: cụm hộ KD + cụm P6=C validate sạch + artifact khớp nguồn")
def q5a():
    for fname, doc_id in NEW_CLUSTER_DOCS.items():
        src = json.loads((CLUSTER_DIR / fname).read_text(encoding="utf-8"))
        assert src["doc_id"] == doc_id, fname
        assert validate(src, FORM_MAPS) == [], fname
        artifact = OUT_DIR / (doc_id + ".json")
        assert artifact.exists(), "thiếu artifact %s" % artifact
        built = build_one(CLUSTER_DIR / fname, FORM_MAPS, write=False)[1]
        assert built + "\n" == artifact.read_text(encoding="utf-8"), \
            "%s: artifact lệch nguồn cluster (cần regen)" % fname


@check("[Q5b] O7: cụm thuế — chỉ tiêu đăng ký thuế 5.1/5.2 hỏi giá trị MỚI "
       "trong PLII_M02, KHÔNG hỏi giá trị cũ")
def q5b():
    q = json.loads((OUT_DIR / "PLII_M02.json").read_text(encoding="utf-8"))
    keys = []
    for x in q["questions"]:
        dk = x["data_key"]
        for t in (dk if isinstance(dk, list) else [dk]):
            keys.append(t["key"] if isinstance(t, dict) else t)
    tax_moi = [k for k in keys if k.startswith("thue_chi_tieu_cu_moi.") and
               k.endswith(".thong_tin_dang_ky_moi")]
    assert len(tax_moi) >= 2, tax_moi
    assert not any(k.endswith(".thong_tin_dang_ky_cu") for k in keys), \
        "không được hỏi khách giá trị CŨ (app tự điền từ hồ sơ)"


@check("[Q5c] O7: manifest blocked — 9 mẫu đã migrate nên `blocked` RỖNG có "
       "chủ đích + ghi chú M11 REMOVED_BY_CURRENT_LAW")
def q5c():
    m = json.loads(BLOCKED_MANIFEST.read_text(encoding="utf-8"))
    assert m.get("blocked_version") == 1
    assert m["blocked"] == [], \
        "còn form blocked dù 9 mẫu đã migrate (merge e268038): %s" % m["blocked"]
    # sổ theo dõi: released ghi nhận 5 doc từng bị chặn đã gỡ
    released = {e["doc_id"] for e in m.get("released", [])}
    assert {"PLI_M01", "PLI_M02", "PLI_M03", "PLI_M04", "PLI_M12"} <= released
    removed = {e["doc_id"]: e for e in m.get("removed_by_current_law", [])}
    assert "PLI_M11" in removed, "thiếu ghi chú M11"
    assert removed["PLI_M11"].get("verdict") == "REMOVED_BY_CURRENT_LAW", \
        removed["PLI_M11"]


@check("[Q5d] O7: sau khi gỡ blocked, PLI_M12/PLI_M27 CÓ artifact questionnaire")
def q5d():
    for doc_id in ("PLI_M12", "PLI_M27"):
        p = OUT_DIR / (doc_id + ".json")
        assert p.exists(), "thiếu artifact %s (chạy builder trước?)" % p


@check("[Q5e] O7: builder fail-loud DOC_BLOCKED nếu cluster trỏ form blocked "
       "(guard giữ nguyên — kiểm bằng manifest tổng hợp)")
def q5e():
    import tempfile
    bad = {
        "doc_id": "PLI_M12", "title": "cluster lan can form blocked",
        "questionnaire_version": 1,
        "questions": [{
            "question_id": "q_x", "group": "g", "text": "t", "type": "text",
            "version": 1, "data_key": "so_van_ban"}],
    }
    # hình dạng y hệt load_blocked() trả về — guard không phụ thuộc manifest
    # thật (hiện rỗng) mà chạy trên entry blocked bất kỳ.
    synthetic_blocked = {
        "PLI_M12": {"doc_id": "PLI_M12", "cluster": "test",
                    "procedures": ["x"], "reason": "TT121 chờ migrate",
                    "manifest": "blocked_tong_hop.json"},
    }
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "bad_cluster.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        try:
            build_one(p, FORM_MAPS, write=True, blocked=synthetic_blocked)
        except QuestionnaireError as exc:
            assert exc.code == "DOC_BLOCKED", exc.code
        else:
            raise AssertionError("builder không chặn form blocked")
        assert not (Path(tmp) / "PLI_M12.json").exists()


# ---------------------------------------------------------------------------
# [P6=C 2026-09-06 — f4xl] Cụm 2 'thay đổi ngành' (PLI_M12) + cụm 3 'thuế'
# (PLI_M27): mapping thủ tục→form→questionnaire, verdict N/A có reason,
# version câu hỏi 20260906, M12 hỏi đủ phần ngành + 7 chỉ tiêu thuế.
# ---------------------------------------------------------------------------

Q_M12 = json.loads((OUT_DIR / "PLI_M12.json").read_text(encoding="utf-8")) \
    if (OUT_DIR / "PLI_M12.json").exists() else None
Q_M27 = json.loads((OUT_DIR / "PLI_M27.json").read_text(encoding="utf-8")) \
    if (OUT_DIR / "PLI_M27.json").exists() else None

CHANGE_PROCEDURES = ["thay_doi_nganh_nghe", "thay_doi_ten_va_tru_so",
                     "thay_doi_von_dieu_le", "bo_sung_cap_nhat_thong_tin_dkdn"]
TAX_KEYS_M12 = ("chk_doi_dia_chi_tb_thue", "ngay_bd", "chk_ht_doc_lap",
                "ap_dung_tu", "so_lao_dong", "chk_co", "chk_gtgt_khoan_tru")


def _q6_all_keys(q: dict) -> list[str]:
    keys = []
    for x in q["questions"]:
        dk = x["data_key"]
        for t in (dk if isinstance(dk, list) else [{"key": dk}]):
            keys.append(t["key"] if isinstance(t, dict) else t)
    return keys


@check("[Q6a] P6=C: cụm thay đổi ngành/thuế validate sạch + artifact khớp nguồn")
def q6a():
    for fname in ("thay_doi_nganh.json", "thue_dang_ky.json"):
        src = json.loads((CLUSTER_DIR / fname).read_text(encoding="utf-8"))
        assert src["doc_id"] == NEW_CLUSTER_DOCS[fname], fname
        assert validate(src, FORM_MAPS) == [], fname
        artifact = OUT_DIR / (src["doc_id"] + ".json")
        assert artifact.exists(), "thiếu artifact %s" % artifact
        built = build_one(CLUSTER_DIR / fname, FORM_MAPS, write=False)[1]
        assert built + "\n" == artifact.read_text(encoding="utf-8"), \
            "%s: artifact lệch nguồn cluster (cần regen)" % fname


@check("[Q6b] P6=C: mọi procedure trong mapping có verdict QUESTIONNAIRE "
       "hoặc N/A kèm reason (không im lặng)")
def q6b():
    for fname in ("thay_doi_nganh.json", "thue_dang_ky.json"):
        src = json.loads((CLUSTER_DIR / fname).read_text(encoding="utf-8"))
        assert src.get("procedures"), fname
        for pr in src["procedures"]:
            assert pr.get("verdict") in ("QUESTIONNAIRE", "N/A"), pr
            if pr["verdict"] == "N/A":
                assert pr.get("reason"), "N/A phải có reason: %s" % pr
                assert not pr.get("questionnaire"), \
                    "N/A thì không trỏ questionnaire: %s" % pr
            else:
                assert pr.get("questionnaire"), \
                    "QUESTIONNAIRE phải trỏ file: %s" % pr


@check("[Q6c] P6=C: 4 thủ tục change-DN đều trỏ PLI_M12 -> thay_doi_nganh.json")
def q6c():
    src = json.loads((CLUSTER_DIR / "thay_doi_nganh.json")
                     .read_text(encoding="utf-8"))
    mapped = {pr["id"] for pr in src["procedures"]
              if pr["verdict"] == "QUESTIONNAIRE"}
    for pid in CHANGE_PROCEDURES:
        assert pid in mapped, "thiếu thủ tục %s" % pid


@check("[Q6d] P6=C: M12 hỏi đủ 3 lưới ngành + 7 chỉ tiêu thuế (địa chỉ TB "
       "thuế, ngày bắt đầu hoạt động, hạch toán, năm tài chính, lao động, "
       "BOT, GTGT) — đúng yêu cầu owner")
def q6d():
    keys = set(_q6_all_keys(Q_M12))
    for grid in ("nganh_bo_sung.", "nganh_xoa_bo.", "nganh_sua_doi_chi_tiet."):
        assert any(k.startswith(grid) for k in keys), "thiếu lưới %s" % grid
    for tax_key in TAX_KEYS_M12:
        assert tax_key in keys, "thiếu chỉ tiêu thuế %s" % tax_key
    assert "nam_bd" in keys and "chk_gtgt_khong_phai_nop" in keys


@check("[Q6e] P6=C: version câu hỏi 20260906 (int của 2026.09.06) trên CẢ 2 "
       "cụm mới; cụm cũ giữ nguyên version 1")
def q6e():
    for fname in ("thay_doi_nganh.json", "thue_dang_ky.json"):
        src = json.loads((CLUSTER_DIR / fname).read_text(encoding="utf-8"))
        assert src.get("content_version") == "2026.09.06", fname
        for x in src["questions"]:
            assert x["version"] == 20260906, \
                "%s/%s: version %r" % (fname, x["question_id"], x["version"])
    old = json.loads((CLUSTER_DIR / "hkd_thay_doi_noi_dung.json")
                     .read_text(encoding="utf-8"))
    assert all(x["version"] == 1 for x in old["questions"])


@check("[Q6f] P6=C: cụm thuế — tam ngừng DN có questionnaire (M27), phần thuế "
       "M27 N/A có reason, phần đăng ký thuế thật sự nằm ở M12")
def q6f():
    src = json.loads((CLUSTER_DIR / "thue_dang_ky.json")
                     .read_text(encoding="utf-8"))
    by_id = {pr["id"]: pr for pr in src["procedures"]}
    assert by_id["tam_ngung_tiep_tuc_kinh_doanh_dn"]["verdict"] == \
        "QUESTIONNAIRE"
    na = by_id["tam_ngung_tiep_tuc_kinh_doanh_dn:phan_thue"]
    assert na["verdict"] == "N/A" and na["reason"], na
    assert by_id["thay_doi_thong_tin_dang_ky_thue"]["form"] == "PLI_M12"
    # không hỏi khách ô thuế không tồn tại trên M27
    keys = set(_q6_all_keys(src))
    assert not any("thue" in k for k in keys), keys


def main() -> int:
    for fn in (q1a, q1b, q1c, q2a, q2b, q2c, q2d, q3a, q3b, q4,
               q5a, q5b, q5c, q5d, q5e, q6a, q6b, q6c, q6d, q6e, q6f):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_questionnaire: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
