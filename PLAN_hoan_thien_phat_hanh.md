# Kế hoạch hoàn thiện và phát hành — Word, Excel, Windows `.exe`, macOS `.app`

> **CẬP NHẬT TRIỂN KHAI 2026-09-10 (sau wave W1 + E0–E3 + P0/P1-prep):**
> Baseline kiểm tra lại tại `main@d7ec076` (đã pull origin, tree sạch): runner
> **68 PASS / 1 FAIL** — FAIL duy nhất là H7.4 (4 file của `d7ec076` thiếu
> entry manifest diff; đã đồng bộ trong wave W1). Số liệu "61/4 FAIL cần
> soffice" ở bản plan gốc đã **stale**: LibreOffice 26.8.0.3 có sẵn tại
> `/opt/homebrew/bin/soffice` — W0 ĐÓNG (manifest môi trường
> `docs/audits/w0_env_manifest_2026-09-10.md`).
>
> **Đã xong (evidence thật, commit riêng từng wave trên main):**
> - **W1 (commit `2c58a1d`)** — corpus v3 `phase10_contact` 450 record
>   (90 render-unit × 5 fixture) từ HEAD sạch: HARD 0, candidate 7 đã
>   adjudicate (D9 M10 ×5 pixel-OK; D5 M45 ×2 allowlist (i)), determinism ×2
>   450/450, ZIP 37/37, PNG 1717==đĩa; sweep nhãn Email/Website **67/86 form,
>   173 occurrence PASS** (NBSP sống sót LO normalize, 2 lớp kiểm chứng
>   DOCX+PDF qua Bridge.export) —
>   `docs/audits/phase10_contact_corpus_2026-09-10.md`; A-8 trim M45/M53
>   registry-gated (M45 empty-paper 2→1 trang; M53 còn ~1–3pt chờ owner P1.2
>   A4 geometry); F7-N3/N5 đóng. Human sign-off corpus v3 vẫn
>   **NOT_REVIEWED** (O5).
> - **Excel E0–E3 (commit `8c41da2`)** — workbook case-level: manifest
>   `app/data/case_questionnaires/` 28 case (id/version/sha256, per-form
>   `content_review`); exporter `Hướng_dẫn / Thông_tin_chung /
>   01_<tên mẫu> / Giấy_tờ_cần_gửi (watermark CHỜ DUYỆT) + __map/__lists
>   veryHidden` + CHECKSUM sha256 + shared-key mirror + escape `=,+,-,@`;
>   importer verify contract/checksum TRƯỚC khi đọc, 14 mã lỗi fail-loud,
>   tái tạo candidate draft v2 NGUYÊN TỬ (không merge vào draft; UI confirm
>   = nút hủy duy nhất); bridge truyền `case_id` (sanitize đường dẫn); audit
>   jsonl chỉ hash/đếm không PII; 33 test mới (6+10+17) + JS suites giữ xanh.
>   **9 case READY, 19 case PENDING** (gate E4 CASE_NOT_READY — không phát
>   hành file khuyết). Compat Excel Desktop/Calc thật + visual workbook còn
>   **NOT RUN** (máy không có Excel).
> - **P0/P1-prep (commit `1075b78`)** — macOS handoff kit
>   `tools/macos_handoff/` + **build `.app` THẬT trên máy dev** (windowed
>   onedir, 629 file, repro ×2 chỉ khác timestamp/ad-hoc signature); engine
>   probe 11/11 trong bundle (DOCX PLI_M72 + PDF soffice + Excel round-trip
>   48 ô); GUI launch ×2, rescue-copy, S-path Unicode+space PASS; **S2–S6
>   visual / S7 offline thật / S8 clean-machine = NOT RUN** chờ người chạy
>   điền verdict. Windows kit: +S6b Excel case-level, spec đủ
>   hiddenimports/datas (phase5r_expectations, questionnaire, layout_roles,
>   docx, excel_case_* điều kiện). Windows `.exe` S1–S8 vẫn **NOT RUN**
>   (không có máy Windows) — đúng blocker plan gốc.
> - **Integration (commit hiện tại)** — đăng ký 6 suite mới vào release
>   runner (excel_case ×3, contact_label_corpus, a8_trailing_sig_trim,
>   f7_notes → **75 suite**), manifest H7 đồng bộ, `open_dir` đa platform,
>   `.gitignore` +`build/`,`dist/`.
>
> **CẬP NHẬT E4/E5 (2026-09-10, owner "duyệt và chốt hết" — xem
> `docs/decision_registry.md` mục 2026-09-10):**
> - **E5 ĐÓNG mức kỹ thuật**: questionnaire sinh cho đủ 21 form còn thiếu
>   (1.141 câu, phủ 100% key fillable — generator
>   `tools/build_form_questionnaires.py`, provenance `content_note` trong từng
>   file, `content_review=owner_delegated_2026-09-10`); **28/28 case READY**;
>   oneOf hiện thực trên workbook (select "Trường hợp hồ sơ" → checkedForms,
>   STRAY_CELL fail-loud); `Giấy_tờ_cần_gửi` in checklist thật + nguồn pháp
>   lý; UI ngừng xuất Excel v1 (giữ nạp v1 chuyển đổi).
> - **Tương thích LibreOffice Calc**: round-trip 5/5 case PASS — giá trị,
>   number_format "@", named range, data validation, protection và CHECKSUM
>   `__map` sống sót qua Calc re-save; rấtHidden→hidden được chấp nhận có ghi
>   audit (chặn visible). Gate visual workbook: 28/28 case xuất PDF/PNG +
>   contact sheet (`docs/audits/excel_case_visual_2026-09-10.md`); WARN page-
>   overflow (sheet rộng hơn A4 dọc — đề xuất fitToWidth, chưa áp) và MANUAL
>   NOT RUN cho phần cần nhìn mắt trên Excel thật (zoom 100%/125%, dropdown,
>   màu, watermark).
> - Excel Desktop Windows / Excel-for-Mac thật: vẫn **NOT RUN** (không có máy).
>
> **Kết luận hiện tại: TECHNICALLY_READY-PARTIAL / RELEASE_NOT_DONE.** Còn
> mở: human visual sign-off corpus v3 (O5) + visual workbook phần MANUAL;
> Windows S1–S8 (O6 — cần máy Windows); macOS S2–S8 manual verdict; Excel
> Desktop/Mac thật; fitToWidth cho sheet rộng (đề xuất); M53/A4 geometry.
> Không tuyên bố `RELEASE_DONE` cho tới khi toàn bộ gate có bằng chứng PASS.

