import React, { useState } from 'react';
import { Check, Edit2, AlertCircle, CheckCircle2, MinusCircle, ShieldCheck } from 'lucide-react';

export default function ExtractionTable({
  title,
  rows,
  evidenceList = [],
  notApplicableList = [],
  fieldCorrections = {},
  onVerifyField,
  onSaveCorrection,
  isSubmitting
}) {
  const [editingField, setEditingField] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [editUnit, setEditUnit] = useState('');

  const startEditing = (fieldName, currentValue, currentUnit = '') => {
    setEditingField(fieldName);
    setEditValue(currentValue != null ? String(currentValue) : '');
    setEditUnit(currentUnit || '');
  };

  const handleSave = async (fieldName) => {
    let parsedVal = editValue.trim();
    if (!isNaN(parsedVal) && parsedVal !== '') {
      parsedVal = parseFloat(parsedVal);
    }
    await onSaveCorrection(fieldName, parsedVal, editUnit.trim() || null);
    setEditingField(null);
  };

  const getEvidence = (fieldName) => {
    return evidenceList.find((e) => e.field === fieldName);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden mb-6">
      <div className="px-5 py-3.5 bg-slate-50/70 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50/50 border-b border-slate-200 text-xs font-semibold text-slate-600">
            <tr>
              <th className="px-5 py-2.5 w-1/3">Metric</th>
              <th className="px-4 py-2.5">Value</th>
              <th className="px-4 py-2.5">Unit</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-5 py-2.5 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => {
              const { fieldName, label, value, unit, isExpected } = row;
              const ev = getEvidence(fieldName);
              const correction = fieldCorrections[fieldName];
              const isEditing = editingField === fieldName;
              const isNA = (value == null || value === '') && notApplicableList.includes(fieldName);
              const isMissing = (value == null || value === '') && !isNA;

              return (
                <tr key={fieldName} className="hover:bg-slate-50/50 transition-colors">
                  {/* Metric Name */}
                  <td className="px-5 py-3 font-medium text-slate-800 text-xs sm:text-sm">
                    {label}
                  </td>

                  {/* Value */}
                  <td className="px-4 py-3 text-xs sm:text-sm">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        placeholder="Value"
                        className="px-2 py-1 rounded border border-slate-300 text-xs w-full max-w-[140px] focus:outline-none focus:border-teal-700"
                      />
                    ) : value != null && value !== '' ? (
                      <span className="font-semibold text-slate-900">
                        {typeof value === 'number' ? value.toLocaleString() : value}
                      </span>
                    ) : isNA ? (
                      <span className="text-slate-400 italic text-xs">Not applicable</span>
                    ) : (
                      <span className="text-amber-700 font-medium italic text-xs">Missing — needs review</span>
                    )}
                    {correction && !isEditing && (
                      <p className="text-[10px] text-slate-400">
                        AI: <span className="line-through">{String(correction.original_ai_value ?? 'null')}</span>
                      </p>
                    )}
                  </td>

                  {/* Unit */}
                  <td className="px-4 py-3 text-xs text-slate-600 font-mono">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editUnit}
                        onChange={(e) => setEditUnit(e.target.value)}
                        placeholder="Unit (e.g. kWh)"
                        className="px-2 py-1 rounded border border-slate-300 text-xs w-24 focus:outline-none focus:border-teal-700"
                      />
                    ) : (
                      unit || '—'
                    )}
                  </td>

                  {/* Status Badge */}
                  <td className="px-4 py-3 text-xs">
                    {correction ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                        Human Corrected
                      </span>
                    ) : ev?.is_verified ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        Human Verified
                      </span>
                    ) : isNA ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-500 border border-slate-200">
                        Not applicable
                      </span>
                    ) : isMissing ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                        Needs Review
                      </span>
                    ) : ev?.confidence_level === 'HIGH' || (ev?.confidence && ev.confidence >= 0.9) ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        High ({Math.round((ev?.confidence || 0.95) * 100)}%)
                      </span>
                    ) : ev?.confidence_level === 'MEDIUM' || (ev?.confidence && ev.confidence >= 0.7) ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                        Medium ({Math.round((ev?.confidence || 0.75) * 100)}%)
                      </span>
                    ) : ev ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200">
                        Low ({Math.round((ev?.confidence || 0.5) * 100)}%)
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>

                  {/* Action */}
                  <td className="px-5 py-3 text-right text-xs">
                    {isEditing ? (
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => handleSave(fieldName)}
                          disabled={isSubmitting}
                          className="px-2.5 py-1 bg-teal-700 hover:bg-teal-800 text-white rounded text-xs font-medium"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingField(null)}
                          className="px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded text-xs font-medium"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end space-x-2">
                        {!ev?.is_verified && value != null && value !== '' && (
                          <button
                            onClick={() => onVerifyField(fieldName)}
                            disabled={isSubmitting}
                            className="px-2 py-0.5 text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded font-medium text-xs transition-colors"
                          >
                            Verify
                          </button>
                        )}
                        <button
                          onClick={() => startEditing(fieldName, value, unit)}
                          disabled={isSubmitting}
                          className="px-2 py-0.5 text-slate-600 hover:text-slate-900 border border-slate-200 rounded hover:bg-slate-100 text-xs transition-colors"
                        >
                          Edit
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
