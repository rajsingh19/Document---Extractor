import React from 'react';
import { Leaf, Cpu, CheckCircle2, AlertCircle, RefreshCw, FileText } from 'lucide-react';

export default function Navbar({ health, onRefresh, isRefreshing }) {
  return (
    <header className="sticky top-0 z-30 glass-panel border-b border-slate-800/80 px-4 sm:px-8 py-3.5 shadow-xl">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        
        {/* Brand & Logo */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 p-0.5 shadow-lg shadow-emerald-500/20 flex items-center justify-center">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Leaf className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                Senseible <span className="text-emerald-400 font-semibold">Document AI</span>
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                MSME MVP
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              Automated Sustainability & ESG Document Intelligence
            </p>
          </div>
        </div>

        {/* Integration Status Badges & Controls */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* OpenAI Integration Status */}
          <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
            health?.openai_configured 
              ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50' 
              : 'bg-amber-950/60 text-amber-300 border-amber-700/50'
          }`}>
            <Cpu className="w-3.5 h-3.5" />
            <span>LLM: {health?.openai_configured ? (health?.openai_model || 'OpenAI Live') : 'Heuristic Engine'}</span>
          </div>

          {/* OCR Engine Status */}
          <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
            health?.ocr_available 
              ? 'bg-blue-950/60 text-blue-300 border-blue-700/50' 
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}>
            <FileText className="w-3.5 h-3.5" />
            <span>OCR: {health?.ocr_available ? 'Tesseract Ready' : 'Disabled'}</span>
          </div>

          {/* System Health */}
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700/80">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>API Online</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/80 transition-all disabled:opacity-50"
            title="Refresh dashboard data"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>

      </div>
    </header>
  );
}
