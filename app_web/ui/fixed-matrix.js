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

function sumFormula(formula, spec, draft) {
  var match = String(formula || '').trim().match(/^sum\(\s*([^)]+?)\s*\)$/i);
  if (!match) return { supported: false, value: null };
  var tag = match[1];
  var totalRows = (Array.isArray(spec.totals) ? spec.totals : []).map(
    function (total) { return String(total.id); });
  var total = 0;
  rowsOf(spec).forEach(function (row) {
    if (isOutputRow(row) || totalRows.indexOf(String(row.id)) >= 0) return;
    var value = numberValue(cellValue(spec, draft, row.id, tag));
    if (value !== null) total += value;
  });
  return { supported: true, value: total, tag: tag };
}

function formulaValue(formula, spec, draft) {
  return sumFormula(formula, spec, draft);
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

  (Array.isArray(spec.totals) ? spec.totals : []).forEach(function (total) {
    var evaluated = formulaValue(total.formula, spec, draft);
    var targetRow = result.rows.filter(function (row) {
      return String(row.id) === String(total.id);
    })[0];
    if (!targetRow) return;
    targetRow.cells[total.target_tag || total.targetTag || 'value'] =
      evaluated.value;
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
