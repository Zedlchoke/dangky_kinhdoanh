/* output-table.js - standalone renderer for contract-defined output grids.
 * UMD module: no DOM, no draft mutation, and no form-specific decisions. */
(function (root) {
  'use strict';

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function valueAt(object, key) {
    if (!object || typeof object !== 'object') return undefined;
    return object[key];
  }

  function contextValue(context, key) {
    var values = context && context.values;
    return valueAt(values, key);
  }

  function contextChecked(context, key) {
    var checks = context && context.checks;
    return valueAt(checks, key) === true;
  }

  function matchesValue(value, expected) {
    var actual = value == null ? '' : String(value).trim();
    var choices = Array.isArray(expected) ? expected : [expected];
    return choices.some(function (choice) {
      return actual === String(choice == null ? '' : choice).trim();
    });
  }

  /* Conditions are intentionally data-driven. Unsupported conditions fail
   * closed, so a malformed contract cannot accidentally render output. */
  function isActive(contract, context) {
    var conditions = contract && contract.active_when;
    if (conditions == null) conditions = [];
    if (!Array.isArray(conditions)) conditions = [conditions];
    var hasOwn = Object.prototype.hasOwnProperty;

    return conditions.every(function (condition) {
      if (!condition || typeof condition !== 'object') return false;
      if (condition.checkedKey != null &&
          !contextChecked(context, condition.checkedKey)) return false;
      if (hasOwn.call(condition, 'valueOf')) {
        var selector = condition.valueOf;
        if (!selector || selector.key == null ||
            !matchesValue(contextValue(context, selector.key), selector.equals)) {
          return false;
        }
      }
      return condition.checkedKey != null || hasOwn.call(condition, 'valueOf');
    });
  }

  function positiveInteger(value, fallback) {
    var n = Number(value);
    return Number.isInteger(n) && n > 0 ? n : fallback;
  }

  function cellLabel(labels, row, col, cols) {
    if (!Array.isArray(labels)) return '';
    var rowLabel = labels[row];
    if (Array.isArray(rowLabel)) return rowLabel[col] == null ? '' : rowLabel[col];
    // flat labels đếm ĐỦ cols -> trải theo CỘT (bảng 1 hàng × N cột, khối ký
    // ngang 5R2 PLI_M70) — đồng bộ điều kiện horizontal của _find_output_grid_block
    if (labels.length === cols) return labels[col] == null ? '' : labels[col];
    return col === 0 ? rowLabel : '';
  }

  function renderOutputTable(contract, context) {
    contract = contract || {};
    if (contract.kind !== 'output-table' || !isActive(contract, context || {})) {
      return '';
    }

    var grid = contract.grid || {};
    var rows = positiveInteger(grid.rows, 0);
    var cols = positiveInteger(grid.cols, 0);
    if (!rows || !cols) return '';

    var sectionId = contract.section_id == null ? '' : contract.section_id;
    var semanticKey = contract.semantic_key == null ? '' : contract.semantic_key;
    var html = '<table class="btable output-table" role="grid"' +
      ' data-component="output-table"' +
      ' data-output-only="true"' +
      ' data-section-id="' + escapeHtml(sectionId) + '"' +
      ' data-semantic-key="' + escapeHtml(semanticKey) + '"' +
      ' aria-rowcount="' + rows + '"' +
      ' aria-colcount="' + cols + '">';

    html += '<tbody>';
    for (var row = 0; row < rows; row++) {
      html += '<tr role="row" data-output-row="' + row + '">';
      for (var col = 0; col < cols; col++) {
        html += '<td role="gridcell" data-output-row="' + row +
          '" data-output-col="' + col + '">' +
          escapeHtml(cellLabel(grid.labels, row, col, cols))
            .split('\n').join('<br>') +
          '</td>';
      }
      html += '</tr>';
    }
    return html + '</tbody></table>';
  }

  var api = {
    escapeHtml: escapeHtml,
    isActive: isActive,
    renderOutputTable: renderOutputTable
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  } else {
    root.OutputTable = api;
  }
})(typeof module !== 'undefined' && module.exports ? module.exports : window);
