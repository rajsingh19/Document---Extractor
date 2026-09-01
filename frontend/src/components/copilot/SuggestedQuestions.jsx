import React from 'react';
import { HelpCircle, ChevronRight } from 'lucide-react';

export default function SuggestedQuestions({ onSelectQuestion, disabled = false }) {
  const suggestions = [
    "What needs my attention?",
    "What sustainability data is missing?",
    "Why did emissions change?",
    "How can I reduce emissions?",
    "Show my latest metrics"
  ];

  return (
    <div className="space-y-2.5">
      <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
        Suggested questions
      </p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((q, idx) => (
          <button
            key={idx}
            onClick={() => onSelectQuestion(q)}
            disabled={disabled}
            className="px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-md text-xs font-medium text-slate-700 text-left transition-colors shadow-2xs flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <span>{q}</span>
            <ChevronRight className="w-3 h-3 text-slate-400 group-hover:text-slate-600 transition-colors" />
          </button>
        ))}
      </div>
    </div>
  );
}