> Lập ngày 10/09/2026, sau kiểm tra tại `main@3f4af84`.
>
> **Verdict đầu vào:** chưa phát hành. Release runner tại máy kiểm tra là
> **61 PASS / 4 FAIL**: bốn failure đều cần `soffice` để xuất/kiểm PDF.
> Corpus Word trước đó không còn là bằng chứng đầy đủ cho HEAD vì sau corpus
> đã thay header của 23 template. Excel mới có 7 questionnaire, trong khi
> 28 case hiện tham chiếu 27 form khác nhau (21 form chưa có questionnaire).

Kế hoạch này bổ sung và cụ thể hóa các gate F3–F7 trong `PLAN.md`; không thay
thế các quyết định pháp lý đã chốt trong registry. Không gọi sản phẩm là
`RELEASE_DONE` trước khi toàn bộ gate cuối cùng PASS bằng evidence thật.

## 1. Mục tiêu phát hành

Người vận hành phải có thể:

1. Chọn một trong 28 case.
2. Xuất **một Excel duy nhất cho cả hồ sơ/case** để gửi khách.
3. Khách điền Excel trên Microsoft Excel hoặc LibreOffice Calc.
4. Nạp lại file, ứng dụng tái tạo đầy đủ case, mẫu được chọn, dữ liệu đơn,
   checkbox/radio và mọi hàng bảng lặp, rồi chỉ ra phần còn thiếu.
5. Xuất DOCX/PDF/ZIP không lẫn mẫu, không vỡ bảng/trang và mở được bằng Word.
6. Chạy offline bằng `.exe` trên Windows và `.app` trên macOS.

`state`/draft JSON v2 là nguồn chân lý. Excel là kênh thu thập dữ liệu, không
phải database hay nguồn để suy đoán cấu trúc biểu mẫu.

