import React from 'react';

export default function DataTable({ columns, rows, onRowClick, emptyMessage }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="table-container">
        <div className="table-empty">{emptyMessage || 'No data available.'}</div>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id ?? i}
              onClick={() => onRowClick && onRowClick(row)}
              className={onRowClick ? 'data-table-row--clickable' : ''}
            >
              {columns.map((col) => (
                <td key={col.key}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
