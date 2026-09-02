import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  Send, 
  Sparkles, 
  Loader2, 
  AlertCircle, 
  RefreshCw, 
  FileText,
  Copy,
  Check,
  ArrowRight,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { askCopilot } from '../../services/api';

export default function DocumentChatbot({ document: doc, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastQuestion, setLastQuestion] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const chatBottomRef = useRef(null);

  // Reset chat state when document changes to guarantee strict document isolation
  useEffect(() => {
    setMessages([]);
    setInput('');
    setErrorMessage(null);
    setLastQuestion(null);
    setExpandedSources({});
  }, [doc?.id]);

  // Scroll to bottom on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Escape key listener to close drawer
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

  const companyName = doc.company_name || 'TARA ENGINEERING WORKS';
  const docType = doc.document_type || 'Electricity Bill';
  const docFilename = doc.original_filename || doc.filename || 'msme_test_invoice.pdf';

  // Dynamic suggested questions based on document type
  const getSuggestedQuestions = (typeStr) => {
    const type = (typeStr || '').toLowerCase();
    if (type.includes('electricity') || type.includes('bill') || type.includes('energy') || type.includes('power')) {
      return [
        "Summarize this document",
        "What is the electricity consumption?",
        "What is the peak demand recorded?",
        "Which fields are missing?",
        "Why does this document need review?"
      ];
    }
    if (type.includes('esg') || type.includes('audit') || type.includes('emission') || type.includes('carbon')) {
      return [
        "Summarize this document",
        "What carbon emissions are reported?",
        "What is the compliance status?",
        "Which fields are missing?",
        "Why does this document need review?"
      ];
    }
    if (type.includes('waste') || type.includes('manifest') || type.includes('hazardous')) {
      return [
        "Summarize this document",
        "What waste quantities are reported?",
        "What hazardous waste is recorded?",
        "Which fields are missing?",
        "Why does this document need review?"
      ];
    }
    return [
      "Summarize this document",
      "What key metrics are reported?",
      "Which fields are missing?",
      "Explain the extraction quality score",
      "Why does this document need review?"
    ];
  };

  const suggestedQuestions = getSuggestedQuestions(docType);

  const handleSendMessage = async (userText) => {
    const question = (userText || input).trim();
    if (!question || isLoading) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Append user message
    const updatedMessages = [
      ...messages, 
      { role: 'user', content: question, time: timeStr }
    ];
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);
    setErrorMessage(null);
    setLastQuestion(question);

    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content
    }));

    try {
      // Ground exclusively on currently open document_id
      const response = await askCopilot(question, historyPayload, doc.id);
      
      setMessages([
        ...updatedMessages,
        {
          role: 'assistant',
          content: response.answer || "I couldn't find that information in this document.",
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sources: response.sources || []
        }
      ]);
    } catch (err) {
      console.error('Document chatbot error:', err);
      setErrorMessage("Unable to reach the AI assistant. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyText = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const toggleSourceExpand = (idx) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleRetry = () => {
    if (lastQuestion) {
      handleSendMessage(lastQuestion);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Subtle Backdrop Overlay */}
      <div 
        className="fixed inset-0 bg-[#0f172a]/12 backdrop-blur-[1px] transition-opacity"
        onClick={onClose}
      />

      {/* Right AI Drawer Container (420px - 460px Desktop) */}
      <div className="relative w-full sm:w-[440px] md:w-[460px] bg-white border-l border-[#DDE5E9] shadow-2xl flex flex-col z-10 h-[calc(100vh-56px)] mt-[56px] transition-all duration-250 ease-out">
        
        {/* 1. DRAWER HEADER */}
        <div className="px-5 py-3.5 border-b border-[#DDE5E9] bg-white flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-[#EAF7F2] text-[#0F6B56] flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4 text-[#0F6B56]" />
            </div>
            <div>
              <h2 className="text-[18px] font-bold text-[#102A43] leading-tight">Ask AI</h2>
              <p className="text-xs font-medium text-[#6B7C93] leading-tight">Document Assistant</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#6B7C93] hover:text-[#102A43] hover:bg-slate-100 transition-colors"
            title="Close drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 2. DRAWER BODY STREAM */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F7F9FB]">
          
          {/* Active Document Context Indicator Card */}
          <div className="bg-[#EAF7F2] border border-[#0F6B56]/20 rounded-xl p-3.5 space-y-2 shadow-2xs">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-10 bg-rose-50 border border-rose-200/80 rounded-lg flex flex-col items-center justify-center text-rose-600 shrink-0">
                <FileText className="w-4 h-4" />
                <span className="text-[8px] font-bold tracking-tight">PDF</span>
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-xs font-bold text-[#102A43] truncate">{docType}</h3>
                <p className="text-xs font-semibold text-[#102A43]/80 truncate">{companyName}</p>
                <p className="text-[11px] font-medium text-[#6B7C93] truncate">{docFilename}</p>
              </div>
            </div>

            {/* Active Indicator Pill */}
            <div className="pt-2 border-t border-[#0F6B56]/15 flex items-center space-x-1.5 text-[11px] font-bold text-[#0F6B56]">
              <span className="w-2 h-2 rounded-full bg-[#0F6B56] animate-pulse shrink-0" />
              <span>Using this document</span>
            </div>
          </div>

          {/* EMPTY CHAT STATE (Before User Asks Anything) */}
          {messages.length === 0 && (
            <div className="py-2 space-y-4">
              
              {/* Centered Contextual Banner */}
              <div className="flex flex-col items-center justify-center text-center p-3">
                <div className="w-10 h-10 rounded-full bg-[#EAF7F2] text-[#0F6B56] flex items-center justify-center shadow-2xs">
                  <Sparkles className="w-5 h-5 text-[#0F6B56]" />
                </div>
                <h3 className="text-xs font-bold text-[#102A43] mt-2">
                  Ask anything about this document
                </h3>
                <p className="text-[11px] text-[#6B7C93] text-center max-w-xs leading-relaxed mt-0.5 font-medium">
                  I can help explain extracted values, missing fields, evidence, and quality scores.
                </p>
              </div>

              {/* Dynamic Suggested Questions Cards */}
              <div className="space-y-2">
                <h4 className="text-[10px] font-extrabold tracking-wider text-[#6B7C93] uppercase px-1">
                  ASK ABOUT THIS DOCUMENT
                </h4>
                
                <div className="space-y-1.5">
                  {suggestedQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(q)}
                      disabled={isLoading}
                      className="w-full text-left p-3 bg-white hover:bg-[#EAF7F2]/50 border border-[#DDE5E9] hover:border-[#0F6B56]/50 rounded-xl text-xs font-medium text-[#102A43] transition-all flex items-center justify-between shadow-2xs group disabled:opacity-50"
                    >
                      <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                        <Sparkles className="w-3.5 h-3.5 text-[#0F6B56] shrink-0" />
                        <span className="truncate">{q}</span>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-[#6B7C93] group-hover:text-[#0F6B56] shrink-0 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>

            </div>
          )}

          {/* Time Divider */}
          {messages.length > 0 && (
            <div className="flex items-center justify-center my-2">
              <span className="px-3 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-[#6B7C93]">
                Today
              </span>
            </div>
          )}

          {/* Messages Stream */}
          {messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            if (isUser) {
              return (
                <div key={index} className="flex justify-end space-y-1 flex-col items-end">
                  <div className="max-w-[85%] bg-[#EAF7F2] border border-[#0F6B56]/20 text-[#102A43] rounded-2xl rounded-tr-xs px-4 py-2.5 text-xs shadow-2xs font-medium">
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  <span className="text-[10px] text-[#6B7C93] pr-1">{msg.time || '2:05 PM'}</span>
                </div>
              );
            }

            return (
              <div key={index} className="flex justify-start space-y-1 flex-col items-start">
                <div className="max-w-[92%] bg-white border border-[#DDE5E9] text-[#102A43] rounded-2xl rounded-tl-xs p-4 text-xs shadow-2xs space-y-2.5">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-[#0F6B56]">
                    <Sparkles className="w-3.5 h-3.5 text-[#0F6B56]" />
                    <span>✦ AI</span>
                  </div>

                  <div className="text-[#102A43] leading-relaxed whitespace-pre-wrap font-medium">
                    {msg.content}
                  </div>

                  {/* Expandable Source Evidence Chip */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-1 border-t border-slate-100">
                      <button
                        onClick={() => toggleSourceExpand(index)}
                        className="inline-flex items-center space-x-1 text-[10px] font-semibold text-[#0F6B56] hover:underline"
                      >
                        <span>Source: Document Evidence ({msg.sources.length})</span>
                        {expandedSources[index] ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>

                      {expandedSources[index] && (
                        <div className="mt-1.5 p-2 bg-slate-50 border border-[#DDE5E9] rounded-lg text-[10px] font-mono text-slate-700 space-y-1 max-h-32 overflow-y-auto">
                          {msg.sources.map((src, sIdx) => (
                            <div key={sIdx} className="leading-tight">
                              <span className="font-bold text-[#102A43]">
                                {typeof src === 'object' && src.field ? src.field : 'Extracted Field'}:
                              </span>{' '}
                              "{typeof src === 'object' && src.source_text ? src.source_text : 'Grounded document excerpt'}"
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1 text-[10px] text-[#6B7C93]">
                    <span>{msg.time || '2:05 PM'}</span>
                    <button
                      onClick={() => handleCopyText(msg.content, index)}
                      className="flex items-center space-x-1 px-1.5 py-0.5 rounded hover:bg-slate-100 text-[#6B7C93] hover:text-[#102A43] transition-colors"
                      title="Copy response"
                    >
                      {copiedIndex === index ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span className="text-emerald-700 font-bold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Loading State */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-[#DDE5E9] rounded-2xl px-4 py-3 text-xs text-[#102A43] shadow-2xs flex items-center space-x-2.5">
                <Loader2 className="w-4 h-4 text-[#0F6B56] animate-spin shrink-0" />
                <span className="font-semibold">Reading document...</span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-3.5 text-xs space-y-2">
              <div className="flex items-center space-x-1.5">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span className="font-semibold">{errorMessage}</span>
              </div>
              <button
                onClick={handleRetry}
                className="inline-flex items-center space-x-1 px-2.5 py-1 bg-white border border-rose-200 rounded-md text-rose-700 text-xs font-semibold hover:bg-rose-50"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Try Again</span>
              </button>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* 3. STICKY CHAT INPUT AT BOTTOM */}
        <div className="p-3.5 border-t border-[#DDE5E9] bg-white space-y-2 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2"
          >
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about this document..."
                disabled={isLoading}
                className="w-full h-11 pl-3.5 pr-10 bg-slate-50/70 border border-[#DDE5E9] focus:border-[#0F6B56] focus:bg-white rounded-xl text-xs text-[#102A43] placeholder-[#6B7C93] focus:outline-none transition-colors shadow-2xs font-medium disabled:opacity-50"
              />
            </div>
            
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="w-11 h-11 bg-[#0F6B56] hover:bg-[#0c5947] text-white rounded-xl flex items-center justify-center transition-all shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
              title="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Footer Disclaimer */}
          <p className="text-[10px] text-center text-[#6B7C93] font-medium">
            AI responses are based on this document.
          </p>
        </div>

      </div>
    </div>
  );
}