## 2. Quyết định sản phẩm Excel

### 2.1 Một workbook theo case, không theo form đang mở

Thiết kế hiện tại xuất `currentDocId()` nên chỉ tạo được phiếu cho một mẫu;
không đáp ứng hồ sơ có nhiều mẫu. Thay bằng:

```
case được chọn
  └─ questionnaire manifest của case
       ├─ các trường dùng chung (chỉ hỏi một lần)
       ├─ các nhóm câu hỏi của mẫu bắt buộc/tùy chọn đang active
       └─ rules chọn mẫu / oneOf / activeWhen
  └─ DKKD_<caseId>_<schema-version>.xlsx
       └─ import nguyên tử → draft v2 → validate → DOCX/ZIP
```

Các sheet công khai:

| Sheet | Mục đích |
|---|---|
| `Hướng_dẫn` | 5–7 bước ngắn, màu sắc, cách trả file và thông tin phiên bản. |
| `Thông_tin_chung` | Dữ liệu dùng chung như tên, mã số, địa chỉ, người ký. Không lặp lại ở nhiều mẫu. |
| `01_<tên thủ tục>` … | Chỉ các câu áp dụng với form/mẫu đang chọn; một sheet cho một cụm nghiệp vụ, không buộc khách đọc nhãn pháp lý. |
| `Giấy_tờ_cần_gửi` | Checklist chỉ hiển thị khi danh mục đã được legal/product duyệt. |
| `__map` *(veryHidden)* | Khoá contract machine-readable: schema, case, selected forms, question id, key, transforms, row group, checksum. |
| `__lists` *(veryHidden)* | Danh mục cho dropdown; không đưa công thức/logic ẩn vào vùng khách điền. |

Chỉ ô vàng được mở khoá để nhập. Ô xám là computed/autofill và read-only.
Dropdown, date, tiền, mã định danh và checkbox phải có validation. Bảng lặp
dùng Excel Table thật, có hàng mẫu rõ ràng, không dùng hàng/ô ngầm để đoán dữ
liệu.

### 2.2 Hợp đồng import bắt buộc

Import không được merge tùy tiện vào hồ sơ đang mở. Sau khi file qua mọi kiểm
tra, tạo `candidate_state` v2 mới gồm:

`caseId`, `checkedForms`, `activeDocId`, `store.values`, `store.checks`,
`store.loops`, `autoSum` và metadata schema. Chỉ thay state đang mở bằng
candidate này khi toàn bộ validation pass; lỗi bất kỳ phải giữ nguyên draft
cũ và trả danh sách lỗi có ô/câu hỏi.

Fail-loud bắt buộc với: sai case/version/checksum, sheet/map bị xóa hoặc đổi,
question lạ, cell lạ, form không thuộc case, lựa chọn oneOf sai, công thức,
ID/text bị Excel chuyển số hoặc scientific notation, ngày/số sai, bảng vượt
giới hạn hoặc key không hợp lệ. Chuỗi khách nhập phải được lưu dạng text để
không mất số 0 đầu. Giá trị hiển thị bắt đầu `=`, `+`, `-`, `@` phải được
escape khi export và bị từ chối nếu xuất hiện như formula khi import.

### 2.3 Phạm vi rollout Excel

Hiện có: `PLII_M01`, `PLII_M02`, `PLII_M03`, `PLII_M04`, `PLI_M12`,
`PLI_M27`, `PLI_M72`. Trong 27 form được 28 case tham chiếu, sáu form đầu
thực sự được case dùng; còn 21 form chưa có questionnaire.

Rollout theo case (không theo thứ tự file) để mỗi đợt dùng được trọn vẹn:

1. **E1 — Core household:** các case chỉ dùng PLII_M01…M04; thay xuất một
   form bằng workbook case-level và kiểm thử bảng thành viên/ngành.
2. **E2 — Thay đổi doanh nghiệp:** case dùng PLI_M12, M13–M32; ưu tiên M12,
   M27 rồi những case một mẫu trước.
3. **E3 — Thành lập/chuyển đổi:** PLI_M01…M10 và PLI_M72; xử lý branch loại
   hình và mọi bảng người/vốn/cổ đông.
