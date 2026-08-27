'use strict';

/*
 * Pure fixed-matrix platform.
 *
 * A matrix spec owns its legal rows. Draft values remain flat under
 * values["<semantic_key>.<row_id>.<tag>"]. Computed/output-only cells are
 * projections and are never written back to the draft.
 */

function clone(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function rowsOf(spec) {
  if (!spec || !Array.isArray(spec.fixed_rows)) return [];
  return spec.fixed_rows;
}

function columnsOf(spec) {
  return Array.isArray(spec && spec.columns) ? spec.columns : [];
}

function isOutputColumn(column) {
  return !!column && (column.outputOnly === true ||
    column.output_only === true || column.inputType === 'outputOnly' ||
    column.type === 'outputOnly' || column.computed === true);
}

function isOutputRow(row) {
  return !!row && (row.outputOnly === true || row.output_only === true);
}

function valueKey(spec, rowId, tag) {
  return String(spec.semantic_key || spec.semanticKey) + '.' +
    String(rowId) + '.' + String(tag);
}

function valuesOf(draft) {
  if (!draft) return {};
  return draft.values || (draft.store && draft.store.values) || {};
}

function cellValue(spec, draft, rowId, tag) {
  var values = valuesOf(draft);
  var key = valueKey(spec, rowId, tag);
  if (Object.prototype.hasOwnProperty.call(values, key)) return values[key];

  var row = rowsOf(spec).filter(function (item) {
    return String(item.id) === String(rowId);
  })[0];
  var cells = row && row.cells;
  return cells && Object.prototype.hasOwnProperty.call(cells, tag) ?
    cells[tag] : '';
}

function numberValue(value) {
  if (value === null || value === undefined || String(value).trim() === '') {
    return null;
  }
  var text = String(value).trim().replace(/\s/g, '');
  // Draft money values conventionally use dots for thousands. A decimal
  // comma is retained only when there is no dot.
  if (text.indexOf('.') >= 0 && text.indexOf(',') >= 0) {
    text = text.replace(/\./g, '').replace(',', '.');
  } else if (text.indexOf(',') >= 0) {
    text = text.replace(',', '.');
  } else if (/^-?\d{1,3}(\.\d{3})+$/.test(text)) {
    text = text.replace(/\./g, '');
  }
  var result = Number(text);
  return Number.isFinite(result) ? result : null;
}

/*
 * Lane W2 — D1.4=A: "giá trị loại cổ phần = số lượng × mệnh giá" là projection
 * (ô outputOnly), nên engine phải TỰ TÍNH LẠI chứ không tin draft. Vì vậy ngoài
 * `sum(<tag>)`, module nhận thêm `product(<col_tag>[, <col_tag>...])` theo đúng
 * grammar đã nới ở tools/form_specs/schema/table_kinds.schema.json
 * (mục fixed_matrix.totals).
 *
 * Ngữ nghĩa product() chốt và áp ĐỒNG NHẤT với phía Python
 * (tools/docx_render.py::_TOTALS_FORMULA_RE):
 *   1. op viết thường đúng chữ (`sum`|`product`); mỗi thừa số là một tag cột;
 *   2. mỗi dòng input nhân các ô theo đúng thứ tự tag khai báo, rồi CỘNG DỒN
 *      tích từng dòng vào ô tổng; dòng tổng/dòng outputOnly bị loại khỏi vùng
 *      quét (cùng quy tắc sum() đang dùng);
 *   3. dòng KHÔNG kê khai gì (rỗng ở mọi thừa số) bị bỏ qua — như sum bỏ qua ô
 *      rỗng: một loại cổ phần không dùng không được tính thành 0 đồng;
 *   4. dòng ĐÃ kê khai mà THIẾU >= 1 thừa số -> không suy ra được con số pháp
 *      lý, nên ô tổng là KHÔNG XÁC ĐỊNH và in TRỐNG (chuỗi ''), tuyệt đối
 *      KHÔNG thay bằng 0 — trống nghĩa là "chưa đủ dữ liệu nguồn";
 *   5. không có dòng nào đủ thừa số (draft trắng tinh) -> cũng in trống;
 *   6. mọi số đi qua numberValue() hiện có (nghìn '.', thập phân ',', bỏ dấu
 *      cách); kết quả trả dạng số thô — định dạng hiển thị vẫn thuộc về
 *      componentNumberText/displayMoney của render.js, không hard-code format;
 *   7. formula/tag lạ -> {supported:false} -> validate() vẫn push blocking
 *      FORMULA_UNSUPPORTED như cũ (không thêm mã lỗi mới).
 */

function totalsOf(spec) {
  return Array.isArray(spec && spec.totals) ? spec.totals : [];
}

/* Dòng bị loại khỏi vùng quét công thức: dòng outputOnly + mọi dòng đích
 * khai báo trong spec.totals. */
function excludedRowIds(spec) {
  var ids = totalsOf(spec).map(function (total) {
    return String(total.id);
  });
  rowsOf(spec).forEach(function (row) {
    if (isOutputRow(row)) ids.push(String(row.id));
  });
  return ids;
}

function declaredTags(spec) {
  return columnsOf(spec).map(function (column) {
    return column && column.tag !== undefined && column.tag !== null ?
      String(column.tag) : '';
  }).filter(function (tag) { return tag !== ''; });
}

function sumFormula(formula, spec, draft) {
  var match = String(formula || '').trim().match(/^sum\(\s*([^)]+?)\s*\)$/i);
  if (!match) return { supported: false, value: null };
  var tag = match[1];
  var totalRows = totalsOf(spec).map(
    function (total) { return String(total.id); });
  var total = 0;
  rowsOf(spec).forEach(function (row) {
    if (isOutputRow(row) || totalRows.indexOf(String(row.id)) >= 0) return;
    var value = numberValue(cellValue(spec, draft, row.id, tag));
    if (value !== null) total += value;
  });
  return { supported: true, value: total, tag: tag };
}

