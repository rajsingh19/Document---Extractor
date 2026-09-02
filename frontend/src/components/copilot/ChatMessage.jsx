import React from 'react';
import { Bot, User, Sparkles, CheckCircle2, FileText, ArrowRight, ExternalLink, Lightbulb, Target } from 'lucide-react';

export default function ChatMessage({ message, onSelectAction, onSelectSource }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg bg-slate-900 text-white rounded-lg px-4 py-2.5 text-xs shadow-2xs space-y-1">
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-2xl w-full bg-white border border-slate-200 rounded-lg p-4 text-xs shadow-2xs space-y-3">
        {/* Assistant Header Tag */}
        <div className="flex items-center space-x-1.5 pb-2 border-b border-slate-100 text-slate-500">
          <Sparkles className="w-3.5 h-3.5 text-[#0f6b56]" />
          <span className="font-semibold text-slate-800 text-[11px]">Senseible Copilot</span>
          {message.intent && (
            <span className="text-[10px] text-slate-400">&bull; {message.intent.replace(/_/g, ' ')}</span>
          )}
        </div>

        {/* Content Body */}
        <div className="text-slate-800 leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Structured Recommended Actions (Step 11E) */}
        {message.recommendations && message.recommendations.length > 0 && (
          <div className="pt-2 border-t border-slate-100 space-y-2.5">
            <div className="flex items-center space-x-1.5 text-slate-700 font-semibold text-[11px]">
              <Target className="w-3.5 h-3.5 text-[#0f6b56]" />
              <span>Recommended Actions:</span>
            </div>

            <div className="space-y-2">
              {message.recommendations.slice(0, 3).map((rec, i) => (
                <div
                  key={rec.id || i}
                  className="bg-slate-50 border border-slate-200 rounded-md p-3 text-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{rec.title}</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-200 text-slate-700 uppercase">
                      {rec.category}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-600 space-y-1">
                    <p><strong className="text-slate-700">Why:</strong> {rec.reason}</p>
                    {rec.suggested_actions && rec.suggested_actions.length > 0 && (
                      <div>
                        <strong className="text-slate-700">Next steps:</strong>
                        <ul className="list-disc list-inside text-slate-600 pl-1 mt-0.5 space-y-0.5">
                          {rec.suggested_actions.slice(0, 2).map((act, aIdx) => (
                            <li key={aIdx}>{act}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {rec.source_document_id && onSelectSource && (
                    <div className="pt-1 flex items-center justify-between border-t border-slate-200/60">
                      <button
                        onClick={() => onSelectSource(rec.source_document_id)}
                        className="text-[10px] text-[#0f6b56] hover:underline font-medium inline-flex items-center space-x-1"
                      >
                        <FileText className="w-2.5 h-2.5" />
                        <span>Source: Doc #{rec.source_document_id}</span>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Verified Sources Chips */}
        {message.sources && message.sources.length > 0 && (
          <div className="pt-2 border-t border-slate-100 space-y-1.5">
            <span className="text-[11px] font-medium text-slate-400">Sources:</span>
            <div className="flex flex-wrap gap-1.5">
              {message.sources.map((src, i) => {
                const docName = typeof src === 'string' ? src : (src.document_name || src.filename || 'Document');
                const docId = typeof src === 'object' ? src.document_id : null;
                const fieldName = typeof src === 'object' && src.field ? ` (${src.field.replace(/_/g, ' ')})` : '';

                return (
                  <button
                    key={i}
                    onClick={() => onSelectSource && docId && onSelectSource(docId)}
                    className="inline-flex items-center space-x-1 px-2 py-1 rounded bg-slate-50 hover:bg-slate-100 border border-slate-200 text-[11px] text-slate-700 font-medium transition-colors group cursor-pointer"
                    title={typeof src === 'object' && src.source_text ? `Evidence: "${src.source_text}"` : docName}
                  >
                    <FileText className="w-3 h-3 text-[#0f6b56] group-hover:text-teal-800" />
                    <span>{docName}{fieldName}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Suggested Next Steps / Actions */}
        {message.actions && message.actions.length > 0 && (
          <div className="pt-2 border-t border-slate-100 space-y-1.5">
            <span className="text-[11px] font-medium text-slate-400">Suggested Next Steps:</span>
            <div className="flex flex-wrap gap-1.5">
              {message.actions.map((act, i) => {
                const label = typeof act === 'string' ? act : (act.label || 'Action');
                return (
                  <button
                    key={i}
                    onClick={() => onSelectAction && onSelectAction(act)}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-50 hover:bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-700 transition-colors"
                  >
                    <span>{label}</span>
                    <ArrowRight className="w-2.5 h-2.5 text-slate-400" />
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
