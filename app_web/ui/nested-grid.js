'use strict';

/*
 * Pure nested-grid platform.
 *
 * The contract owns header structure, physical column order, row groups, and
 * discriminator meaning. This module deliberately does not infer legal row
 * semantics from labels or form IDs.
 */

var hasOwn = Object.prototype.hasOwnProperty;

function clone(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function invalid(message, path) {
  return { code: 'NESTED_CONTRACT_INVALID', path: path || '', message: message };
}

function positiveInteger(value) {
  return Number.isInteger(value) && value > 0;
}

function columnsOf(spec) {
  return Array.isArray(spec && spec.columns) ? spec.columns : [];
}

function requiredColumnsOf(group) {
  if (!group || typeof group !== 'object') return [];
  if (Array.isArray(group.required_columns)) return group.required_columns;
  if (Array.isArray(group.required_fields)) return group.required_fields;
  if (Array.isArray(group.required)) return group.required;
  return [];
}

function headerRowsOf(spec) {
  return Array.isArray(spec && spec.header_rows) ? spec.header_rows : [];
}

function validateContract(spec) {
  var errors = [];
  if (!spec || typeof spec !== 'object' || Array.isArray(spec)) {
    return [invalid('Contract must be an object')];
  }
  if (spec.kind !== 'nested-grid') {
    errors.push(invalid('kind must be nested-grid', 'kind'));
  }
  if (typeof spec.semantic_key !== 'string' || !spec.semantic_key.trim()) {
    errors.push(invalid('semantic_key is required', 'semantic_key'));
  }
  if (!headerRowsOf(spec).length) {
    errors.push(invalid('header_rows must contain at least one row', 'header_rows'));
  }
  if (!columnsOf(spec).length) {
    errors.push(invalid('columns must contain at least one column', 'columns'));
  }

  var seen = {};
  columnsOf(spec).forEach(function (column, index) {
    var path = 'columns[' + index + ']';
    if (!column || typeof column !== 'object' ||
        typeof column.tag !== 'string' || !column.tag.trim() ||
        !Number.isInteger(column.col_index) || column.col_index < 0) {
      errors.push(invalid('column requires tag and non-negative col_index', path));
      return;
    }
    if (hasOwn.call(seen, column.col_index)) {
      errors.push(invalid('col_index must be unique', path + '.col_index'));
    }
    seen[column.col_index] = true;
  });

  headerRowsOf(spec).forEach(function (row, rowIndex) {
    if (!Array.isArray(row) || !row.length) {
      errors.push(invalid('header row must be a non-empty array',
        'header_rows[' + rowIndex + ']'));
      return;
    }
    row.forEach(function (cell, cellIndex) {
      if (!cell || typeof cell !== 'object' ||
          !positiveInteger(cell.rowspan == null ? 1 : cell.rowspan) ||
          !positiveInteger(cell.colspan == null ? 1 : cell.colspan)) {
        errors.push(invalid('header cell spans must be positive integers',
          'header_rows[' + rowIndex + '][' + cellIndex + ']'));
      }
    });
  });

  if (spec.discriminator != null) {
    var discriminator = spec.discriminator;
    if (!discriminator || typeof discriminator.tag !== 'string' ||
        !Array.isArray(discriminator.values) || !discriminator.values.length ||
        discriminator.values.some(function (value) {
          return value == null || String(value).trim() === '';
        })) {
      errors.push(invalid('discriminator requires tag and non-empty values',
        'discriminator'));
    }
  }
  if (spec.row_groups != null && !Array.isArray(spec.row_groups)) {
    errors.push(invalid('row_groups must be an array', 'row_groups'));
  }
  (Array.isArray(spec.row_groups) ? spec.row_groups : []).forEach(function (group, index) {
    if (!group || typeof group.group_id !== 'string' || !group.group_id.trim()) {
      errors.push(invalid('row group requires group_id', 'row_groups[' + index + ']'));
    }
    if (group && (group.required_columns != null ||
        group.required_fields != null || group.required != null) &&
        (!Array.isArray(requiredColumnsOf(group)) ||
         requiredColumnsOf(group).some(function (tag) {
           return typeof tag !== 'string' || !tag.trim();
         }))) {
      errors.push(invalid('group required fields must be string tags',
        'row_groups[' + index + ']'));
    }
    if (group && group.match != null && typeof group.match !== 'function' &&
        !isMatchRule(group.match)) {
      errors.push(invalid('unsupported row-group match', 'row_groups[' + index + '].match'));
    }
  });
  return errors;
}

function safeMatch(rule, row) {
  if (typeof rule === 'function') return !!rule(row);
  if (!rule || typeof rule !== 'string') {
    if (!rule || typeof rule !== 'object' || typeof rule.tag !== 'string') return false;
    if (hasOwn.call(rule, 'equals')) return String(row[rule.tag]) === String(rule.equals);
    if (rule.notEmpty === true) return row[rule.tag] != null &&
      String(row[rule.tag]).trim() !== '';
    if (rule.exists === true) return hasOwn.call(row, rule.tag);
    return false;
  }
  var match = rule.trim().match(/^([A-Za-z_][\w.-]*)\s*(==|!=)\s*null$/);
  if (!match) return false;
  var present = row[match[1]] != null;
  return match[2] === '!=' ? present : !present;
}

function isMatchRule(rule) {
  if (typeof rule === 'function') return true;
  if (typeof rule === 'string') {
    return /^([A-Za-z_][\w.-]*)\s*(==|!=)\s*null$/.test(rule.trim());
  }
  return !!(rule && typeof rule === 'object' &&
    typeof rule.tag === 'string' &&
    (hasOwn.call(rule, 'equals') || rule.notEmpty === true || rule.exists === true));
}

function physicalColumns(spec) {
  var contractErrors = validateContract(spec);
  if (contractErrors.length) return { columns: [], errors: contractErrors };
  var columns = columnsOf(spec).map(function (column) {
    return clone(column);
  }).sort(function (a, b) { return a.col_index - b.col_index; });
  var errors = [];
  var base = columns.length && columns[0].col_index === 1 ? 1 : 0;
  columns.forEach(function (column, index) {
    if (column.col_index !== base + index) {
      errors.push(invalid('physical columns must be contiguous from zero or one',
        'columns[' + column.tag + '].col_index'));
    }
  });
  return { columns: columns, errors: errors };
}

function headerLayout(spec) {
  var physical = physicalColumns(spec);
  if (physical.errors.length) return { rows: [], columns: [], errors: physical.errors };
  var occupied = [];
  var rows = [];
  var width = physical.columns.length;
  headerRowsOf(spec).forEach(function (sourceRow, rowIndex) {
    var output = [];
    var cursor = 0;
    occupied[rowIndex] = occupied[rowIndex] || [];
    sourceRow.forEach(function (sourceCell) {
      while (occupied[rowIndex][cursor]) cursor++;
      var rowspan = sourceCell.rowspan == null ? 1 : sourceCell.rowspan;
      var colspan = sourceCell.colspan == null ? 1 : sourceCell.colspan;
      if (cursor + colspan > width) {
        return;
      }
      for (var r = rowIndex; r < rowIndex + rowspan; r++) {
        occupied[r] = occupied[r] || [];
        for (var c = cursor; c < cursor + colspan; c++) {
          if (occupied[r][c]) return;
          occupied[r][c] = true;
        }
      }
      output.push({
        text: sourceCell.text == null ? '' : String(sourceCell.text),
        rowspan: rowspan,
        colspan: colspan,
        col_index: cursor
      });
      cursor += colspan;
    });
    rows.push(output);
  });
  var malformed = false;
  for (var row = 0; row < headerRowsOf(spec).length; row++) {
    for (var col = 0; col < width; col++) {
      if (!occupied[row] || !occupied[row][col]) malformed = true;
    }
  }
  if (malformed) {
    return { rows: [], columns: [], errors: [
      invalid('header spans do not cover the physical column grid', 'header_rows')
    ] };
  }
  return { rows: rows, columns: physical.columns, errors: [] };
}

function rowId(row, index) {
  return row && row._row_id != null ? String(row._row_id) : 'r' + (index + 1);
}

function normalizeRows(spec, rows) {
  var errors = validateContract(spec);
  if (errors.length || !Array.isArray(rows)) return { rows: [], errors: errors.concat(
    Array.isArray(rows) ? [] : [invalid('rows must be an array', 'rows')]) };
  var seen = {};
  var result = rows.map(function (row, index) {
    var copy = clone(row);
    if (!copy || typeof copy !== 'object' || Array.isArray(copy)) {
      errors.push(invalid('row must be an object', 'rows[' + index + ']'));
      return copy;
    }
    copy._row_id = rowId(copy, index);
    if (hasOwn.call(seen, copy._row_id)) {
      errors.push(invalid('row IDs must be unique', 'rows[' + index + ']._row_id'));
    }
    seen[copy._row_id] = true;
    return copy;
  });
  return { rows: errors.length ? [] : result, errors: errors };
}

function error(spec, row, tag, code, message) {
  var key = spec.semantic_key + '.' + row._row_id + (tag ? '.' + tag : '');
  return { key: key, docId: spec.form_id || null, code: code,
    message: message, severity: 'blocking' };
}

/* O3 (owner decision packet v7, 2026-09-06): min_rows chỉ đếm DÒNG BUSINESS
 * DATA. Cột cấu trúc (outputOnly - chỉ dùng để in; stt - số thứ tự tự sinh)
 * không được tính là dữ liệu nghiệp vụ: một dòng chỉ có ô STT/chữ ký in là
 * dòng trống về mặt dữ liệu. */
function isStructuralColumn(column) {
  return !column || typeof column.tag !== 'string' || !column.tag ||
    column.type === 'outputOnly' || column.type === 'stt';
}

function businessColumnsOf(spec) {
  return columnsOf(spec)
    .filter(function (column) { return !isStructuralColumn(column); })
    .map(function (column) { return column.tag; });
}

function cellHasValue(row, key) {
  return row[key] != null && String(row[key]).trim() !== '';
}

/* Dòng BUSINESS DATA của một spec: ít nhất một ô dữ liệu có giá trị.
 * Loại trừ: key nội bộ (_row_id...), cột cấu trúc (outputOnly/stt), và tag
 * discriminator (vai trò dòng chưa phải dữ liệu - khớp contract export giữ
 * dòng chỉ có discriminator để không mất cấu trúc). Key ngoài khai báo vẫn
 * tính là dữ liệu (khớp blank-row contract của đường export). */
function businessRowsOf(spec, rows) {
  var structural = {};
  columnsOf(spec).forEach(function (column) {
    if (isStructuralColumn(column)) structural[column.tag] = true;
  });
  var businessTags = businessColumnsOf(spec);
  var discriminatorTag = spec && spec.discriminator &&
    typeof spec.discriminator.tag === 'string' ? spec.discriminator.tag : null;
  return (Array.isArray(rows) ? rows : []).filter(function (row) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) return false;
    if (businessTags.some(function (tag) { return cellHasValue(row, tag); })) {
      return true;
    }
    return Object.keys(row).some(function (key) {
      return key.charAt(0) !== '_' &&
        !hasOwn.call(structural, key) &&
        !(discriminatorTag != null && key === discriminatorTag) &&
        cellHasValue(row, key);
    });
  });
}

