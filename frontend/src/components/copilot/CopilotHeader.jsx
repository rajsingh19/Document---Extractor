import React from 'react';
import { Sparkles, Trash2 } from 'lucide-react';

export default function CopilotHeader({ onClearChat, messageCount = 0 }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
      <div>
        <div className="flex items-center space-x-2">
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">AI Copilot</h1>
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Preview
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">
          Your sustainability operations assistant. Ask questions about your documents and sustainability data.
        </p>
      </div>

      {messageCount > 0 && (
        <button
          onClick={onClearChat}
          className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 rounded text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors shadow-2xs self-start sm:self-auto"
          title="Clear conversation"
        >
          <Trash2 className="w-3.5 h-3.5 text-slate-400" />
          <span>Clear Chat</span>
        </button>
      )}
    </div>
  );
}
