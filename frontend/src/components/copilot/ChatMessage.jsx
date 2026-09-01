import React from 'react';
import { Bot, User, Sparkles, CheckCircle2, FileText, ArrowRight, ExternalLink } from 'lucide-react';

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