4. **E4 — Chi nhánh, tạm ngừng, công bố:** M21, M26–M32, M78 và các mẫu case
   còn lại.
5. **E5 — Review nội dung:** product/legal duyệt câu hỏi đời thường,
   ví dụ, dropdown và checklist giấy tờ của từng case trước khi bật nút gửi
   khách.

Không tạo questionnaire cho mẫu đã `REMOVED_BY_CURRENT_LAW`; case liên quan
phải bị chặn hoặc chuyển về mẫu thay thế hợp pháp.

## 3. Wave W0 — tái lập môi trường render

**Mục tiêu:** mọi máy QA có renderer cố định, không còn failure
`PDF_EXPORT_UNAVAILABLE`.

1. Cài LibreOffice ổn định, thêm `soffice` vào PATH và ghi version; không dùng
   Word COM chưa kích hoạt làm renderer tự động.
2. Kiểm `python-docx`, `openpyxl`, Node, browser runtime và Microsoft Word
   (nếu có) trong manifest môi trường.
3. Chạy lại `python -X utf8 -m tools.release_runner --json evidence/release.json`.
   Gate W0: **65/65 PASS**, không critical fail/not-run.
4. Chạy riêng và lưu stdout/artifact của bốn suite đã fail:
   `test_phase5r_metadata`, `test_phase5r_signatures`,
   `test_v7_header_name`, `test_export_concurrency`.
5. Không commit `generated_ho_so`, draft thật, screenshot có PII hay file
   evidence máy khách.

## 4. Wave W1 — visual Word/DOCX/PDF trên HEAD hiện tại

### W1.1 Delta bắt buộc

Render năm fixture (trống, tối thiểu, đầy đủ hợp lệ, dữ liệu dài, lựa chọn)
cho **23 template header vừa đổi**:

`PLII_M02–M06`, `PLI_M12–M15`, `PLI_M17–M19`, `PLI_M21`, `PLI_M23`,
`PLI_M25–M33` theo danh sách chính xác trong commit `a01f433`.

Kiểm mỗi trang PNG/PDF tại 100%: header trái/phải, quốc hiệu, ngày ký,
checkbox đúng một lựa chọn, ngày không dính/trùng, bảng không rơi ký tự,
không hàng trắng trước data, không orphan, không cắt chữ ký và không lộ marker.

**EML-001 (owner, 10/09/2026):** Với dòng có số điện thoại và thư điện tử,
nhãn `Thư điện tử (nếu có):` không được bị giữ ở dòng trên khi email dài rơi
xuống dòng dưới. Render engine phải dùng no-break space sau dấu `:` để nhãn
và giá trị email cùng chuyển xuống dòng kế tiếp; thêm regression fixture email
dài cho PLII_M02 và quét tất cả mẫu có nhãn này trong corpus W1.2.

**WEB-001 (owner, 10/09/2026):** Áp dụng cùng hợp đồng cho nhãn
`Website (nếu có):`: không để nhãn ở cuối dòng trước còn URL rơi xuống dòng
sau. URL chỉ được ngắt bên trong chính URL khi dài hơn bề rộng trang; bổ sung
fixture URL dài cho PLII_M02 và quét toàn corpus W1.2.

### W1.2 Corpus cuối

Sau delta pass, render lại corpus cuối từ **HEAD sạch**:

- 86 form active, PLI_M72 đủ 5 variant, 5 fixture = 450 record.
- Kiểm DOCX→PDF, ZIP integrity, deterministic `word/document.xml`, PNG
  manifest == files, Word open-direct và detector D1–D19.
- Visual gate tự động phải `HARD 0`, candidate được adjudicate rõ ràng.
- Reviewer người thật ký verdict từng trang; AI/contact-sheet chỉ để sàng lọc,
  không tự ghi PASS thay người.

Mọi lỗi nhận được phải vào `docs/defect_registry.md` với form, fixture, trang,
ảnh crop, root cause và regression test. Fix template luôn đi theo
source/spec → generator → blocks/form maps, regenerate hai lần zero-diff;
không sửa tay file generated.

