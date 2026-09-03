import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ArrowLeft, 
  FileDown, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Info, 
  Layers, 
  Clock, 
  Building2, 
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  FileCheck,
  CheckSquare
} from 'lucide-react';
import { 
  getGreenFinanceAssessment, 
  generateGreenFinanceAssessment, 
  updateGreenFinanceAssessmentStatus, 
  finalizeGreenFinanceAssessment,
  getGreenFinanceAssessmentPdfUrl
} from '../services/api';

export default function GreenFinanceDetail({ assessmentId, onNavigate }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [finalizing, setFinalizing] = useState(false);

  // Requirement inspection modal
  const [selectedRequirement, setSelectedRequirement] = useState(null);

  // Status modal
  const [statusModal, setStatusModal] = useState(false);
  const [newStatus, setNewStatus] = useState('READY_FOR_APPLICATION');
  const [statusNote, setStatusNote] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    loadAssessment();
  }, [assessmentId]);

  const loadAssessment = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getGreenFinanceAssessment(assessmentId);
      setAssessment(data);
    } catch (err) {
      console.error("Failed to load assessment details:", err);
      setError("Unable to load green finance assessment details.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      setGenerating(true);
      const data = await generateGreenFinanceAssessment(assessmentId);
      setAssessment(data);
    } catch (err) {
      console.error("Failed to regenerate assessment:", err);
    } finally {
      setGenerating(false);
    }
  };

  const handleFinalize = async () => {
    try {
      setFinalizing(true);
      const data = await finalizeGreenFinanceAssessment(assessmentId);
      setAssessment(data);
    } catch (err) {
      console.error("Failed to finalize assessment:", err);
    } finally {
      setFinalizing(false);
    }
  };

  const handleStatusUpdate = async (e) => {
    e.preventDefault();
    try {
      setUpdatingStatus(true);
      await updateGreenFinanceAssessmentStatus(assessmentId, newStatus, statusNote || null);
      setStatusModal(false);
      loadAssessment();
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const getBandBadge = (band) => {
    switch (band) {
      case 'READY_FOR_REVIEW':
        return <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">READY FOR REVIEW</span>;
      case 'PARTIALLY_READY':
        return <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-amber-100 text-amber-800 border border-amber-300">PARTIALLY READY</span>;
      case 'NOT_READY':
        return <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-rose-100 text-rose-800 border border-rose-300">NOT READY</span>;
      default:
        return <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">{band}</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-12 text-center text-slate-500">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-emerald-600 mb-2" />
        Loading readiness assessment...
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 p-12 text-center text-slate-500">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <p className="font-semibold text-slate-800">{error || "Assessment not found."}</p>
        <button
          onClick={() => onNavigate && onNavigate('green-finance')}
          className="mt-4 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium"
        >
          Back to Assessments
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* NAVIGATION & ACTIONS */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <button
            onClick={() => onNavigate && onNavigate('green-finance')}
            className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900 text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Green Finance Engine
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRegenerate}
              disabled={generating || assessment.status === 'FINALIZED'}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl border border-slate-200 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
              Re-evaluate Readiness
            </button>
            <button
              onClick={() => setStatusModal(true)}
              disabled={assessment.status === 'FINALIZED'}
              className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl transition-colors disabled:opacity-50"
            >
              Update Workflow Status
            </button>
            <button
              onClick={handleFinalize}
              disabled={finalizing || assessment.status === 'FINALIZED'}
              className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl transition-colors disabled:opacity-50"
            >
              {finalizing ? 'Finalizing...' : 'Finalize Assessment'}
            </button>
            <a
              href={getGreenFinanceAssessmentPdfUrl(assessment.id)}
              download
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors shadow-sm flex items-center gap-1.5"
            >
              <FileDown className="w-4 h-4" />
              Download PDF Report
            </a>
          </div>
        </div>

        {/* HEADER SCORE CARD */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-bold px-2.5 py-0.5 bg-emerald-50 text-emerald-800 rounded border border-emerald-200">
                  {assessment.assessment_code}
                </span>
                {getBandBadge(assessment.readiness_band)}
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
                  {assessment.status}
                </span>
              </div>
              <h1 className="text-xl font-bold text-slate-900">{assessment.business_name}</h1>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-right">
                <span className="text-xs uppercase font-semibold text-slate-400 block">Overall Readiness Score</span>
                <div className="text-3xl font-black text-slate-900 font-mono mt-0.5">
                  {assessment.overall_readiness_score} <span className="text-sm font-medium text-slate-400">/ 100</span>
                </div>
              </div>
            </div>
          </div>

          {/* DISCLAIMER BOX */}
          <div className="bg-emerald-50/70 p-3.5 rounded-xl border border-emerald-200 flex items-start gap-2.5 text-xs text-emerald-900">
            <Info className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="block font-semibold">APPLICATION READINESS DISCLAIMER</strong>
              <p className="mt-0.5">{assessment.disclaimer}</p>
            </div>
          </div>
        </div>

        {/* 10 DIMENSIONS GRID */}
        <div className="space-y-3">
          <h2 className="text-base font-bold text-slate-900">10 Readiness Dimensions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
            {assessment.dimensions.map((dim) => (
              <div
                key={dim.category}
                className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-500 font-mono">{dim.category}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      dim.status === 'SUPPORTED' ? 'bg-emerald-50 text-emerald-700 font-bold' : 'bg-amber-50 text-amber-700 font-bold'
                    }`}>
                      {dim.status}
                    </span>
                  </div>
                  <h3 className="text-xs font-bold text-slate-900 line-clamp-1">{dim.title}</h3>
                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{dim.explanation}</p>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-900">{dim.score}%</span>
                  <span className="text-[10px] text-slate-400">{dim.supported_count}/{dim.total_count} Criteria</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* TWO COLUMN LAYOUT: MISSING & NEXT ACTIONS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* MISSING REQUIREMENTS */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              What is Missing? ({assessment.missing_requirements.length})
            </h3>

            {assessment.missing_requirements.length === 0 ? (
              <p className="text-xs text-slate-500">All core sustainability readiness requirements are supported!</p>
            ) : (
              <div className="space-y-3 text-xs">
                {assessment.missing_requirements.map((m) => (
                  <div key={m.requirement_code} className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-800">{m.requirement_code}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        m.priority === 'HIGH' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'
                      }`}>
                        {m.priority} PRIORITY
                      </span>
                    </div>
                    <strong className="block text-slate-900">{m.requirement_name}</strong>
                    <p className="text-slate-600">{m.reason}</p>
                    <div className="text-blue-700 font-semibold pt-1">
                      Action Needed: {m.what_is_needed}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* RECOMMENDED NEXT ACTIONS */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
              Recommended Next Actions ({assessment.next_actions.length})
            </h3>

            <div className="space-y-3 text-xs">
              {assessment.next_actions.map((act, idx) => (
                <div key={idx} className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-700">{act.category}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800">
                      {act.priority}
                    </span>
                  </div>
                  <strong className="block text-slate-900">{act.action}</strong>
                  <p className="text-slate-600">{act.reason}</p>
                  <span className="text-emerald-700 font-semibold block pt-0.5">
                    Impact: {act.expected_readiness_impact}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* APPLICATION CHECKLIST TABLE */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-blue-600" />
            Application Readiness Document & Evidence Checklist
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4 w-32">Category</th>
                  <th className="py-3 px-4 w-36">Code</th>
                  <th className="py-3 px-4">Requirement Title</th>
                  <th className="py-3 px-4 w-28">Check Status</th>
                  <th className="py-3 px-4">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assessment.checklist.map((chk, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-500">{chk.category}</td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-700">{chk.item_code}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{chk.title}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                        chk.status === 'READY' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                      }`}>
                        {chk.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-600">{chk.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* STATUS UPDATE MODAL */}
        {statusModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">Update Assessment Status</h3>
                <button
                  onClick={() => setStatusModal(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleStatusUpdate} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Workflow Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="DRAFT">DRAFT</option>
                    <option value="GENERATED">GENERATED</option>
                    <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                    <option value="READY_FOR_APPLICATION">READY_FOR_APPLICATION</option>
                    <option value="FINALIZED">FINALIZED (Immutable)</option>
                  </select>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setStatusModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updatingStatus}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {updatingStatus ? 'Updating...' : 'Save Workflow Status'}
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
