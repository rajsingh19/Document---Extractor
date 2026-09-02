import React, { useState } from 'react';
import { FileText, BarChart3, Activity, X, CheckCircle2, ShieldCheck, Database, Cpu, Sparkles } from 'lucide-react';

export default function Navbar({ activeTab, onSelectTab, health, onSeedSample, isSeeding, attentionCount = 0 }) {
  const [showStatusModal, setShowStatusModal] = useState(false);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Left: Brand & Main Navigation */}
          <div className="flex items-center space-x-6">
            <div 
              onClick={() => onSelectTab('documents')}
              className="flex items-center space-x-2.5 cursor-pointer select-none"
            >
              <div className="w-7 h-7 rounded-md bg-[#0f6b56] text-white flex items-center justify-center font-bold text-sm shadow-xs">
                S
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-slate-900 text-sm tracking-tight leading-tight">
                  Senseible
                </span>
                <span className="text-[10px] text-slate-400 font-medium tracking-normal leading-none">
                  Document Intelligence
                </span>
              </div>
            </div>

            <nav className="flex space-x-1 pl-2">
              <button
                onClick={() => onSelectTab('documents')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'documents'
                    ? 'bg-slate-100 text-slate-900 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Documents</span>
              </button>

              <button
                onClick={() => onSelectTab('metrics')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'metrics'
                    ? 'bg-slate-100 text-slate-900 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5 text-slate-500" />
                <span>Metrics</span>
              </button>
            </nav>
          </div>

          {/* Right: Sample Documents & System Status */}
          <div className="flex items-center space-x-3">
            {onSeedSample && (
              <div className="hidden md:flex items-center space-x-1.5 text-xs">
                <span className="text-slate-400 text-[11px] font-medium mr-1">Demo Data:</span>
                <button
                  onClick={() => onSeedSample('electricity')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded text-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
                  title="Load fictional Demo Electricity Bill"
                >
                  Electricity Bill
                </button>
                <button
                  onClick={() => onSeedSample('esg')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded text-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
                  title="Load fictional Demo ESG Audit"
                >
                  ESG Audit
                </button>
                <button
                  onClick={() => onSeedSample('scanned')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded text-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
                  title="Load fictional Demo Waste Manifest"
                >
                  Waste Manifest
                </button>
              </div>
            )}

            {/* System Status Button */}
            <button
              onClick={() => setShowStatusModal(true)}
              className="flex items-center space-x-1.5 pl-3 border-l border-slate-200 text-xs hover:opacity-80 transition-opacity"
              title="View system status"
            >
              <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-slate-600 font-medium hidden sm:inline text-xs">
                System Status
              </span>
            </button>
          </div>

        </div>
      </div>

      {/* Clean System Status Modal */}
      {showStatusModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/30 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-lg max-w-sm w-full p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <Activity className="w-4 h-4 text-[#0f6b56]" />
                <h3 className="text-sm font-semibold text-slate-900">System Status</h3>
              </div>
              <button
                onClick={() => setShowStatusModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <Cpu className="w-3.5 h-3.5 text-slate-500" />
                  <span>Backend API</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Healthy
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <Database className="w-3.5 h-3.5 text-slate-500" />
                  <span>Database</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Connected
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
                  <span>Extraction Engine</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Available
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  <span>OCR Service</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {health?.ocr_available ? 'Available' : 'Installed'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <Sparkles className="w-3.5 h-3.5 text-slate-500" />
                  <span>LLM Extraction</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                  {health?.openai_configured ? 'Configured (Live)' : 'Deterministic Active'}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setShowStatusModal(false)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
