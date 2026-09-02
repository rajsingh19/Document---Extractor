import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  Send, 
  Sparkles, 
  Loader2, 
  AlertCircle, 
  RefreshCw, 
  FileText,
  ChevronRight,
  Target
} from 'lucide-react';
import { askCopilot } from '../../services/api';

export default function DocumentChatbot({ document: doc, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastQuestion, setLastQuestion] = useState(null);
  const chatBottomRef = useRef(null);

  // Reset chat when document changes to ensure strict document isolation
  useEffect(() => {
    setMessages([]);
    setInput('');
    setErrorMessage(null);
    setLastQuestion(null);
  }, [doc?.id]);

  // Scroll chat to bottom on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Handle escape key to close drawer
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!doc) return null;

  const companyName = doc.company_name || 'Organization';
  const docType = doc.document_type || 'Document';
  const docTitle = doc.original_filename || doc.filename;

  const suggestedQuestions = [
    "Summarize this document",
    "What electricity consumption is reported?",
    "What emissions are reported?",
    "What is the peak demand?",
    "Are any fields missing?",
    "Explain the extraction quality"
  ];

  const handleSendMessage = async (userText) => {
    const question = (userText || input).trim();
    if (!question || isLoading) return;

    // Append user question
    const updatedMessages = [...messages, { role: 'user', content: question }];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);
    setErrorMessage(null);
    setLastQuestion(question);

    // Prepare conversational history turns
    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content
    }));

    try {
      // Send question with document ID to ground exclusively on this document
      const response = await askCopilot(question, historyPayload, doc.id);
      
      setMessages([
        ...updatedMessages,
        {
          role: 'assistant',
          content: response.answer || "I couldn't find that information in this document.",
          sources: response.sources || [],
          recommendations: response.recommendations || []
        }
      ]);
    } catch (err) {
      console.error('Document chatbot error:', err);
      setErrorMessage("Unable to reach the assistant. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (lastQuestion) {
      handleSendMessage(lastQuestion);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Dimmed Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-900/20 backdrop-blur-2xs transition-opacity"
        onClick={onClose}
      />

      {/* Right Drawer */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md sm:max-w-lg bg-white border-l border-slate-200 shadow-2xl flex flex-col">
          
          {/* 1. DRAWER HEADER */}
          <div className="p-4 border-b border-slate-200 bg-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 rounded bg-emerald-50 text-[#0f6b56] border border-emerald-200 flex items-center justify-center">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <h2 className="text-sm font-bold text-slate-900">Ask AI</h2>
              </div>
              <button
                onClick={onClose}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                title="Close chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Document Context Header Info */}
            <div className="mt-2.5 pt-2 border-t border-slate-100">
              <div className="text-xs font-semibold text-slate-800 truncate">
                {companyName}
              </div>
              <div className="text-[11px] text-slate-500 flex items-center space-x-1.5 truncate mt-0.5">
                <span className="font-medium text-slate-600">{docType}</span>
                <span>&bull;</span>
                <span className="truncate">{docTitle}</span>
              </div>
            </div>
          </div>

          {/* 2. CHAT STREAM / CONTENT */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/40">
            
            {/* Suggested Questions Section */}
            <div className="bg-white border border-slate-200 rounded-lg p-3.5 shadow-2xs space-y-2">
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <span>Suggested questions</span>
                <span className="text-[10px] text-[#0f6b56] font-medium lowercase">This document only</span>
              </div>
              <div className="flex flex-col gap-1.5">
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(q)}
                    disabled={isLoading}
                    className="w-full text-left px-2.5 py-1.5 rounded bg-slate-50 hover:bg-emerald-50/50 hover:text-[#0f6b56] border border-slate-200 hover:border-emerald-200 text-xs text-slate-700 transition-colors flex items-center justify-between group disabled:opacity-50"
                  >
                    <span className="truncate">{q}</span>
                    <ChevronRight className="w-3 h-3 text-slate-400 group-hover:text-[#0f6b56] shrink-0" />
                  </button>
                ))}
              </div>
            </div>

            {/* Message History */}
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              if (isUser) {
                return (
                  <div key={index} className="flex justify-end">
                    <div className="max-w-[85%] bg-slate-900 text-white rounded-lg px-3.5 py-2 text-xs shadow-2xs">
                      <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                );
              }

              return (
                <div key={index} className="flex justify-start">
                  <div className="max-w-[92%] bg-white border border-slate-200 rounded-lg p-3.5 text-xs shadow-2xs space-y-2.5">
                    <div className="flex items-center space-x-1.5 text-[11px] font-semibold text-[#0f6b56]">
                      <Sparkles className="w-3 h-3" />
                      <span>Document Assistant</span>
                    </div>

                    <div className="text-slate-800 leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </div>

                    {/* Verified Evidence Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="pt-1.5 border-t border-slate-100 flex flex-wrap gap-1">
                        <span className="text-[10px] text-slate-400 self-center mr-1">Source:</span>
                        {msg.sources.slice(0, 3).map((src, sIdx) => {
                          const fName = typeof src === 'object' && src.field ? src.field.replace(/_/g, ' ') : 'Extracted Field';
                          return (
                            <span 
                              key={sIdx}
                              className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-100 text-[10px] text-slate-600 border border-slate-200"
                              title={typeof src === 'object' && src.source_text ? `Evidence: "${src.source_text}"` : fName}
                            >
                              <FileText className="w-2.5 h-2.5 text-[#0f6b56]" />
                              <span>{fName}</span>
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-slate-200 rounded-lg px-3.5 py-2.5 text-xs text-slate-600 shadow-2xs flex items-center space-x-2">
                  <Loader2 className="w-3.5 h-3.5 text-[#0f6b56] animate-spin shrink-0" />
                  <span>Checking document data...</span>
                </div>
              </div>
            )}

            {/* Error Message with Retry */}
            {errorMessage && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs space-y-2">
                <div className="flex items-center space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                  <span className="font-semibold">{errorMessage}</span>
                </div>
                <button
                  onClick={handleRetry}
                  className="inline-flex items-center space-x-1 px-2 py-0.5 bg-white border border-rose-200 rounded text-rose-700 text-xs font-medium hover:bg-rose-50"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Try Again</span>
                </button>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>

          {/* 3. INPUT FORM */}
          <div className="p-3 border-t border-slate-200 bg-white">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center space-x-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about this document..."
                disabled={isLoading}
                className="flex-1 px-3 py-2 bg-white border border-slate-200 rounded-md text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0f6b56] shadow-2xs disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="px-3 py-2 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded-md text-xs font-semibold transition-colors shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center shrink-0"
                title="Send question"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </div>
      </div>
    </div>
  );
}
