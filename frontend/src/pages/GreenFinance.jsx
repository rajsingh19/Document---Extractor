import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  PlusCircle, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  FileDown, 
  ArrowRight, 
  Building2, 
  Layers, 
  Calendar, 
  Filter,
  Info,
  ChevronRight,
  TrendingUp,
  AlertTriangle,
  FileText
} from 'lucide-react';
import { 
  getGreenFinanceAssessments, 
  createGreenFinanceAssessment, 
  generateGreenFinanceAssessment,
  getGreenFinanceAssessmentPdfUrl
} from '../services/api';

export default function GreenFinance({ onNavigate }) {
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');

  // Create Modal
  const [createModal, setCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    reporting_period: '2024-10',
    business_name: 'TARA ENGINEERING WORKS',
    notes: '',
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      const data = await getGreenFinanceAssessments(params);
      setAssessments(data.items || []);
    } catch (err) {
      console.error("Failed to load green finance assessments:", err);
      setError("Unable to load green finance assessments.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAssessment = async (e) => {
    e.preventDefault();
    try {
      setCreating(true);
      // 1. Create draft assessment
      const ass = await createGreenFinanceAssessment(createForm);
      // 2. Generate assessment deterministically
      await generateGreenFinanceAssessment(ass.id);
      setCreateModal(false);
      
      if (onNavigate) {
        onNavigate('green-finance-detail', ass.id);
      } else {
        loadData();
      }
    } catch (err) {
      console.error("Failed to create assessment:", err);
    } finally {
      setCreating(false);
    }
  };

  const getBandBadge = (band) => {
    switch (band) {
      case 'READY_FOR_REVIEW':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">READY FOR REVIEW</span>;
      case 'PARTIALLY_READY':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">PARTIALLY READY</span>;
      case 'NOT_READY':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">NOT READY</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">{band}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-7 h-7 text-emerald-600" />
              Green Finance Readiness Engine
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Prepare your sustainability evidence and documentation for green-finance review.
            </p>
          </div>
          <button
            onClick={() => setCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-xl shadow-sm transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            New Readiness Assessment
          </button>
        </div>

        {/* PRODUCT BOUNDARY NOTICE */}
        <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200 flex items-start gap-3 text-xs text-emerald-950">
          <Info className="w-4 h-4 text-emerald-700 flex-shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold block text-sm">LENDER READINESS PREPARATION NOTICE</strong>
            <p className="mt-0.5">
              This score measures the completeness and quality of sustainability-related application evidence available in Senseible. 
              It is <strong>not</strong> a lender credit score, loan eligibility score, approval prediction, or financing guarantee. Credit underwriting and financial assessment are strictly performed by your financial institution.
            </p>
          </div>
        </div>

        {/* FILTERS */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Workflow Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="GENERATED">Generated</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="FINALIZED">Finalized</option>
            </select>

            {statusFilter && (
              <button
                onClick={() => setStatusFilter('')}
                className="text-xs text-rose-600 hover:text-rose-700 font-medium"
              >
                Clear Filter
              </button>
            )}
          </div>
        </div>

        {/* ASSESSMENTS LIST */}
        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
            Loading readiness assessments...
          </div>
        ) : assessments.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <ShieldCheck className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-medium text-slate-800">No Green Finance Readiness assessments prepared yet.</p>
            <p className="text-xs text-slate-400 mt-1">Click "New Readiness Assessment" to evaluate your application posture.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {assessments.map((ass) => (
              <div
                key={ass.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all p-5"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {ass.assessment_code}
                      </span>
                      {getBandBadge(ass.readiness_band)}
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
                        {ass.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-2xl font-black text-slate-900 font-mono">
                        {ass.overall_readiness_score} <span className="text-sm font-normal text-slate-400">/ 100</span>
                      </div>
                      <div>
                        <h3 
                          onClick={() => onNavigate && onNavigate('green-finance-detail', ass.id)}
                          className="text-base font-semibold text-slate-900 hover:text-emerald-700 transition-colors cursor-pointer"
                        >
                          {ass.business_name}
                        </h3>
                        <p className="text-xs text-slate-500">
                          Reporting Period: <strong>{ass.reporting_period}</strong> | Version: <strong>{ass.assessment_version}</strong>
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
                      <span className="bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-emerald-800 font-medium">
                        Supported Criteria: <strong>{ass.supported_requirements} / {ass.total_requirements}</strong>
                      </span>
                      {ass.missing_requirements_count > 0 && (
                        <span className="bg-rose-50 px-2 py-0.5 rounded border border-rose-200 text-rose-800 font-medium">
                          Missing Criteria: <strong>{ass.missing_requirements_count}</strong>
                        </span>
                      )}
                      <span className="text-slate-400">
                        Generated {ass.generated_at ? new Date(ass.generated_at).toLocaleDateString() : 'Draft'}
                      </span>
                    </div>
                  </div>

                  {/* ACTIONS */}
                  <div className="flex items-center gap-2">
                    <a
                      href={getGreenFinanceAssessmentPdfUrl(ass.id)}
                      download
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg border border-slate-200 transition-colors flex items-center gap-1.5"
                    >
                      <FileDown className="w-3.5 h-3.5 text-slate-600" />
                      PDF Report
                    </a>
                    <button
                      onClick={() => onNavigate && onNavigate('green-finance-detail', ass.id)}
                      className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1"
                    >
                      <span>View Assessment</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* CREATE ASSESSMENT MODAL */}
        {createModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">New Green Finance Readiness Assessment</h3>
                <button
                  onClick={() => setCreateModal(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateAssessment} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Reporting Period</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 2024-10"
                    value={createForm.reporting_period}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, reporting_period: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Business Entity Name</label>
                  <input
                    type="text"
                    required
                    value={createForm.business_name}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, business_name: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-500 flex items-start gap-2">
                  <Info className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <p>
                    Readiness is evaluated across 10 core dimensions from <strong>POSTED</strong> carbon ledger entries, utility metrics, reduction projects, and evidence provenance. Missing data is never treated as zero.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setCreateModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {creating ? 'Evaluating Readiness...' : 'Evaluate Readiness'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
