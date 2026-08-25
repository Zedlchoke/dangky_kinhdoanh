"""Nạp dữ liệu đọc-chỉ (use_cases, form_maps) và tiện ích hồ sơ nháp."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

# <root>/app_tk/engine_io.py -> <root>/app
APP_DIR = Path(__file__).resolve().parent.parent / "app"
ROOT_DIR = APP_DIR.parent
USE_CASES_PATH = APP_DIR / "data" / "use_cases.json"
FORM_MAPS_PATH = APP_DIR / "data" / "form_maps.json"
GENERATED_DIR = ROOT_DIR / "generated_ho_so"
PROFILES_DIR = ROOT_DIR / "profiles"


def load_use_cases() -> dict:
    return json.loads(USE_CASES_PATH.read_text(encoding="utf-8"))


def load_form_maps() -> dict:
    return json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))


VSIC_PATH = APP_DIR / "data" / "nganh_vsic.json"
_VSIC_CACHE: list[tuple[str, str, int]] | None = None


def load_nganh_vsic() -> list[tuple[str, str, int]]:
    """Danh mục ngành VSIC [(ma, ten, cap)] — nạp JSON đúng 1 lần rồi cache."""
    global _VSIC_CACHE
    if _VSIC_CACHE is None:
        items: list[tuple[str, str, int]] = []
        try:
            raw = json.loads(VSIC_PATH.read_text(encoding="utf-8"))
            for it in raw.get("nganh", []):
                items.append((str(it.get("ma", "")), str(it.get("ten", "")),
                              int(it.get("cap", 4))))
        except Exception as exc:  # noqa: BLE001 — thiếu file thì tra cứu tắt
            print("Không nạp được nganh_vsic.json:", exc)
        _VSIC_CACHE = items
    return _VSIC_CACHE


def form_map_id(pl: str, mau: int) -> str:
    """Mã form map từ (phụ lục, số mẫu), vd ("I", 2) -> "PLI_M02"."""
    return "PL%s_M%02d" % (pl, int(mau))


def forms_of_case(case: dict, maps: dict) -> list[dict]:
    """Ghép từng mẫu của case với form map tương ứng.

    Trả về list dict: {pl, mau, bat_buoc, ghi_chu, map_id, map}.
    `map` có thể là None nếu thiếu trong form_maps (bỏ qua khi xuất).
    """
    out = []
    for f in case.get("forms", []):
        mid = form_map_id(f.get("pl", "I"), f.get("mau", 0))
        out.append(
            {
                "pl": f.get("pl", "I"),
                "mau": f.get("mau", 0),
                "bat_buoc": bool(f.get("bat_buoc")),
                "ghi_chu": f.get("ghi_chu", ""),
                "map_id": mid,
                "map": maps.get(mid),
            }
        )
    return out


def slugify(text: str, max_len: int = 60) -> str:
    """Chuyển tên tiếng Việt thành chuỗi tên file an toàn."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text[:max_len].strip("_") or "mau"


def nested_set(d: dict, dotted_key: str, value) -> None:
    """Gán giá trị vào dict lồng nhau theo key dạng 'a.b.c'."""
    parts = dotted_key.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def nested_get(d: dict, dotted_key: str):
    """Lấy giá trị lồng nhau 'a.b.c'; trả None nếu thiếu."""
    cur = d
    for p in dotted_key.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def draft_path(case_id: str) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR / ("%s_draft.json" % case_id)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
