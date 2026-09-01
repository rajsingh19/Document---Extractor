import React from 'react';
import { FileText, BarChart3 } from 'lucide-react';

export default function Navbar({ activeTab, onSelectTab, health, onSeedSample, isSeeding }) {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Left: Brand & Main Nav */}
          <div className="flex items-center space-x-6">
            <div 
              onClick={() => onSelectTab('documents')}
              className="flex items-center space-x-2.5 cursor-pointer select-none"
            >
              <div className="w-7 h-7 rounded-lg bg-[#0f6b56] text-white flex items-center justify-center font-bold text-sm shadow-xs">
                S
              </div>
              <span className="font-bold text-slate-900 text-sm tracking-tight">
                Senseible Document Extractor
              </span>
            </div>

            <nav className="flex space-x-1.5 pl-2">
              <button
                onClick={() => onSelectTab('documents')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 border ${
                  activeTab === 'documents'
                    ? 'bg-slate-100/90 text-slate-900 border-slate-200/80 font-semibold'
                    : 'bg-transparent text-slate-600 border-transparent hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Documents</span>
              </button>

              <button
                onClick={() => onSelectTab('metrics')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 border ${
                  activeTab === 'metrics'
                    ? 'bg-slate-100/90 text-slate-900 border-slate-200/80 font-semibold'
                    : 'bg-transparent text-slate-600 border-transparent hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5 text-slate-500" />
                <span>Metrics</span>
              </button>
            </nav>
          </div>

          {/* Right: Sample Buttons & System Status */}
          <div className="flex items-center space-x-3">
            {onSeedSample && (
              <div className="hidden lg:flex items-center space-x-1.5 text-xs">
                <span className="text-slate-400 mr-1 text-[11px]">Sample PDFs:</span>
                <button
                  onClick={() => onSeedSample('electricity')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors shadow-xs disabled:opacity-50"
                  title="Load sample Electricity Bill"
                >
                  Electricity Bill
                </button>
                <button
                  onClick={() => onSeedSample('esg')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors shadow-xs disabled:opacity-50"
                  title="Load sample ESG Audit"
                >
                  ESG Audit
                </button>
                <button
                  onClick={() => onSeedSample('scanned')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors shadow-xs disabled:opacity-50"
                  title="Load sample Waste Manifest"
                >
                  Waste Manifest
                </button>
              </div>
            )}

            {/* System Status Indicator */}
            <div className="flex items-center space-x-1.5 pl-3 border-l border-slate-200 text-xs">
              <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-slate-600 font-medium hidden sm:inline text-xs">
                {health?.status === 'healthy' ? 'System Online' : 'Connecting...'}
              </span>
            </div>
          </div>

        </div>
      </div>
    </header>
  );
}
