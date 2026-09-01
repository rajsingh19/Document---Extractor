import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

export default function ChatInput({ onSendMessage, isLoading = false, placeholder = "Ask about your documents..." }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setInput('');
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-2xs focus-within:border-teal-700 transition-colors">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
          aria-label="Ask Copilot a question"
          className="flex-1 max-h-32 min-h-[38px] py-2 px-2.5 bg-transparent resize-none text-xs text-slate-900 placeholder-slate-400 focus:outline-none disabled:opacity-50"
        />

        <button
          type="button"
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          aria-label="Send question"
          className="p-2 rounded-md bg-[#0f6b56] hover:bg-[#0c5947] text-white disabled:opacity-40 disabled:hover:bg-[#0f6b56] disabled:cursor-not-allowed transition-colors shrink-0 shadow-2xs"
        >
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      <div className="flex items-center justify-between px-2 pt-1.5 text-[10px] text-slate-400">
        <span>Press <b>Enter</b> to send, <b>Shift + Enter</b> for new line</span>
        <span>Senseible Copilot (Step 11A)</span>
      </div>
    </div>
  );
}
