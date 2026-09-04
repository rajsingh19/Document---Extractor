import React, { useState, useEffect } from 'react';
import { 
  Award, 
  PlusCircle, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  FileDown, 
  ArrowRight, 
  FolderKanban, 
  Layers, 
  Calendar, 
  Filter,
  Info,
  ChevronRight,
  TrendingUp,
  AlertTriangle,
  FileText,
  ShieldAlert,
  Sparkles
} from 'lucide-react';
import { 
  getCarbonCreditAssessments, 
  createCarbonCreditAssessment, 
  generateCarbonCreditAssessment,
  getReductionProjects,
  getCarbonCreditAssessmentPdfUrl
} from '../services/api';

export default function CarbonCredit({ onNavigate }) {
  const [assessments, setAssessments] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [projectFilter, setProjectFilter] = useState('');

  // Create Modal
  const [createModal, setCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    project_id: '',
    reporting_period: '2024-10',
    notes: '',
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
    loadProjects();
  }, [statusFilter, projectFilter]);

  const loadProjects = async () => {
    try {
      const data = await getReductionProjects();
      setProjects(data.projects || []);
      if (data.projects && data.projects.length > 0 && !createForm.project_id) {
        setCreateForm(prev => ({ ...prev, project_id: data.projects[0].id }));
      }
    } catch (err) {
      console.error("Failed to load reduction projects:", err);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (projectFilter) params.project_id = projectFilter;
      const data = await getCarbonCreditAssessments(params);
      setAssessments(data.items || []);
    } catch (err) {
      console.error("Failed to load carbon credit assessments:", err);
      setError("Unable to load carbon credit assessments.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAssessment = async (e) => {
    e.preventDefault();
    if (!createForm.project_id) {
      alert("Please select a reduction project.");
      return;
    }
    try {
      setCreating(true);
      // 1. Create draft assessment
      const ass = await createCarbonCreditAssessment({
        project_id: parseInt(createForm.project_id, 10),
        reporting_period: createForm.reporting_period,
        notes: createForm.notes || undefined,
      });
      // 2. Generate assessment deterministically
      await generateCarbonCreditAssessment(ass.id);
      setCreateModal(false);
      
      if (onNavigate) {
        onNavigate('carbon-credit-detail', ass.id);
      } else {
        loadData();
      }
    } catch (err) {
      console.error("Failed to create assessment:", err);
      alert(err.response?.data?.detail || "Failed to create assessment.");
    } finally {
      setCreating(false);
    }
  };

  const getBandBadge = (band) => {
    switch (band) {
      case 'READY_FOR_METHODOLOGY_REVIEW':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#EAF7F2] text-[#0F6B56] border border-[#0F6B56]/30">
            READY FOR METHODOLOGY REVIEW
          </span>
        );
      case 'PARTIALLY_READY':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
            PARTIALLY READY
          </span>
        );
      case 'NOT_READY':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
            NOT READY
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {band}
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Award className="w-7 h-7 text-[#0F6B56]" />
              Carbon Credit Readiness & Project Eligibility
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Assess whether your reduction project is prepared for methodology and certification review.
            </p>
          </div>
          <button
            onClick={() => setCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#0F6B56] hover:bg-[#0c5343] text-white font-medium text-sm rounded-xl shadow-xs transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            New Project Readiness Assessment
          </button>
        </div>

        {/* PRODUCT BOUNDARY & DISCLAIMER NOTICE */}
        <div className="bg-[#EAF7F2] p-4 rounded-xl border border-[#0F6B56]/20 flex items-start gap-3 text-xs text-slate-800">
          <Info className="w-4 h-4 text-[#0F6B56] flex-shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold block text-sm text-[#0F6B56]">CRITICAL PRODUCT BOUNDARY NOTICE</strong>
            <p className="mt-0.5">
              This assessment measures project documentation and evidence readiness for standard review. It does <strong>not</strong> issue, verify, guarantee, or estimate tradable carbon credits. Carbon footprint reductions do not automatically constitute carbon credits without third-party validation and registry issuance.
            </p>
          </div>
        </div>

        {/* FILTERS */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
            >
              <option value="">All Workflow Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="GENERATED">Generated</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="READY_FOR_METHODOLOGY_REVIEW">Ready for Methodology Review</option>
              <option value="FINALIZED">Finalized</option>
            </select>

            <select
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
            >
              <option value="">All Reduction Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.project_code} - {p.title}
                </option>
              ))}
            </select>

            {(statusFilter || projectFilter) && (
              <button
                onClick={() => {
                  setStatusFilter('');
                  setProjectFilter('');
                }}
                className="text-xs text-slate-500 hover:text-slate-800 underline"
              >
                Clear Filters
              </button>
            )}
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* ASSESSMENTS LIST / TABLE */}
        {loading ? (
          <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-500 shadow-xs">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#0F6B56] mb-2" />
            Loading project readiness assessments...
          </div>
        ) : error ? (
          <div className="bg-white p-8 rounded-2xl border border-rose-200 text-center text-rose-600 shadow-xs">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : assessments.length === 0 ? (
          <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-500 shadow-xs space-y-3">
            <Award className="w-12 h-12 mx-auto text-slate-300" />
            <h3 className="text-base font-semibold text-slate-800">No Carbon Credit Assessments Found</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Create a readiness assessment for an active decarbonization project to evaluate baseline, monitoring, accounting, and documentation posture.
            </p>
            <button
              onClick={() => setCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#0F6B56] hover:bg-[#0c5343] text-white font-medium text-xs rounded-xl shadow-xs transition-all mt-2"
            >
              <PlusCircle className="w-4 h-4" />
              Create First Assessment
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="divide-y divide-slate-100">
              {assessments.map((a) => (
                <div
                  key={a.id}
                  className="p-5 hover:bg-slate-50/80 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer"
                  onClick={() => onNavigate && onNavigate('carbon-credit-detail', a.id)}
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono text-xs font-semibold text-[#0F6B56] bg-[#EAF7F2] px-2 py-0.5 rounded">
                        {a.assessment_code}
                      </span>
                      <h2 className="text-base font-bold text-slate-900">{a.project_name}</h2>
                      {getBandBadge(a.readiness_band)}
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                        v{a.assessment_version}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        Period: <b>{a.reporting_period}</b>
                      </span>
                      <span className="flex items-center gap-1">
                        <FolderKanban className="w-3.5 h-3.5" />
                        Status: <b>{a.status}</b>
                      </span>
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5" />
                        Methodology: <b>{a.methodology_status}</b>
                      </span>
                    </div>
                  </div>

                  {/* SCORE & ACTIONS */}
                  <div className="flex items-center gap-5">
                    <div className="text-right">
                      <div className="text-xl font-extrabold text-slate-900">
                        {a.overall_readiness_score.toFixed(1)} <span className="text-xs text-slate-400 font-normal">/ 100</span>
                      </div>
                      <div className="text-[11px] text-slate-500">Readiness Score</div>
                    </div>

                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                      <a
                        href={getCarbonCreditAssessmentPdfUrl(a.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                        title="Download PDF Report"
                      >
                        <FileDown className="w-4 h-4" />
                      </a>

                      <button
                        onClick={() => onNavigate && onNavigate('carbon-credit-detail', a.id)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition-colors"
                      >
                        View Details
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* CREATE ASSESSMENT MODAL */}
      {createModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                <Award className="w-5 h-5 text-[#0F6B56]" />
                New Project Readiness Assessment
              </h3>
              <button
                onClick={() => setCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateAssessment} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Target Reduction Project *
                </label>
                {projects.length === 0 ? (
                  <p className="text-xs text-rose-600">
                    No reduction projects found. Please create a reduction project first in Projects tab.
                  </p>
                ) : (
                  <select
                    required
                    value={createForm.project_id}
                    onChange={(e) => setCreateForm({ ...createForm, project_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
                  >
                    <option value="">Select Reduction Project</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.project_code} - {p.title} ({p.category || 'General'})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Reporting Period Context *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2024-10"
                  value={createForm.reporting_period}
                  onChange={(e) => setCreateForm({ ...createForm, reporting_period: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Assessment Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Scoping assessment for solar captive power expansion."
                  value={createForm.notes}
                  onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
                />
              </div>

              <div className="bg-[#EAF7F2] p-3 rounded-xl border border-[#0F6B56]/20 text-[11px] text-slate-700 space-y-1">
                <p className="font-semibold text-[#0F6B56]">Deterministic Evaluation Engine:</p>
                <p>
                  Generates an immediate audit of project definition, baseline records, activity data, posted carbon ledger entries, monitoring, and verification readiness.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCreateModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || projects.length === 0}
                  className="px-4 py-2 bg-[#0F6B56] hover:bg-[#0c5343] disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                >
                  {creating && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  {creating ? 'Evaluating...' : 'Create & Evaluate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
