import React, { useState } from 'react';
import { Check, Edit2, ShieldCheck, AlertCircle } from 'lucide-react';

export default function ExtractionTable({
  title = "Extracted Information",
  rows = [],
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
    <div className="bg-white border border-slate-200 rounded-lg shadow-2xs overflow-hidden mb-6">
      
      {/* Table Title Header */}
      <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <span className="text-[11px] text-slate-500 font-normal">
          {rows.length} parameters tracked
        </span>
      </div>

      {/* Table Data */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50/50 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <th className="py-2.5 px-4 w-1/3">Field</th>
              <th className="py-2.5 px-3">Value</th>
              <th className="py-2.5 px-3">Unit</th>
              <th className="py-2.5 px-3">Confidence</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-4 text-right">Action</th>
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

              const confLevel = ev?.confidence_level || (ev?.confidence >= 0.9 ? 'High' : ev?.confidence >= 0.7 ? 'Medium' : 'Low');

              return (
                <tr key={fieldName} className="hover:bg-slate-50/60 transition-colors">
                  
                  {/* Field Name */}
                  <td className="py-3 px-4 font-medium text-slate-900">
                    {label}
                  </td>

                  {/* Value */}
                  <td className="py-3 px-3">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        placeholder="Value"
                        className="px-2 py-1 rounded border border-slate-300 text-xs w-full max-w-[130px] focus:outline-none focus:border-teal-700 bg-white"
                        autoFocus
                      />
                    ) : value != null && value !== '' ? (
                      <span className="font-semibold text-slate-900">
                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                      </span>
                    ) : isNA ? (
                      <span className="text-slate-400 italic">Not applicable</span>
                    ) : (
                      <span className="text-amber-700 font-medium">Missing</span>
                    )}
                    {correction && !isEditing && (
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        Original AI: <span className="line-through">{String(correction.original_ai_value ?? 'null')}</span>
                      </p>
                    )}
                  </td>

                  {/* Unit */}
                  <td className="py-3 px-3 text-slate-600 font-mono text-[11px]">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editUnit}
                        onChange={(e) => setEditUnit(e.target.value)}
                        placeholder="Unit (e.g. kWh)"
                        className="px-2 py-1 rounded border border-slate-300 text-xs w-20 focus:outline-none focus:border-teal-700 bg-white"
                      />
                    ) : (
                      unit || ev?.unit || '—'
                    )}
                  </td>

                  {/* Confidence */}
                  <td className="py-3 px-3">
                    {value != null && value !== '' ? (
                      <span className={`inline-flex items-center px-1.5 py-0.2 rounded text-[11px] font-medium border ${
                        confLevel.toLowerCase() === 'high'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : confLevel.toLowerCase() === 'medium'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {confLevel}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-3 px-3">
                    {correction || ev?.is_verified ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                        Human Verified
                      </span>
                    ) : value != null && value !== '' ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        AI Extracted
                      </span>
                    ) : isNA ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-50 text-slate-400 border border-slate-200">
                        N/A
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                        Needs Review
                      </span>
                    )}
                  </td>

                  {/* Action Column */}
                  <td className="py-3 px-4 text-right">
                    {isEditing ? (
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => setEditingField(null)}
                          className="px-2 py-0.5 border border-slate-200 rounded text-slate-600 hover:bg-slate-100 text-xs"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSave(fieldName)}
                          disabled={isSubmitting}
                          className="px-2.5 py-0.5 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded text-xs font-semibold shadow-2xs"
                        >
                          Save Correction
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end space-x-1">
                        {value != null && value !== '' && !ev?.is_verified && !correction && (
                          <button
                            onClick={() => onVerifyField(fieldName)}
                            disabled={isSubmitting}
                            className="px-2 py-0.5 bg-white hover:bg-slate-100 border border-slate-200 rounded text-slate-700 text-xs font-medium transition-colors shadow-2xs"
                            title="Verify value"
                          >
                            Verify
                          </button>
                        )}
                        <button
                          onClick={() => startEditing(fieldName, value, unit || ev?.unit)}
                          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                          title="Correct value"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
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
