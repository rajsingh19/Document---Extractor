import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileSearch, CheckCircle2 } from 'lucide-react';

export default function EvidenceSection({ evidence = [] }) {
  const [isOpen, setIsOpen] = useState(true);

  if (!evidence || evidence.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden mb-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-3.5 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between text-left hover:bg-slate-100/50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <FileSearch className="w-4 h-4 text-teal-700" />
          <h3 className="text-sm font-semibold text-slate-900">
            Source Evidence Anchors ({evidence.length})
          </h3>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
      </button>

      {isOpen && (
        <div className="p-5 space-y-3.5">
          {evidence.map((item, idx) => {
            const confLevel = item.confidence_level || (item.confidence >= 0.9 ? 'High' : item.confidence >= 0.7 ? 'Medium' : 'Low');
            const confPercent = item.confidence ? Math.round(item.confidence * 100) : 90;

            return (
              <div key={idx} className="p-3.5 rounded-md border border-slate-200 bg-white space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-900 text-sm">
                      {item.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                    <span className="text-slate-600 font-medium">
                      {item.human_corrected_value != null ? (
                        <span>{item.human_corrected_value} {item.unit || ''} (Corrected)</span>
                      ) : (
                        <span>{item.value != null ? item.value.toLocaleString() : '—'} {item.unit || ''}</span>
                      )}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    {item.is_verified && (
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        Verified
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                      confLevel === 'High' || confPercent >= 90
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : confLevel === 'Medium' || confPercent >= 70
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}>
                      Confidence: {confLevel} ({confPercent}%)
                    </span>
                  </div>
                </div>

                {item.source_text && (
                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-slate-700 font-mono text-[11px] leading-relaxed">
                    "{item.source_text}"
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