## 5. Wave E0–E5 — Excel case-level

### E0 — schema và migration

1. Thêm `case_questionnaires/<caseId>.json` sinh từ use case + form map +
   questionnaire form-level hiện có; duy trì id/version/hash rõ ràng.
2. Viết migration read-only cho 7 questionnaire cũ; trong một release chuyển
   UI/bridge sang manifest case-level, sau đó bỏ API theo `doc_id` chỉ khi
   test backward compatibility pass.
3. Cập nhật bridge để export/import truyền `case_id`, không lấy `activeDocId`.

### E1 — exporter

1. Viết exporter workbook case-level, giữ style hiện hữu nhưng dùng named
   ranges/Excel Table/data validation và `veryHidden` map/lists.
2. Xử lý nhiều form dùng một data key: một ô canonical, các nơi còn lại là
   mirror read-only; không last-write-wins.
3. Thêm `Giấy_tờ_cần_gửi` chỉ từ registry đã duyệt và legal-version watermark.
4. Render/kiểm workbook trên Microsoft Excel và LibreOffice Calc; kiểm không
   vỡ cột ở 100% và 125% zoom, không mất tiếng Việt, dropdown/locked cells
   vẫn dùng được.

### E2 — importer và UI

1. Verify contract/hash trước khi đọc answers; parse typed values theo schema.
2. Rebuild candidate draft v2 nguyên tử; chạy validator/oneOf/activeWhen;
   chỉ cập nhật UI sau pass.
3. Trên UI, nêu case/file/version đã nạp và panel "còn thiếu" theo field,
   form và câu hỏi; có nút hủy trước khi thay draft.
4. Lưu audit metadata local (file hash, schema version, timestamp), không lưu
   dữ liệu khách vào log.

### E3 — test matrix

- Round-trip 28/28 case: scalar, mark/radio, select, date, money, percent,
  nested/fixed/output/editable table và 0/1/N rows.
- Regression multi-form: shared key, oneOf, optional form inactive, branch
  M72, case có nhiều mẫu; import xong export DOCX/ZIP đúng toàn bộ.
- Negative: old/tampered/wrong-case workbook, missing sheets, altered map,
  formula injection, long ID, Unicode, file lớn, unknown cell, duplicate row,
  broken validation, cancellation.
- Compatibility: Excel Desktop Windows, LibreOffice Calc và Excel-for-Mac;
  import lại file đã được mỗi ứng dụng lưu.
- Visual: reviewer kiểm hết các sheet của mỗi case template; ít nhất full
  case dài nhất ở mỗi cụm, sau đó snapshot/thumbnail regression cho mọi case.

### E4 — rollout an toàn

Feature flag `excel_case_v2`: chỉ bật cho case đã đạt legal + content + visual
gate. Phiên bản Excel v1 còn import được trong thời gian chuyển đổi, nhưng UI
không xuất mới v1. Case không đạt gate hiện thông báo rõ, không phát hành file
khuyết cho khách.

### E5 — acceptance

Gate Excel pass khi 28/28 case có workbook, import tạo draft hoàn chỉnh hoặc
liệt kê thiếu chính xác, tests xanh, visual Excel/Calc xanh và DOCX/ZIP
post-import được render pass.

## 6. Wave P0 — Windows `.exe`

Đã có spec và smoke kit ở `tools/windows_handoff/`; chưa có evidence chạy
thật. Thực hiện trên Windows 10/11 sạch:

1. Pin Python, pywebview, WebView2, LibreOffice, openpyxl và PyInstaller sau
   probe đầu tiên; ghi commit/version/pip freeze/SHA-256 vào build manifest.
2. Bảo đảm spec bundle UI, 87 template, data/form maps/VSIC/questionnaire,
   `tools.docx_render`, `tools.excel_export`, `tools.excel_import`; loại
   `profiles`, `generated_ho_so`, test/evidence và secret.
3. Build hai lần bằng `tools/windows_handoff/dangky_kinhdoanh.spec`; so archive
   inventory và hash (khác timestamp phải được giải thích). Không phát hành
   build onefile nếu rescue-copy export không pass.
4. Chạy S1–S8 trong `docs/platform_smoke_checklist.md`, cộng scenario Excel
   case-level, đường dẫn có dấu/space, user không admin và offline.