function productFormula(formula, spec, draft) {
  // Không dùng /i cho product: chấp nhận 'PRODUCT(...)' sẽ làm JS tính còn
  // Python bác bỏ, mất parity hai phía.
  var match = String(formula || '').trim().match(/^product\(\s*(.+?)\s*\)$/);
  if (!match) return { supported: false, value: null };
  var tags = match[1].split(',').map(function (item) {
    return item.trim();
  }).filter(function (item) { return item !== ''; });
  var known = declaredTags(spec);
  // Thừa số phải là tag cột khai báo thật; sai tag coi như formula hỏng.
  if (!tags.length ||
      !tags.every(function (tag) { return known.indexOf(tag) >= 0; })) {
    return { supported: false, value: null, tags: tags };
  }

  var excluded = excludedRowIds(spec);
  var indeterminate = false;   // có dòng khai mà thiếu thừa số
  var usableRows = 0;          // số dòng đủ thừa số đã góp vào tổng
  var total = 0;
  rowsOf(spec).some(function (row) {
    if (indeterminate || isOutputRow(row) ||
        excluded.indexOf(String(row.id)) >= 0) return false;
    var rowProduct = 1;
    var blanks = 0;
    tags.forEach(function (tag) {
      var factor = numberValue(cellValue(spec, draft, row.id, tag));
      if (factor === null) {
        blanks += 1;
        return;
      }
      rowProduct *= factor;
    });
    if (blanks === tags.length) return false;   // dòng không kê khai gì
    if (blanks) {                    // khai thiếu -> ô tổng KHÔNG XÁC ĐỊNH
      indeterminate = true;
      return true;                   // dừng quét: in trống, không đoán số
    }
    usableRows += 1;
    total += rowProduct;
    return false;
  });
  // Trống -> chuỗi rỗng để ô tổng in khoảng trắng, không in '0'.
  return {
    supported: true,
    value: !indeterminate && usableRows ? total : '',
    tags: tags
  };
}

