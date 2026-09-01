import React from 'react';
import { FileSearch } from 'lucide-react';

export default function EvidenceSection({ evidence = [] }) {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6 shadow-2xs text-center text-xs text-slate-500">
        No source evidence anchors recorded for this document.
      </div>
    );
  }

  const formatConfidence = (confLevel, confScore) => {
    const level = (confLevel || (confScore >= 0.9 ? 'High' : confScore >= 0.7 ? 'Medium' : 'Low')).toLowerCase();
    if (level === 'high' || confScore >= 0.9) {
      return {
        label: 'High confidence',
        hint: null,
        badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200'
      };
    }
    if (level === 'medium' || confScore >= 0.7) {
      return {
        label: 'Medium confidence',
        hint: 'Review recommended.',
        badgeClass: 'bg-amber-50 text-amber-700 border-amber-200'
      };
    }
    return {
      label: 'Low confidence',
      hint: 'Please verify this value against the source document.',
      badgeClass: 'bg-rose-50 text-rose-700 border-rose-200'
    };
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-2xs overflow-hidden mb-6">
      
      {/* Header */}
      <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileSearch className="w-4 h-4 text-[#0f6b56]" />
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Source Evidence ({evidence.length})
            </h3>
            <p className="text-[11px] text-slate-500">
              Verifiable text excerpts showing where the extraction engine located each value.
            </p>
          </div>
        </div>
      </div>

      {/* Evidence List */}
      <div className="divide-y divide-slate-100">
        {evidence.map((item, idx) => {
          const conf = formatConfidence(item.confidence_level, item.confidence);
          const fieldName = item.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          const displayValue = item.human_corrected_value != null ? item.human_corrected_value : item.value;

          return (
            <div key={idx} className="p-4 space-y-2 text-xs hover:bg-slate-50/50 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-slate-900 text-xs">
                    {fieldName}
                  </span>
                  <span className="text-slate-400">&bull;</span>
                  <span className="font-medium text-slate-800">
                    {displayValue != null ? (
                      typeof displayValue === 'number' ? displayValue.toLocaleString() : String(displayValue)
                    ) : '—'} {item.unit || ''}
                  </span>
                  {item.human_corrected_value != null && (
                    <span className="text-[10px] text-purple-700 font-medium bg-purple-50 px-1.5 py-0.2 rounded border border-purple-200">
                      Human Verified
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${conf.badgeClass}`}>
                    {conf.label}
                  </span>
                </div>
              </div>

              {/* Source Text Snippet */}
              {item.source_text ? (
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-slate-700 font-mono text-[11px] leading-relaxed">
                  <span className="text-slate-400 font-sans mr-1">Source:</span>
                  "{item.source_text}"
                </div>
              ) : (
                <p className="text-slate-400 italic text-[11px]">No exact source text excerpt.</p>
              )}

              {/* Explanatory hint for medium/low confidence */}
              {conf.hint && (
                <p className="text-[11px] text-amber-700 font-medium">
                  {conf.hint}
                </p>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
}