5. Mở DOCX/PDF bằng Word thật; mở và lưu lại Excel bằng Excel Desktop.
6. Ký Authenticode nếu có certificate. Nếu chưa có, phát hành nội bộ kèm hash
   và ghi rõ SmartScreen có thể cảnh báo; không lách AV/SmartScreen.

Gate P0: clean machine không Python mở `.exe`, mọi S1–S8 và export/import
pass, artifact manifest/hash/SBOM và evidence được lưu ngoài git.

## 7. Wave P1 — macOS `.app`

Không thể build `.app` hợp lệ từ Windows. Cần một runner macOS (Apple Silicon
và, nếu cần hỗ trợ, Intel riêng) hoặc GitHub Actions macOS.

1. Không dùng lại app cũ trong `99_muc_luc`: đó là sản phẩm/entry legacy khác
   và không phải bản `app_web` hiện tại.
2. Tạo `tools/macos_handoff/` gồm PyInstaller `.spec`, `build_app.sh`,
   entitlement tối thiểu, smoke script và README. Entry là `app_web/main.py`
   qua launcher tương tự Windows để đường dẫn bundled assets đúng.
3. Chọn build `--windowed --onedir` trước để debug/export bền vững; chỉ cân
   nhắc onefile sau khi vị trí `generated_ho_so` đã cố định trong thư mục người
   dùng (`~/Documents/DangKyKinhDoanh`), không nằm trong bundle/tạm.
4. Bundle WebKit/pywebview dependencies, UI, data, template và importer/exporter
   như Windows; kiểm private paths, quarantine và quyền Documents.
5. Smoke trên macOS: launch, 28 case, JSON save/open, Excel case v2, DOCX/PDF/
   ZIP, LibreOffice hoặc Word for Mac, offline và đường dẫn Unicode.
6. Ký `codesign --deep --options runtime` và notarize chỉ khi owner cung cấp
   Apple Developer Team ID/certificate/app-specific credentials. Không có
   credential: tạo `.app` unsigned cho nội bộ, không gọi là bản public-ready.
7. Test Gatekeeper trên máy sạch không có Python; ghi `spctl` verdict,
   SHA-256/dmg hash và manifest.

Gate P1: `.app` chạy độc lập, assets/export bền qua restart, smoke pass trên
target architecture; nếu public distribution thì codesign + notarization pass.

## 8. Thứ tự thực hiện và điều kiện merge

| Ưu tiên | Wave | Điều kiện bắt đầu | Điều kiện kết thúc |
|---|---|---|---|
| P0 | W0 | Có LibreOffice renderer | runner 65/65 PASS |
| P0 | W1 | W0 pass, HEAD sạch | corpus + human visual sign-off mới |
| P0 | E0–E2 | W0 pass | import/export case atomic chạy được |
| P1 | E3–E5 | E0–E2 pass | 28 case Excel + visual compatibility pass |
| P1 | P0 | Excel v2 frozen | Windows S1–S8 + `.exe` clean-machine pass |
| P1 | P1 | macOS runner available | `.app` smoke/signing verdict rõ |
| P2 | audit release | mọi gate trên có evidence | independent audit + release decision |

Mỗi lane phải có owner file rõ ràng, test mới được đăng ký vào
`tools/release_runner.py`, và không merge khi runner đỏ. Sau sửa giao diện,
template hoặc Excel layout phải render/duyệt lại artifact ảnh hưởng.

## 9. Definition of Done

Chỉ tuyên bố **`RELEASE_DONE`** khi:

- Word/DOCX/PDF corpus HEAD hiện tại, Excel 28 case và tất cả test đều pass;
- không còn visual evidence stale, `NOT_REVIEWED`, critical fail/not-run;
- Windows `.exe` và macOS `.app` có smoke evidence trên máy sạch;
- Excel import tái tạo đầy đủ case/draft và DOCX/ZIP post-import đã kiểm;
- legal/product đã duyệt các case được phát hành, không gửi workbook cho case
  chưa qua gate;
- audit độc lập xác nhận artifact, hash, privacy và không hạ test để lấy pass.