function formulaValue(formula, spec, draft) {
  var text = String(formula || '').trim();
  var name = /^([A-Za-z]+)\s*\(/.exec(text);
  if (name && name[1].toLowerCase() === 'product') {
    // 'PRODUCT(...)' vẫn rơi vào đây rồi bị productFormula từ chối (fail-loud).
    return productFormula(text, spec, draft);
  }
  return sumFormula(text, spec, draft);
}

function recompute(spec, draft) {
  var result = {
    semantic_key: spec.semantic_key || spec.semanticKey,
    rows: rowsOf(spec).map(function (row) {
      var cells = {};
      columnsOf(spec).forEach(function (column) {
        if (!isOutputColumn(column)) {
          cells[column.tag] = clone(cellValue(spec, draft, row.id, column.tag));
        }
      });
      return { id: row.id, label: row.label, cells: cells };
    })
  };

  totalsOf(spec).forEach(function (total) {
    var evaluated = formulaValue(total.formula, spec, draft);
    var targetRow = result.rows.filter(function (row) {
      return String(row.id) === String(total.id);
    })[0];
    if (!targetRow) return;
    // W2/D1.4=A: product() thiếu thừa số trả '' (trống) — ô tổng phải in
    // khoảng trắng, không bao giờ tự đoán thành '0' hay chuỗi 'null'.
    targetRow.cells[total.target_tag || total.targetTag || 'value'] =
      evaluated.value === null || evaluated.value === undefined ?
        '' : evaluated.value;
  });

  return result;
}

function error(spec, rowId, tag, code, message, severity) {
  var key = String(spec.semantic_key || spec.semanticKey);
  if (rowId !== undefined) key += '.' + rowId;
  if (tag !== undefined) key += '.' + tag;
  return {
    key: key,
    docId: spec.form_id || spec.formId || spec.docId || null,
    code: code,
    message: message,
    severity: severity || 'blocking'
  };
}

function hookErrors(hook, value, context) {
  if (typeof hook !== 'function') return [];
  var result = hook(value, context);
  if (result === true || result === undefined || result === null) return [];
  if (result === false) return [{ code: context.code, message: context.message }];
  return Array.isArray(result) ? result : [result];
}

function validate(spec, draft, hooks) {
  hooks = hooks || {};
  var errors = [];
  columnsOf(spec).forEach(function (column) {
    if (isOutputColumn(column)) return;
    rowsOf(spec).forEach(function (row) {
      var value = cellValue(spec, draft, row.id, column.tag);
      var type = column.inputType || column.type;
      var numeric = type === 'money' || type === 'percent';
      if (numeric && value !== '' && value !== null && value !== undefined) {
        var parsed = numberValue(value);
        var code = type === 'money' ? 'MONEY' : 'PERCENT';
        if (parsed === null || parsed < 0 ||
            (type === 'percent' && parsed > 100)) {
          errors.push(error(spec, row.id, column.tag, code,
            'Invalid ' + type + ' value'));
        }
        var hook = type === 'money' ?
          (hooks.money || hooks.moneyValidator) :
          (hooks.percent || hooks.percentValidator);
        hookErrors(hook, value, {
          spec: spec, row: row, column: column, code: code,
          message: 'Invalid ' + type + ' value'
        }).forEach(function (item) {
          errors.push(error(spec, row.id, column.tag, item.code || code,
            item.message || 'Invalid ' + type + ' value',
            item.severity || 'blocking'));
        });
      }
    });
  });

  (Array.isArray(spec.totals) ? spec.totals : []).forEach(function (total) {
    var evaluated = formulaValue(total.formula, spec, draft);
    if (!evaluated.supported) {
      errors.push(error(spec, total.id, undefined, 'FORMULA_UNSUPPORTED',
        'Unsupported fixed-matrix formula', 'blocking'));
    }
  });
  return errors;
}

function exportMatrix(spec, draft, hooks) {
  var matrix = recompute(spec, draft);
  return {
    semantic_key: matrix.semantic_key,
    rows: matrix.rows,
    errors: validate(spec, draft, hooks)
  };
}

module.exports = {
  cellValue: cellValue,
  exportMatrix: exportMatrix,
  fixedRows: function (spec) { return clone(rowsOf(spec)); },
  formulaValue: formulaValue,
  productFormula: productFormula,
  sumFormula: sumFormula,
  isOutputColumn: isOutputColumn,
  recompute: recompute,
  setCell: function (draft, spec, rowId, tag, value) {
    var target = draft.values || (draft.values = {});
    target[valueKey(spec, rowId, tag)] = value;
    return draft;
  },
  validate: validate,
  canDelete: function () { return false; },
  deleteRow: function () { return false; },
  deleteRows: function () { return 0; }
};
