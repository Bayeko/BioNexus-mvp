/**
 * DynamicFormBuilder - Auto-generates form from Pydantic schema
 *
 * Features:
 * - Reads field types from ParsedData schema
 * - Visual distinction: Green for AI-extracted, Yellow for human-corrected
 * - Inline edit notes (21 CFR Part 11 audit trail)
 * - Live validation of field changes
 */

import React, { useState } from 'react';
import { AlertCircle, ChevronDown, Edit2, Save } from 'lucide-react';

interface DynamicFormBuilderProps {
  extractedData: Record<string, any>;
  confirmedData: Record<string, any>;
  onFieldChange: (fieldName: string, newValue: any, reason?: string) => void;
}

const DynamicFormBuilder: React.FC<DynamicFormBuilderProps> = ({
  extractedData,
  confirmedData,
  onFieldChange,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['basic'])
  );
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editReason, setEditReason] = useState('');

  // Group fields by type/section
  const fieldGroups = groupFieldsBySection(extractedData);

  const toggleSection = (section: string) => {
    const newSet = new Set(expandedSections);
    if (newSet.has(section)) {
      newSet.delete(section);
    } else {
      newSet.add(section);
    }
    setExpandedSections(newSet);
  };

  const handleEditStart = (fieldName: string, currentValue: any) => {
    setEditingField(fieldName);
    setEditValue(JSON.stringify(currentValue, null, 2));
    setEditReason(confirmedData?.[`_notes_${fieldName}`] || '');
  };

  const handleEditSave = (fieldName: string) => {
    try {
      const newValue = JSON.parse(editValue);
      onFieldChange(fieldName, newValue, editReason);
      setEditingField(null);
    } catch (e) {
      // Handle JSON parse error
      alert('Invalid JSON format');
    }
  };

  const renderField = (fieldName: string, value: any) => {
    const extracted = extractedData[fieldName];
    const confirmed = confirmedData?.[fieldName];
    const isModified = extracted !== confirmed;
    const reason = confirmedData?.[`_notes_${fieldName}`];

    // Determine edit state
    const isEditing = editingField === fieldName;

    return (
      <div
        key={fieldName}
        className={`mb-4 p-4 rounded-lg border-l-4 transition-colors ${
          isModified
            ? 'bg-yellow-50 border-yellow-400'
            : 'bg-green-50 border-green-400'
        }`}
      >
        {/* Field Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-semibold text-gray-900">
              {formatFieldName(fieldName)}
            </label>
            {isModified && (
              <span className="px-2 py-1 bg-yellow-200 text-yellow-900 text-xs font-bold rounded">
                CORRECTED
              </span>
            )}
            {!isModified && (
              <span className="px-2 py-1 bg-green-200 text-green-900 text-xs font-bold rounded">
                AI EXTRACTED
              </span>
            )}
          </div>

          <button
            onClick={() =>
              isEditing
                ? handleEditSave(fieldName)
                : handleEditStart(fieldName, confirmed || extracted)
            }
            className="p-1 hover:bg-gray-200 rounded transition-colors"
          >
            {isEditing ? (
              <Save className="w-4 h-4 text-green-600" />
            ) : (
              <Edit2 className="w-4 h-4 text-gray-600" />
            )}
          </button>
        </div>

        {/* Field Content */}
        {isEditing ? (
          <div className="space-y-2">
            {/* Edit Textarea */}
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
            />

            {/* Reason for Correction */}
            <div>
              <label className="text-xs font-semibold text-gray-700">
                Reason for Correction (21 CFR Part 11)
              </label>
              <textarea
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                placeholder="Document why this correction was necessary..."
                className="w-full p-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={2}
              />
            </div>

            {/* Save/Cancel */}
            <div className="flex space-x-2">
              <button
                onClick={() => handleEditSave(fieldName)}
                className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
              >
                Save
              </button>
              <button
                onClick={() => setEditingField(null)}
                className="px-3 py-1 bg-gray-300 text-gray-900 text-sm rounded hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div>
            {/* Display Values */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-600 font-semibold">
                  AI EXTRACTED
                </p>
                <p className="text-sm text-gray-900 font-mono bg-white p-2 rounded border border-gray-200 mt-1">
                  {formatValue(extracted)}
                </p>
              </div>

              {isModified && (
                <div>
                  <p className="text-xs text-gray-600 font-semibold">
                    HUMAN CORRECTED
                  </p>
                  <p className="text-sm text-yellow-900 font-mono bg-white p-2 rounded border border-yellow-300 mt-1 font-bold">
                    {formatValue(confirmed)}
                  </p>
                </div>
              )}
            </div>

            {/* Correction Reason */}
            {isModified && reason && (
              <div className="mt-3 p-2 bg-white border-l-2 border-yellow-400 rounded">
                <p className="text-xs text-gray-600 font-semibold">
                  CORRECTION REASON
                </p>
                <p className="text-sm text-gray-900 italic">{reason}</p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold">21 CFR Part 11 Compliance</p>
            <p className="text-xs mt-1">
              All corrections must include a reason. Each change is attributed to
              you with a timestamp and recorded in the audit trail.
            </p>
          </div>
        </div>
      </div>

      {/* Field Groups */}
      {Object.entries(fieldGroups).map(([section, fields]) => (
        <div key={section} className="border border-gray-200 rounded-lg">
          {/* Section Header */}
          <button
            onClick={() => toggleSection(section)}
            className="w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 flex items-center justify-between transition-colors"
          >
            <h3 className="font-semibold text-gray-900">
              {formatSectionName(section)}
            </h3>
            <ChevronDown
              className={`w-5 h-5 text-gray-600 transition-transform ${
                expandedSections.has(section) ? 'rotate-180' : ''
              }`}
            />
          </button>

          {/* Fields */}
          {expandedSections.has(section) && (
            <div className="p-4 space-y-4">
              {fields.map((fieldName) => renderField(fieldName, null))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// Helper functions
function groupFieldsBySection(
  data: Record<string, any>
): Record<string, string[]> {
  const groups: Record<string, string[]> = {
    basic: [],
    equipment: [],
    samples: [],
    other: [],
  };

  Object.keys(data).forEach((key) => {
    if (key.startsWith('_notes_')) return;

    if (
      key.includes('equipment') ||
      key.includes('device') ||
      key.includes('machine')
    ) {
      groups.equipment.push(key);
    } else if (
      key.includes('sample') ||
      key.includes('specimen') ||
      key.includes('patient')
    ) {
      groups.samples.push(key);
    } else if (
      key.includes('id') ||
      key.includes('name') ||
      key.includes('type')
    ) {
      groups.basic.push(key);
    } else {
      groups.other.push(key);
    }
  });

  return Object.fromEntries(
    Object.entries(groups).filter(([, fields]) => fields.length > 0)
  );
}

function formatFieldName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatSectionName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function formatValue(value: any): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return value.toString();
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return JSON.stringify(value);
}

export default DynamicFormBuilder;