function validate(spec, rows, ctx) {
  var contractErrors = validateContract(spec);
  if (contractErrors.length) return contractErrors.map(function (item) {
    return { key: spec && spec.semantic_key || null, docId: spec && spec.form_id || null,
      code: item.code, message: item.message, severity: 'blocking' };
  });
  var normalized = normalizeRows(spec, rows);
  if (normalized.errors.length) return normalized.errors.map(function (item) {
    return { key: spec.semantic_key, docId: spec.form_id || null,
      code: item.code, message: item.message, severity: 'blocking' };
  });
  var discriminator = spec.discriminator;
  var groups = Array.isArray(spec.row_groups) ? spec.row_groups : [];
  var required = columnsOf(spec).filter(function (column) {
    return column.required === true;
  }).map(function (column) { return column.tag; });
  var errors = [];
  normalized.rows.forEach(function (row) {
    var filled = Object.keys(row).some(function (key) {
      return key !== '_row_id' && row[key] != null && String(row[key]).trim() !== '';
    });
    if (!filled) return;
    var group = null;
    if (discriminator) {
      var value = row[discriminator.tag];
      if (discriminator.values.indexOf(value) < 0) {
        errors.push(error(spec, row, discriminator.tag, 'DISCRIMINATOR_INVALID',
          'Row discriminator is not declared by the contract'));
        return;
      }
    }
    groups.some(function (candidate) {
      if (candidate.match == null || safeMatch(candidate.match, row)) {
        group = candidate;
        return true;
      }
      return false;
    });
    var tags = required.slice();
    if (group) {
      tags = tags.concat(requiredColumnsOf(group));
    }
    tags.filter(function (tag, index) { return tags.indexOf(tag) === index; })
      .forEach(function (tag) {
        if (row[tag] == null || String(row[tag]).trim() === '') {
          errors.push(error(spec, row, tag, 'REQUIRED_FIELD',
            'Required field is missing for this row group'));
        }
      });
  });
  /* O3 (owner decision packet v7, 2026-09-06): min_rows/max_rows chỉ enforce
   * KHI section ACTIVE. ctx.isActive === false nghĩa là caller đã đánh giá
   * activeWhen của section CHƯA thỏa -> section inactive: 0 dòng là hợp lệ,
   * không sinh MIN_ROWS/MAX_ROWS. Không có ctx (caller cũ/test trực tiếp) ->
   * mặc định ACTIVE, giữ hành vi decided của D2.7=A. Dòng business-data được
   * đếm bởi businessRowsOf; blank UI row không tính. */
  var active = !(ctx && ctx.isActive === false);
  if (active) {
    var minRows = spec.min_rows == null ? 0 : Number(spec.min_rows);
    if (positiveInteger(minRows) &&
        businessRowsOf(spec, normalized.rows).length < minRows) {
      errors.push({
        key: spec.semantic_key, docId: spec.form_id || null, code: 'MIN_ROWS',
        message: 'Active section "' + (spec.section_id || spec.semantic_key) +
          '" requires at least ' + minRows + ' row(s) of business data; ' +
          'blank rows do not count (O3)',
        severity: 'blocking'
      });
    }
    var maxRows = spec.max_rows == null ? null : Number(spec.max_rows);
    if (maxRows != null && Number.isFinite(maxRows) && maxRows > 0 &&
        normalized.rows.length > maxRows) {
      errors.push({
        key: spec.semantic_key, docId: spec.form_id || null, code: 'MAX_ROWS',
        message: 'Section "' + (spec.section_id || spec.semantic_key) +
          '" exceeds the maximum of ' + maxRows + ' row(s)',
        severity: 'warning'
      });
    }
  }
  return errors;
}

module.exports = {
  businessColumnsOf: businessColumnsOf,
  businessRowsOf: businessRowsOf,
  headerLayout: headerLayout,
  normalizeRows: normalizeRows,
  physicalColumns: physicalColumns,
  validate: validate,
  validateContract: validateContract
};
