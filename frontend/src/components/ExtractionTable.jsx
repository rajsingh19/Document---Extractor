import React, { useState } from 'react';
import { Edit2, FileText } from 'lucide-react';

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
    <div className="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
      
      {/* Table Title Header */}
      <div className="px-5 py-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-[#0f6b56]" />
          <h3 className="text-xs font-bold text-slate-900">{title}</h3>
        </div>
        <span className="text-[11px] text-slate-500 font-medium">
          {rows.length} parameters tracked
        </span>
      </div>

      {/* Table Data */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50/50 border-b border-slate-200 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              <th className="py-3 px-4 w-5/12">FIELD</th>
              <th className="py-3 px-3">VALUE</th>
              <th className="py-3 px-3">UNIT</th>
              <th className="py-3 px-3">CONFIDENCE</th>
              <th className="py-3 px-3">STATUS</th>
              <th className="py-3 px-4 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => {
              const { fieldName, label, value, unit } = row;
              const ev = getEvidence(fieldName);
              const correction = fieldCorrections[fieldName];
              const isEditing = editingField === fieldName;
              const isNA = (value == null || value === '') && notApplicableList.includes(fieldName);
              const isMissing = (value == null || value === '') && !isNA;

              const confLevel = (ev?.confidence_level || (ev?.confidence >= 0.9 ? 'HIGH' : ev?.confidence >= 0.7 ? 'MEDIUM' : 'LOW')).toUpperCase();

              return (
                <tr key={fieldName} className="hover:bg-slate-50/80 transition-colors">
                  
                  {/* Field Name */}
                  <td className="py-3.5 px-4 font-semibold text-slate-900">
                    {label}
                  </td>

                  {/* Value */}
                  <td className="py-3.5 px-3">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        placeholder="Value"
                        className="px-2.5 py-1 rounded border border-slate-300 text-xs w-full max-w-[130px] focus:outline-none focus:border-[#0f6b56] bg-white"
                        autoFocus
                      />
                    ) : value != null && value !== '' ? (
                      <span className="font-bold text-slate-900">
                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                      </span>
                    ) : isNA ? (
                      <span className="text-slate-400 italic">Not applicable</span>
                    ) : (
                      <span className="text-rose-600 font-bold">Missing</span>
                    )}
                    {correction && !isEditing && (
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        Original: <span className="line-through">{String(correction.original_ai_value ?? 'null')}</span>
                      </p>
                    )}
                  </td>

                  {/* Unit */}
                  <td className="py-3.5 px-3 text-slate-500 font-mono text-xs">
                    {isEditing ? (
                      <input
                        type="text"
                        value={editUnit}
                        onChange={(e) => setEditUnit(e.target.value)}
                        placeholder="Unit"
                        className="px-2 py-1 rounded border border-slate-300 text-xs w-20 focus:outline-none focus:border-[#0f6b56] bg-white"
                      />
                    ) : (
                      unit || ev?.unit || '—'
                    )}
                  </td>

                  {/* Confidence */}
                  <td className="py-3.5 px-3">
                    {value != null && value !== '' ? (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                        confLevel === 'HIGH'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : confLevel === 'MEDIUM'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {confLevel}
                      </span>
                    ) : (
                      <span className="text-slate-300 font-bold">—</span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-3.5 px-3">
                    {correction || ev?.is_verified ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                        Human Verified
                      </span>
                    ) : value != null && value !== '' ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                        AI Extracted
                      </span>
                    ) : isNA ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-500 border border-slate-200">
                        N/A
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        Needs Review
                      </span>
                    )}
                  </td>

                  {/* Action Column */}
                  <td className="py-3.5 px-4 text-right">
                    {isEditing ? (
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => setEditingField(null)}
                          className="px-2 py-1 border border-slate-200 rounded text-slate-600 hover:bg-slate-100 text-xs font-medium"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSave(fieldName)}
                          disabled={isSubmitting}
                          className="px-2.5 py-1 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded text-xs font-semibold shadow-2xs"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end space-x-1">
                        {value != null && value !== '' && !ev?.is_verified && !correction && (
                          <button
                            onClick={() => onVerifyField(fieldName)}
                            disabled={isSubmitting}
                            className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors shadow-2xs"
                            title="Verify value"
                          >
                            Verify
                          </button>
                        )}
                        <button
                          onClick={() => startEditing(fieldName, value, unit || ev?.unit)}
                          className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                          title="Edit value"
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
