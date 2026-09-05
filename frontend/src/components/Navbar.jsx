import React, { useState } from 'react';
import { FileText, BarChart3, Activity, X, ShieldCheck, Database, Cpu, Sparkles, Layers, Calculator, BookOpen, Lightbulb, FolderKanban, Award, TrendingUp, Target } from 'lucide-react';


export default function Navbar({ activeTab, onSelectTab, health, onSeedSample, isSeeding }) {
  const [showStatusModal, setShowStatusModal] = useState(false);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Left: Brand & Navigation */}
          <div className="flex items-center space-x-6">
            <div 
              onClick={() => onSelectTab('documents')}
              className="flex items-center space-x-2.5 cursor-pointer select-none"
            >
              <div className="w-7 h-7 rounded-md bg-[#0F6B56] text-white flex items-center justify-center font-bold text-sm shadow-2xs">
                S
              </div>
              <span className="font-bold text-slate-900 text-sm tracking-tight">
                Senseible Document Extractor
              </span>
            </div>

            <nav className="flex space-x-1 pl-2">
              <button
                onClick={() => onSelectTab('documents')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'documents'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Documents</span>
              </button>

              <button
                onClick={() => onSelectTab('metrics')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'metrics'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Metrics</span>
              </button>

              <button
                onClick={() => onSelectTab('emission-factors')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'emission-factors'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>Emission Factors</span>
              </button>

              <button
                onClick={() => onSelectTab('activity-data')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'activity-data'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Activity Data</span>
              </button>

              <button
                onClick={() => onSelectTab('carbon-dashboard')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'carbon-dashboard'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Carbon Footprint</span>
              </button>

              <button
                onClick={() => onSelectTab('forecast')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'forecast'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span>Forecast</span>
              </button>

              <button
                onClick={() => onSelectTab('reduction-intelligence')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'reduction-intelligence'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Target className="w-3.5 h-3.5" />
                <span>Reduction Intelligence</span>
              </button>

              <button
                onClick={() => onSelectTab('reduction-roadmap')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'reduction-roadmap'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Roadmap</span>
              </button>

              <button
                onClick={() => onSelectTab('reduction-opportunities')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'reduction-opportunities'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Lightbulb className="w-3.5 h-3.5" />
                <span>Opportunities</span>
              </button>


              <button
                onClick={() => onSelectTab('reduction-projects')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'reduction-projects'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <FolderKanban className="w-3.5 h-3.5" />
                <span>Projects</span>
              </button>

              <button
                onClick={() => onSelectTab('compliance-reports')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'compliance-reports' || activeTab === 'compliance-report-detail'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Compliance Reports</span>
              </button>

              <button
                onClick={() => onSelectTab('green-finance')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'green-finance' || activeTab === 'green-finance-detail'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Green Finance</span>
              </button>

              <button
                onClick={() => onSelectTab('carbon-credit')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'carbon-credit' || activeTab === 'carbon-credit-detail'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Award className="w-3.5 h-3.5" />
                <span>Carbon Credits</span>
              </button>



              <button
                onClick={() => onSelectTab('carbon-calculations')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'carbon-calculations'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Calculator className="w-3.5 h-3.5" />
                <span>Calculations</span>
              </button>

              <button
                onClick={() => onSelectTab('carbon-ledger')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === 'carbon-ledger'
                    ? 'bg-[#EAF7F2] text-[#0F6B56]'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Ledger</span>
              </button>
            </nav>
          </div>

          {/* Right: Sample PDFs & System Online */}
          <div className="flex items-center space-x-3">
            {onSeedSample && (
              <div className="hidden lg:flex items-center space-x-1.5 text-xs">
                <span className="text-slate-400 text-[11px] font-medium mr-1">Sample PDFs:</span>
                <button
                  onClick={() => onSeedSample('electricity')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
                  title="Load Electricity Bill sample"
                >
                  Electricity Bill
                </button>
                <button
                  onClick={() => onSeedSample('esg')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
                  title="Load ESG Audit sample"
                >
                  ESG Audit
                </button>
                <button
                  onClick={() => onSeedSample('scanned')}
                  disabled={isSeeding}
                  className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-md text-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
                  title="Load Waste Manifest sample"
                >
                  Waste Manifest
                </button>
              </div>
            )}

            {/* System Status / Online Indicator */}
            <button
              onClick={() => setShowStatusModal(true)}
              className="flex items-center space-x-1.5 pl-3 border-l border-slate-200 text-xs hover:opacity-80 transition-opacity"
              title="View system status"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-slate-600 font-medium hidden sm:inline text-xs">
                System Online
              </span>
            </button>
          </div>

        </div>
      </div>

      {/* System Status Modal */}
      {showStatusModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-2xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-xl max-w-sm w-full p-5 shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <Activity className="w-4 h-4 text-[#0F6B56]" />
                <h3 className="text-sm font-bold text-slate-900">System Status</h3>
              </div>
              <button
                onClick={() => setShowStatusModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <Cpu className="w-3.5 h-3.5 text-slate-500" />
                  <span>Backend API</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Healthy
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <Database className="w-3.5 h-3.5 text-slate-500" />
                  <span>Database</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Connected
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
                  <span>Extraction Engine</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Available (PyMuPDF / Tesseract)
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                <div className="flex items-center space-x-2 text-slate-700">
                  <Sparkles className="w-3.5 h-3.5 text-slate-500" />
                  <span>LLM Extraction</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {health?.openai_configured ? 'Configured (Live)' : 'Deterministic Active'}
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setShowStatusModal(false)}
                className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-md transition-colors"
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
