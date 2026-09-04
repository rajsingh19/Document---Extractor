import React, { useState, useEffect } from 'react';
import { 
  Award, 
  ArrowLeft, 
  FileDown, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Info, 
  Layers, 
  Clock, 
  FolderKanban, 
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  FileCheck,
  CheckSquare,
  ShieldCheck,
  Building2,
  Calendar,
  Lock,
  ArrowRight,
  FileText
} from 'lucide-react';
import { 
  getCarbonCreditAssessment, 
  generateCarbonCreditAssessment, 
  updateCarbonCreditAssessmentStatus, 
  finalizeCarbonCreditAssessment,
  getCarbonCreditAssessmentPdfUrl
} from '../services/api';

export default function CarbonCreditDetail({ assessmentId, onNavigate }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [finalizing, setFinalizing] = useState(false);

  // Requirement inspection modal
  const [selectedRequirement, setSelectedRequirement] = useState(null);

  // Status modal
  const [statusModal, setStatusModal] = useState(false);
  const [newStatus, setNewStatus] = useState('READY_FOR_METHODOLOGY_REVIEW');
  const [statusNote, setStatusNote] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    loadAssessment();
  }, [assessmentId]);

  const loadAssessment = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCarbonCreditAssessment(assessmentId);
      setAssessment(data);
    } catch (err) {
      console.error("Failed to load carbon credit assessment details:", err);
      setError("Unable to load carbon credit assessment details.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      setGenerating(true);
      const data = await generateCarbonCreditAssessment(assessmentId);
      setAssessment(data);
    } catch (err) {
      console.error("Failed to regenerate assessment:", err);
      alert(err.response?.data?.detail || "Failed to regenerate assessment.");
    } finally {
      setGenerating(false);
    }
  };

  const handleFinalize = async () => {
    if (!window.confirm("Are you sure you want to finalize this assessment? Finalized assessments are immutable and cannot be regenerated.")) {
      return;
    }
    try {
      setFinalizing(true);
      const data = await finalizeCarbonCreditAssessment(assessmentId);
      setAssessment(data);
    } catch (err) {
      console.error("Failed to finalize assessment:", err);
      alert(err.response?.data?.detail || "Failed to finalize assessment.");
    } finally {
      setFinalizing(false);
    }
  };

  const handleStatusUpdate = async (e) => {
    e.preventDefault();
    try {
      setUpdatingStatus(true);
      await updateCarbonCreditAssessmentStatus(assessmentId, newStatus, statusNote || null);
      setStatusModal(false);
      loadAssessment();
    } catch (err) {
      console.error("Failed to update status:", err);
      alert(err.response?.data?.detail || "Failed to update status.");
    } finally {
      setUpdatingStatus(false);
    }
  };

  const getBandBadge = (band) => {
    switch (band) {
      case 'READY_FOR_METHODOLOGY_REVIEW':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-[#EAF7F2] text-[#0F6B56] border border-[#0F6B56]/30">
            READY FOR METHODOLOGY REVIEW
          </span>
        );
      case 'PARTIALLY_READY':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-amber-100 text-amber-800 border border-amber-300">
            PARTIALLY READY
          </span>
        );
      case 'NOT_READY':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-rose-100 text-rose-800 border border-rose-300">
            NOT READY
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {band}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-12 text-center text-slate-500">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#0F6B56] mb-2" />
        Loading carbon credit readiness assessment...
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen bg-slate-50 p-12 text-center text-slate-500">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <p className="font-semibold text-slate-800">{error || "Assessment not found."}</p>
        <button
          onClick={() => onNavigate && onNavigate('carbon-credit')}
          className="mt-4 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium"
        >
          Back to Assessments
        </button>
      </div>
    );
  }

  const isFinalized = assessment.status === 'FINALIZED';

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* TOP NAVIGATION & ACTIONS */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <button
            onClick={() => onNavigate && onNavigate('carbon-credit')}
            className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900 text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Carbon Credit Engine
          </button>

          <div className="flex items-center gap-2 flex-wrap">
            {!isFinalized && (
              <>
                <button
                  onClick={handleRegenerate}
                  disabled={generating}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-xl shadow-2xs transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
                  {generating ? 'Evaluating...' : 'Re-Evaluate'}
                </button>

                <button
                  onClick={() => setStatusModal(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-xl shadow-2xs transition-colors"
                >
                  Update Status
                </button>

                <button
                  onClick={handleFinalize}
                  disabled={finalizing}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#0F6B56] hover:bg-[#0c5343] text-white text-xs font-semibold rounded-xl shadow-2xs transition-colors"
                >
                  <Lock className="w-3.5 h-3.5" />
                  {finalizing ? 'Finalizing...' : 'Finalize Assessment'}
                </button>
              </>
            )}

            {isFinalized && (
              <span className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-200 text-slate-700 text-xs font-bold rounded-xl">
                <Lock className="w-3.5 h-3.5" /> Finalized (Immutable)
              </span>
            )}

            <a
              href={getCarbonCreditAssessmentPdfUrl(assessment.id)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-black text-white text-xs font-medium rounded-xl shadow-2xs transition-colors"
            >
              <FileDown className="w-3.5 h-3.5" />
              Download PDF Report
            </a>
          </div>
        </div>

        {/* MANDATORY DISCLAIMER */}
        <div className="bg-[#EAF7F2] p-4 rounded-xl border border-[#0F6B56]/20 flex items-start gap-3 text-xs text-slate-800">
          <Info className="w-4 h-4 text-[#0F6B56] flex-shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold block text-sm text-[#0F6B56]">CRITICAL PRODUCT BOUNDARY NOTICE</strong>
            <p className="mt-0.5">
              {assessment.disclaimer}
            </p>
          </div>
        </div>

        {/* SCORE & EXECUTIVE BANNER */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono text-xs font-bold text-[#0F6B56] bg-[#EAF7F2] px-2.5 py-1 rounded-md">
                {assessment.assessment_code}
              </span>
              <h1 className="text-xl font-extrabold text-slate-900">{assessment.project_name}</h1>
              {getBandBadge(assessment.readiness_band)}
              <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                Version {assessment.assessment_version}
              </span>
            </div>

            <p className="text-xs text-slate-600">
              Assesses whether your reduction project has sufficient project definition, baseline traceability, activity data, carbon accounting, reduction evidence, monitoring, measurement history, and verification readiness to begin formal methodology and standard review.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
              <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Reporting Period</span>
                <span className="font-bold text-slate-800">{assessment.reporting_period}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Category & Scope</span>
                <span className="font-bold text-slate-800">{assessment.project_category || 'General'} ({assessment.project_scope || 'N/A'})</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Methodology Status</span>
                <span className="font-bold text-slate-800">{assessment.methodology_status}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Standard Alignment</span>
                <span className="font-bold text-slate-800">{assessment.standard_status}</span>
              </div>
            </div>
          </div>

          {/* SCORE CARD */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white p-5 rounded-xl flex flex-col justify-between items-center text-center shadow-xs">
            <div className="w-full">
              <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                Readiness Score
              </span>
              <div className="text-4xl font-black mt-2 text-emerald-400">
                {assessment.overall_readiness_score.toFixed(1)}
                <span className="text-sm font-normal text-slate-400 ml-1">/ 100</span>
              </div>
            </div>

            <div className="w-full pt-3 border-t border-slate-700/60 text-xs text-slate-300 space-y-1">
              <div className="flex justify-between">
                <span>Supported:</span>
                <span className="font-bold text-white">{assessment.supported_requirements} / {assessment.total_requirements}</span>
              </div>
              <div className="flex justify-between">
                <span>Needs Attention:</span>
                <span className="font-bold text-amber-400">{assessment.missing_requirements_count + assessment.needs_review_requirements}</span>
              </div>
            </div>
          </div>
        </div>

        {/* CORE DATA CARDS GRID */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* 1. CARBON ACCOUNTING CARD */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-[#0F6B56]" />
                Carbon Accounting Posture
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 bg-[#EAF7F2] text-[#0F6B56] rounded-md">
                Source of Truth
              </span>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="text-slate-500">Accounted Emissions:</span>
                <span className="font-extrabold text-slate-900 text-sm">
                  {assessment.accounting_summary?.accounted_emissions_tco2e !== null && assessment.accounting_summary?.accounted_emissions_tco2e !== undefined
                    ? `${assessment.accounting_summary.accounted_emissions_tco2e.toFixed(4)} tCO2e`
                    : 'Not Recorded'}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="text-slate-500">POSTED Ledger Entries:</span>
                <span className="font-bold text-slate-800">
                  {assessment.accounting_summary?.posted_ledger_entries_count || 0} entries
                </span>
              </div>
              <p className="text-[11px] text-slate-500 pt-1">
                Derived directly from POSTED CarbonLedgerEntry records. Never recalculated or labeled as carbon credits.
              </p>
            </div>
          </div>

          {/* 2. MEASUREMENT & BASELINE CARD */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-[#0F6B56]" />
                Baseline & Measurement
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md">
                Observed Data
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="text-slate-500">Baseline Period:</span>
                <span className="font-bold text-slate-800">
                  {assessment.baseline_period || 'Not Defined'} ({assessment.baseline_co2e || 0} {assessment.baseline_co2e_unit || 'kgCO2e'})
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="text-slate-500">Observed Reduction:</span>
                <span className="font-bold text-slate-800">
                  {assessment.accounting_summary?.observed_reduction_tco2e !== null && assessment.accounting_summary?.observed_reduction_tco2e !== undefined
                    ? `${assessment.accounting_summary.observed_reduction_tco2e.toFixed(4)} tCO2e`
                    : 'Pending Measurement'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 pt-1">
                Observed change between baseline and measurement periods. Does not assume causality without verification.
              </p>
            </div>
          </div>

          {/* 3. VERIFICATION & STANDARD CARD */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-[#0F6B56]" />
                Verification & Standard
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md">
                Generic Standard
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="text-slate-500">External Verification:</span>
                <span className="font-bold text-slate-800">
                  {assessment.methodology?.verification_pathway_status === 'EXTERNALLY_VERIFIED' ? 'Externally Verified' : 'Not Recorded'}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center">
                <span className="text-slate-500">Registry Standard:</span>
                <span className="font-bold text-slate-800">Generic Carbon Standard</span>
              </div>
              <p className="text-[11px] text-slate-500 pt-1">
                Standard-specific eligibility (e.g. Verra, Gold Standard) requires formal methodology review by an accredited body.
              </p>
            </div>
          </div>

        </div>

        {/* "WHAT IS MISSING?" PRIORITY ALERT SECTION */}
        {assessment.missing_requirements && assessment.missing_requirements.length > 0 && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  What is Missing Before Methodology Review?
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {assessment.missing_requirements.length} priority items require attention before initiating standard certification review.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {assessment.missing_requirements.map((m) => (
                <div key={m.requirement_code} className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2 text-xs flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold text-slate-500">{m.requirement_code}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        m.priority === 'HIGH' ? 'bg-rose-100 text-rose-800' :
                        m.priority === 'MEDIUM' ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'
                      }`}>
                        {m.priority} PRIORITY
                      </span>
                    </div>
                    <h4 className="font-bold text-slate-900 text-sm">{m.requirement_name}</h4>
                    <p className="text-slate-600">{m.reason}</p>
                  </div>

                  <div className="pt-2 border-t border-slate-200/60 text-slate-700 space-y-1">
                    <span className="font-bold text-slate-900 block text-[11px]">Recommended Action:</span>
                    <p className="text-[#0F6B56] font-medium">{m.recommended_action}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* "CERTIFICATION PATHWAY" WORKFLOW STEPS */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FolderKanban className="w-5 h-5 text-[#0F6B56]" />
              Potential Project Certification Pathway
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Visual roadmap distinguishing current readiness preparation from future out-of-scope certification and registry steps.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 pt-2">
            
            <div className="p-3.5 bg-[#EAF7F2] rounded-xl border border-[#0F6B56]/30 text-xs space-y-1.5">
              <div className="flex items-center justify-between text-[#0F6B56] font-bold">
                <span>Step 1</span>
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <h4 className="font-bold text-slate-900">Project Preparation</h4>
              <p className="text-[11px] text-slate-600">In Scope: Project definition, baseline, activity data & posted carbon ledger.</p>
            </div>

            <div className="p-3.5 bg-[#EAF7F2] rounded-xl border border-[#0F6B56]/30 text-xs space-y-1.5">
              <div className="flex items-center justify-between text-[#0F6B56] font-bold">
                <span>Step 2</span>
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <h4 className="font-bold text-slate-900">Methodology Review</h4>
              <p className="text-[11px] text-slate-600">In Scope: Assess data package readiness against generic standard rules.</p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5 opacity-90">
              <div className="flex items-center justify-between text-slate-400 font-bold">
                <span>Step 3</span>
                <Clock className="w-4 h-4" />
              </div>
              <h4 className="font-bold text-slate-800">Project Documentation</h4>
              <p className="text-[11px] text-slate-500">Project design document (PDD) submission to standard program.</p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5 opacity-80">
              <div className="flex items-center justify-between text-slate-400 font-bold">
                <span>Step 4</span>
                <Clock className="w-4 h-4" />
              </div>
              <h4 className="font-bold text-slate-800">Validation / Verification</h4>
              <p className="text-[11px] text-slate-500">Independent audit by accredited third-party validation/verification body (VVB).</p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5 opacity-70">
              <div className="flex items-center justify-between text-slate-400 font-bold">
                <span>Step 5</span>
                <Clock className="w-4 h-4" />
              </div>
              <h4 className="font-bold text-slate-800">Registry Process</h4>
              <p className="text-[11px] text-slate-500">Official registry review and registration under standard rules.</p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-dashed border-slate-300 text-xs space-y-1.5 opacity-60">
              <div className="flex items-center justify-between text-slate-400 font-bold">
                <span>Step 6</span>
                <Sparkles className="w-4 h-4" />
              </div>
              <h4 className="font-bold text-slate-800">Potential Credit Issuance</h4>
              <p className="text-[11px] text-slate-500">Out of Scope: Tradable credit issuance subject to authoritative registry decisions.</p>
            </div>

          </div>
        </div>

        {/* 15 READINESS DIMENSIONS CARDS */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-[#0F6B56]" />
                Readiness Dimensions (15 Categories)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Deterministic weighted completion evaluation across every project readiness dimension.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {assessment.dimensions?.map((dim) => (
              <div key={dim.category} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-sm">{dim.title}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    dim.status === 'SUPPORTED' ? 'bg-[#EAF7F2] text-[#0F6B56]' :
                    dim.status === 'PARTIAL' ? 'bg-amber-100 text-amber-800' :
                    dim.status === 'NEEDS_REVIEW' ? 'bg-blue-100 text-blue-800' : 'bg-rose-100 text-rose-800'
                  }`}>
                    {dim.status}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        dim.score >= 80 ? 'bg-[#0F6B56]' :
                        dim.score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                      }`}
                      style={{ width: `${dim.score}%` }}
                    />
                  </div>
                  <span className="font-bold text-slate-800 text-xs w-10 text-right">{dim.score.toFixed(0)}%</span>
                </div>

                <p className="text-slate-600 text-[11px] leading-relaxed">{dim.explanation}</p>

                <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-200/60">
                  <span>Supported: {dim.supported_count} / {dim.total_count} criteria</span>
                  {dim.source_ref && <span>Source: {dim.source_ref}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CERTIFICATION PATHWAY CHECKLIST TABLE */}
        {assessment.checklist && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-[#0F6B56]" />
              Carbon Credit Project Readiness Checklist
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 font-bold border-y border-slate-200 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3 w-10">#</th>
                    <th className="py-2.5 px-3 w-48">Section</th>
                    <th className="py-2.5 px-3 w-32">Status</th>
                    <th className="py-2.5 px-3">Criteria Evaluated</th>
                    <th className="py-2.5 px-3 w-32">Source Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {assessment.checklist.map((chk) => (
                    <tr key={chk.section_number} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono text-slate-400">{chk.section_number}</td>
                      <td className="py-2.5 px-3 font-bold text-slate-800">{chk.section_name}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          chk.status === 'READY' ? 'bg-[#EAF7F2] text-[#0F6B56]' :
                          chk.status === 'PARTIAL' ? 'bg-amber-100 text-amber-800' :
                          chk.status === 'NEEDS_REVIEW' ? 'bg-blue-100 text-blue-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {chk.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{chk.description}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px]">{chk.evidence_ref || 'Database'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* EVIDENCE PROVENANCE & AUDIT TRAIL */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Clock className="w-5 h-5 text-[#0F6B56]" />
            Immutable Audit Trail & Lifecycle Events
          </h3>

          <div className="divide-y divide-slate-100 text-xs">
            {assessment.events?.map((evt) => (
              <div key={evt.id} className="py-2.5 flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800">{evt.event_type}</span>
                    <span className="text-slate-400 font-mono text-[10px]">{evt.actor}</span>
                  </div>
                  <p className="text-slate-600 text-[11px]">{evt.notes || 'Status transition logged.'}</p>
                </div>
                <span className="text-slate-400 text-[11px] whitespace-nowrap">
                  {new Date(evt.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* STATUS UPDATE MODAL */}
      {statusModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm">Update Workflow Status</h3>
              <button onClick={() => setStatusModal(false)} className="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
            </div>

            <form onSubmit={handleStatusUpdate} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Status</label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
                >
                  <option value="DRAFT">Draft</option>
                  <option value="GENERATED">Generated</option>
                  <option value="NEEDS_REVIEW">Needs Review</option>
                  <option value="READY_FOR_METHODOLOGY_REVIEW">Ready for Methodology Review</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Status Change Note</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Completed initial documentation review."
                  value={statusNote}
                  onChange={(e) => setStatusNote(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setStatusModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updatingStatus}
                  className="px-4 py-1.5 bg-[#0F6B56] text-white text-xs font-semibold rounded-xl"
                >
                  {updatingStatus ? 'Updating...' : 'Save Status'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
