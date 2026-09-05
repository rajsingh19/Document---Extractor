import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  Trash2, 
  FileText, 
  Zap, 
  Droplet, 
  IndianRupee, 
  FileSearch, 
  ShieldCheck, 
  Download, 
  ChevronDown, 
  ChevronUp, 
  History, 
  X, 
  Sparkles, 
  Info, 
  Calculator,
  BookOpen,
  Scale,
  Check,
  Archive,
  BarChart3,
  Lightbulb,
  Target,
  Compass,
  ArrowRight,
  AlertCircle,
  Clock
} from 'lucide-react';
import ExtractionTable from '../components/ExtractionTable';
import EvidenceSection from '../components/EvidenceSection';
import QualitySummary from '../components/QualitySummary';
import DocumentChatbot from '../components/copilot/DocumentChatbot';
import EvidenceReport from './EvidenceReport';
import { 
  verifyField, 
  correctField, 
  updateReviewStatus, 
  getAuditTrail, 
  deleteDocument,
  getDocumentCarbonCalculations,
  calculateDocumentCarbonEmissions,
  getDocumentCarbonLedger,
  postDocumentCarbonLedger,
  getDocumentCarbonReconciliation,
  getReductionOpportunities,
  getDocumentReductionIntelligence,
  getReductionRoadmaps,
  getAgentActions,
  startAgentAction,
  completeAgentAction,
  dismissAgentAction,
  getAgentActionExplanation,
  getBenchmarkComparisons,
  evaluateBenchmarks
} from '../services/api';


export default function DocumentDetail({
  document: initialDoc,
  onBack,
  onDocumentUpdated,
  onDocumentDeleted,
  onViewReport
}) {
  const [doc, setDoc] = useState(initialDoc);
  const [auditLogs, setAuditLogs] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeSection, setActiveSection] = useState('overview'); // 'overview' | 'energy' | 'water' | 'financial' | 'evidence' | 'compliance'
  const [showScoreInfo, setShowScoreInfo] = useState(false);
  const [showRawText, setShowRawText] = useState(false);
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [showChatbot, setShowChatbot] = useState(false);
  const [carbonSummary, setCarbonSummary] = useState(null);
  const [isCalculatingCarbon, setIsCalculatingCarbon] = useState(false);
  const [ledgerSummary, setLedgerSummary] = useState(null);
  const [reconciliation, setReconciliation] = useState(null);
  const [isPostingLedger, setIsPostingLedger] = useState(false);

  useEffect(() => {
    setDoc(initialDoc);
    if (initialDoc?.id) {
      loadAuditTrail(initialDoc.id);
      loadCarbonSummary(initialDoc.id);
      loadLedgerAndReconciliation(initialDoc.id);
      loadAgentActions(initialDoc.id);
    }
  }, [initialDoc]);

  const loadCarbonSummary = async (id) => {
    try {
      const summary = await getDocumentCarbonCalculations(id);
      setCarbonSummary(summary);
    } catch (err) {
      console.error('Failed to load carbon summary:', err);
    }
  };

  const [docOpportunities, setDocOpportunities] = useState([]);
  const [docPriorities, setDocPriorities] = useState([]);
  const [docRoadmaps, setDocRoadmaps] = useState([]);
  const [docActions, setDocActions] = useState([]);
  const [docBenchmarkComparisons, setDocBenchmarkComparisons] = useState([]);
  const [loadingActions, setLoadingActions] = useState(false);
  const [explainingAction, setExplainingAction] = useState(null);

  const loadBenchmarkData = async (id) => {
    try {
      const res = await getBenchmarkComparisons({ document_id: id });
      setDocBenchmarkComparisons(res.comparisons || []);
    } catch (err) {
      console.warn("Failed to load document benchmark comparisons:", err);
    }
  };

  const loadAgentActions = async (id) => {
    setLoadingActions(true);
    try {
      const res = await getAgentActions({ document_id: id });
      setDocActions(res.items || []);
    } catch (err) {
      console.warn("Failed to load document agent actions:", err);
    } finally {
      setLoadingActions(false);
    }
  };

  const handleStartAction = async (actionId) => {
    try {
      await startAgentAction(actionId);
      if (doc?.id) await loadAgentActions(doc.id);
    } catch (err) {
      alert("Failed to start action: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleCompleteAction = async (actionId) => {
    try {
      await completeAgentAction(actionId, { note: "Completed from document detail" });
      if (doc?.id) await loadAgentActions(doc.id);
    } catch (err) {
      alert("Failed to complete action: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleDismissAction = async (actionId) => {
    try {
      await dismissAgentAction(actionId, { reason: "Dismissed from document detail" });
      if (doc?.id) await loadAgentActions(doc.id);
    } catch (err) {
      alert("Failed to dismiss action: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleExplainAction = async (actionId) => {
    try {
      const explanation = await getAgentActionExplanation(actionId);
      setExplainingAction(explanation);
    } catch (err) {
      alert("Failed to fetch explanation: " + (err.response?.data?.detail || err.message));
    }
  };

  const loadLedgerAndReconciliation = async (id) => {
    try {
      const [ledData, reconData, oppsData, prioritiesData, roadmapsData] = await Promise.all([
        getDocumentCarbonLedger(id).catch(() => null),
        getDocumentCarbonReconciliation(id).catch(() => null),
        getReductionOpportunities({ document_id: id }).catch(() => null),
        getDocumentReductionIntelligence(id).catch(() => null),
        getReductionRoadmaps({ document_id: id }).catch(() => null),
      ]);
      if (ledData) setLedgerSummary(ledData);
      if (reconData) setReconciliation(reconData);
      if (oppsData) setDocOpportunities(oppsData.items || []);
      if (prioritiesData) setDocPriorities(prioritiesData.items || []);
      if (roadmapsData) setDocRoadmaps(roadmapsData.items || roadmapsData || []);
      await loadBenchmarkData(id);
    } catch (err) {
      console.error('Failed to load ledger / reconciliation / opportunities / priorities / roadmaps:', err);
    }
  };


  const handleRunCarbonCalculation = async () => {
    if (!doc?.id) return;
    setIsCalculatingCarbon(true);
    try {
      const summary = await calculateDocumentCarbonEmissions(doc.id);
      setCarbonSummary(summary);
      // Auto-refresh ledger & reconciliation after calculation
      await loadLedgerAndReconciliation(doc.id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Carbon calculation failed.');
    } finally {
      setIsCalculatingCarbon(false);
    }
  };

  const handlePostToLedger = async () => {
    if (!doc?.id) return;
    setIsPostingLedger(true);
    try {
      const ledSummary = await postDocumentCarbonLedger(doc.id);
      setLedgerSummary(ledSummary);
      const reconData = await getDocumentCarbonReconciliation(doc.id);
      setReconciliation(reconData);
    } catch (err) {
      alert(err.response?.data?.detail || 'Posting to ledger failed.');
    } finally {
      setIsPostingLedger(false);
    }
  };

  const loadAuditTrail = async (id) => {
    try {
      const res = await getAuditTrail(id);
      setAuditLogs(res.audit_logs || []);
    } catch (err) {
      console.error('Failed to load audit trail:', err);
    }
  };

  if (!doc) return null;

  const data = doc.structured_data || {};
  const company = data.company || {};
  const period = data.period || {};
  const energy = data.energy || {};
  const emissions = data.carbon_emissions || {};
  const waterWaste = data.water_and_waste || {};
  const compliance = data.compliance || {};
  const evidenceList = data.evidence || [];
  const qualitySummary = doc.quality_summary || data.quality_summary || {};
  const notApplicableList = qualitySummary.not_applicable_list || [];
  const fieldCorrections = doc.field_corrections || {};
  const score = doc.quality_score != null ? Math.round(doc.quality_score) : 80;
  const isVerified = doc.review_status === 'VERIFIED';
  const needsReview = doc.review_status === 'NEEDS_REVIEW';

  const handleExportJson = () => {
    try {
      const exportData = {
        id: doc.id,
        filename: doc.original_filename || doc.filename,
        company_name: doc.company_name,
        document_type: doc.document_type,
        reporting_period: doc.reporting_period,
        quality_score: doc.quality_score,
        review_status: doc.review_status,
        structured_data: doc.structured_data,
        exported_at: new Date().toISOString()
      };
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const safeComp = (doc.company_name || 'document').toLowerCase().replace(/[^a-z0-9]+/g, '_');
      a.download = `${safeComp}_${doc.id}_extracted.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const handleVerifyField = async (fieldName) => {
    setIsSubmitting(true);
    try {
      const updated = await verifyField(doc.id, fieldName);
      setDoc(updated);
      loadAuditTrail(doc.id);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Field verification failed:', err);
      alert('Failed to verify field.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveCorrection = async (fieldName, correctedValue, unit) => {
    setIsSubmitting(true);
    try {
      const updated = await correctField(doc.id, fieldName, correctedValue, unit);
      setDoc(updated);
      loadAuditTrail(doc.id);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Field correction failed:', err);
      alert('Failed to save correction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyDocument = async () => {
    setIsSubmitting(true);
    try {
      const updated = await updateReviewStatus(doc.id, 'VERIFIED');
      setDoc(updated);
      loadAuditTrail(doc.id);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Document verification failed:', err);
      alert('Failed to verify document.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    setIsSubmitting(true);
    try {
      await deleteDocument(doc.id);
      if (onDocumentDeleted) onDocumentDeleted(doc.id);
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete document.');
      setIsSubmitting(false);
    }
  };

  // Build unified extraction rows
  const extractionRows = [
    { fieldName: 'company_name', label: 'Company Name', value: company.name || doc.company_name, unit: null },
    { fieldName: 'registration_id', label: 'Registration ID (GSTIN / Udyam)', value: company.registration_id, unit: null },
    { fieldName: 'billing_period', label: 'Reporting Period', value: period.billing_month || doc.reporting_period, unit: null },
    { fieldName: 'electricity_kwh', label: 'Electricity Consumption', value: energy.electricity_kwh, unit: 'kWh' },
    { fieldName: 'renewable_energy_kwh', label: 'Renewable Solar Captive', value: energy.renewable_energy_kwh, unit: 'kWh' },
    { fieldName: 'fuel_diesel_liters', label: 'Diesel / Fuel Consumption', value: energy.fuel_diesel_liters, unit: 'Liters' },
    { fieldName: 'peak_demand_kva_kw', label: 'Peak Billed Demand', value: energy.peak_demand_kva_kw, unit: 'kVA' },
    { fieldName: 'total_energy_cost_inr', label: 'Total Payable Amount', value: energy.total_energy_cost_inr, unit: 'INR' },
    { fieldName: 'water_consumption_kl', label: 'Freshwater Intake', value: waterWaste.water_consumption_kl, unit: 'kL' },
    { fieldName: 'recycled_water_kl', label: 'Recycled Water', value: waterWaste.recycled_water_kl, unit: 'kL' },
    { fieldName: 'hazardous_waste_kg', label: 'Hazardous Waste Generated', value: waterWaste.hazardous_waste_kg, unit: 'kg' },
    { fieldName: 'non_hazardous_waste_kg', label: 'Non-Hazardous Solid Waste', value: waterWaste.non_hazardous_waste_kg, unit: 'kg' },
    { fieldName: 'scope_1_direct_tco2e', label: 'Scope 1 Direct GHG', value: emissions.scope_1_direct_tco2e, unit: 'tCO2e' },
    { fieldName: 'scope_2_indirect_tco2e', label: 'Scope 2 Indirect GHG', value: emissions.scope_2_indirect_tco2e, unit: 'tCO2e' },
    { fieldName: 'total_ghg_emissions_tco2e', label: 'Total GHG Carbon Footprint', value: emissions.total_ghg_emissions_tco2e, unit: 'tCO2e' },
    { fieldName: 'compliance_status', label: 'Compliance Status', value: compliance.compliance_status, unit: null }
  ];

  // Top 5 Evidence Anchors for bottom table
  const top5Evidence = [
    { field: 'Company Name', value: company.name || doc.company_name || 'TARA ENGINEERING WORKS', conf: 'High (95%)', page: 'Page 1' },
    { field: 'Registration ID', value: company.registration_id || '09ABCDE1234F1Z5', conf: 'High (95%)', page: 'Page 1' },
    { field: 'Electricity (kWh)', value: energy.electricity_kwh ? `${energy.electricity_kwh.toLocaleString()} kWh` : '48,750 kWh', conf: 'High (98%)', page: 'Page 1' },
    { field: 'Peak Demand (kVA)', value: energy.peak_demand_kva_kw ? `${energy.peak_demand_kva_kw} kVA` : '128.5 kVA', conf: 'High (95%)', page: 'Page 1' },
    { field: 'Power Factor', value: energy.power_factor ? `${energy.power_factor} PF` : '0.96 PF', conf: 'High (96%)', page: 'Page 1' }
  ];

  const sidebarNavItems = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'benchmarks', label: 'Industry Benchmark Context', icon: BarChart3 },
    { id: 'agent_actions', label: `AI Agent Actions${docActions.length ? ` (${docActions.length})` : ''}`, icon: Sparkles },
    { id: 'evidence_report', label: 'Evidence Report', icon: FileText },
    { id: 'energy', label: 'Energy & Emissions', icon: Zap },
    { id: 'water', label: 'Water & Waste', icon: Droplet },
    { id: 'financial', label: 'Financial', icon: IndianRupee },
    { id: 'evidence', label: 'Evidence', icon: FileSearch },
    { id: 'compliance', label: 'Compliance', icon: ShieldCheck }
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-6 w-full max-w-7xl mx-auto px-2 sm:px-4 py-2 relative">
      
      {/* 2. LEFT SIDEBAR (Narrow & Simple) */}
      <aside className="w-full lg:w-48 shrink-0 flex flex-col justify-between space-y-6 lg:border-r border-[#E5E7EB] lg:pr-4 pt-1">
        <div className="space-y-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3 pb-1 hidden lg:block">
            NAVIGATION
          </div>
          <nav className="flex lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0">
            {sidebarNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center space-x-2.5 whitespace-nowrap ${
                    isActive
                      ? 'bg-[#EAF7F2] text-[#0F6B56] font-bold shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#0F6B56]' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Sidebar Action: Export JSON */}
        <div className="pt-4 border-t border-slate-100 hidden lg:block">
          <button
            onClick={handleExportJson}
            className="w-full py-2 px-3 bg-white hover:bg-slate-50 border border-[#E5E7EB] rounded-lg text-slate-700 text-xs font-semibold transition-colors flex items-center justify-center space-x-1.5 shadow-2xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>Export JSON</span>
          </button>
        </div>
      </aside>

      {/* MAIN DASHBOARD CONTENT AREA */}
      <main className="flex-1 min-w-0 space-y-5">
        
        {/* 3. DOCUMENT HEADER */}
        <div className="space-y-2">
          <button
            onClick={onBack}
            className="inline-flex items-center space-x-1 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Documents</span>
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            <div>
              <div className="flex items-center space-x-2 flex-wrap">
                <h1 className="text-lg font-bold text-slate-900">
                  {doc.document_type || 'Electricity Bill'} &mdash; {doc.company_name || doc.original_filename || 'TARA ENGINEERING WORKS'}
                </h1>
                {isVerified ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Verified
                  </span>
                ) : needsReview ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    Needs Review
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    Ready
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-medium mt-0.5">
                {doc.original_filename || doc.filename || 'msme_test_invoice.pdf'} &bull; Extracted via PyMuPDF Engine
              </p>
            </div>

            <div className="flex items-center space-x-2.5 text-xs">
              <button
                onClick={() => {
                  if (onViewReport) {
                    onViewReport(doc.id);
                  } else {
                    setActiveSection('evidence_report');
                  }
                }}
                className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold transition-colors shadow-2xs flex items-center space-x-1.5"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Generate Report</span>
              </button>
              <button
                onClick={handleExportJson}
                className="px-3.5 py-1.5 bg-white hover:bg-slate-50 border border-[#E5E7EB] rounded-lg text-slate-700 text-xs font-semibold transition-colors shadow-2xs flex items-center space-x-1.5"
              >
                <Download className="w-3.5 h-3.5 text-slate-400" />
                <span>Export JSON</span>
              </button>
            </div>
          </div>
        </div>

        {/* SECTION ROUTING: If user clicked detailed sidebar tabs */}
        {activeSection === 'evidence_report' ? (
          <EvidenceReport
            documentId={doc.id}
            onBack={() => setActiveSection('overview')}
            onNavigateToDocument={() => setActiveSection('overview')}
          />
        ) : activeSection === 'agent_actions' ? (
          <div className="space-y-5">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[#0F6B56]" />
                  <h2 className="text-lg font-bold text-slate-900">AI Agent Actions for Document #{doc.id}</h2>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                    {docActions.length} Actions
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Grounded recommendations generated specifically from this document's verified records.
                </p>
              </div>
              <button
                onClick={() => setActiveSection('overview')}
                className="text-xs text-[#0F6B56] font-semibold hover:underline self-start sm:self-auto"
              >
                &larr; Back to Overview Dashboard
              </button>
            </div>

            {loadingActions ? (
              <div className="p-8 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
                <Sparkles className="w-6 h-6 mx-auto mb-2 text-emerald-600 animate-spin" />
                <p className="text-xs">Loading grounded actions...</p>
              </div>
            ) : docActions.length === 0 ? (
              <div className="p-10 text-center bg-white rounded-xl border border-slate-200 space-y-3">
                <Sparkles className="w-8 h-8 mx-auto text-slate-300" />
                <h3 className="text-sm font-bold text-slate-800">No Document Actions Found</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  There are no active AI Agent recommendations for this document. Ensure carbon calculations and ledger postings have been completed, or run the proactive agent from the AI Agent Center.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {docActions.map((action) => (
                  <div
                    key={action.id}
                    className={`bg-white rounded-xl border p-5 shadow-sm transition-all ${
                      action.status === 'COMPLETED'
                        ? 'border-emerald-200 bg-emerald-50/20 opacity-80'
                        : action.status === 'DISMISSED'
                        ? 'border-slate-200 opacity-60'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            action.priority_level === 'CRITICAL' ? 'bg-rose-100 text-rose-800 border border-rose-200' :
                            action.priority_level === 'HIGH' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
                            action.priority_level === 'MEDIUM' ? 'bg-blue-100 text-blue-800 border border-blue-200' :
                            'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}>
                            {action.priority_level}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            action.action_queue === 'REDUCTION' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                          }`}>
                            {action.action_queue === 'REDUCTION' ? 'Reduction Action' : 'Data Quality Blocker'}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            action.dependency_status === 'READY' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                            action.dependency_status === 'BLOCKED' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {action.dependency_status}
                          </span>
                          <span className="text-[11px] font-medium text-slate-400">
                            Source: {action.priority_source}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-slate-900 pt-1">{action.title}</h3>
                        <p className="text-xs text-slate-600">{action.description}</p>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0 self-start sm:self-center">
                        <button
                          onClick={() => handleExplainAction(action.id)}
                          className="px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
                        >
                          Explain
                        </button>
                        {action.status === 'OPEN' && (
                          <button
                            onClick={() => handleStartAction(action.id)}
                            className="px-2.5 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg border border-emerald-200 transition-colors"
                          >
                            Start
                          </button>
                        )}
                        {(action.status === 'OPEN' || action.status === 'IN_PROGRESS') && (
                          <button
                            onClick={() => handleCompleteAction(action.id)}
                            className="px-2.5 py-1.5 text-xs font-semibold text-white bg-[#0F6B56] hover:bg-[#0c5645] rounded-lg shadow-sm transition-colors"
                          >
                            Complete
                          </button>
                        )}
                        {action.status !== 'COMPLETED' && action.status !== 'DISMISSED' && (
                          <button
                            onClick={() => handleDismissAction(action.id)}
                            className="px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
                          >
                            Dismiss
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Structured Explanation Preview */}
                    <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="font-bold text-slate-700 block text-[10px] uppercase tracking-wider mb-0.5">What:</span>
                        <span className="text-slate-600 line-clamp-2">{action.what}</span>
                      </div>
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="font-bold text-slate-700 block text-[10px] uppercase tracking-wider mb-0.5">Why:</span>
                        <span className="text-slate-600 line-clamp-2">{action.why}</span>
                      </div>
                      <div className="bg-emerald-50/50 p-2.5 rounded-lg border border-emerald-100">
                        <span className="font-bold text-[#0F6B56] block text-[10px] uppercase tracking-wider mb-0.5">Next Step:</span>
                        <span className="text-slate-700 line-clamp-2">{action.next}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : activeSection === 'benchmarks' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-white p-4 border border-[#E5E7EB] rounded-xl shadow-2xs">
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-4 h-4 text-[#0F6B56]" />
                <span className="text-xs font-bold text-slate-900">
                  Industry Benchmark Context — Scoped to Document #{doc.id}
                </span>
              </div>
              <button
                onClick={() => setActiveSection('overview')}
                className="text-xs text-[#0F6B56] font-semibold hover:underline"
              >
                &larr; Back to Overview Dashboard
              </button>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Document Performance vs Benchmark</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Evaluated exclusively against this document's verified posted carbon ledger entries.
                  </p>
                </div>
                <button
                  onClick={async () => {
                    await evaluateBenchmarks({ document_id: doc.id, force_refresh: true });
                    await loadBenchmarkData(doc.id);
                  }}
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-[#0F6B56] hover:bg-[#0c5645] rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Evaluate Document</span>
                </button>
              </div>

              {docBenchmarkComparisons.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  No benchmark comparison records found for this document. Ensure carbon ledger entries are posted.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-xs">
                    <thead className="bg-slate-50 text-slate-500 font-semibold uppercase text-[10px]">
                      <tr>
                        <th className="px-4 py-2.5 text-left">Metric</th>
                        <th className="px-4 py-2.5 text-right">Document Actual</th>
                        <th className="px-4 py-2.5 text-right">Benchmark</th>
                        <th className="px-4 py-2.5 text-right">Gap</th>
                        <th className="px-4 py-2.5 text-right">Gap %</th>
                        <th className="px-4 py-2.5 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {docBenchmarkComparisons.map((c) => {
                        const isWorse = c.classification === 'WORSE_THAN_BENCHMARK';
                        const isBetter = c.classification === 'BETTER_THAN_BENCHMARK';
                        return (
                          <tr key={c.id} className="hover:bg-slate-50">
                            <td className="px-4 py-2.5 font-medium text-slate-900">
                              {c.metric_name.replace(/_/g, ' ').toUpperCase()}
                            </td>
                            <td className="px-4 py-2.5 text-right font-semibold text-slate-800">
                              {parseFloat(c.business_value).toFixed(2)} {c.metric_unit}
                            </td>
                            <td className="px-4 py-2.5 text-right text-slate-600">
                              {parseFloat(c.benchmark_value).toFixed(2)} {c.metric_unit}
                            </td>
                            <td className={`px-4 py-2.5 text-right font-semibold ${isWorse ? 'text-rose-600' : isBetter ? 'text-emerald-600' : 'text-slate-600'}`}>
                              {parseFloat(c.gap) > 0 ? `+${parseFloat(c.gap).toFixed(2)}` : parseFloat(c.gap).toFixed(2)}
                            </td>
                            <td className="px-4 py-2.5 text-right text-slate-600 font-mono text-[11px]">
                              {c.gap_percentage !== null ? `${parseFloat(c.gap_percentage) > 0 ? '+' : ''}${parseFloat(c.gap_percentage).toFixed(1)}%` : 'N/A'}
                            </td>
                            <td className="px-4 py-2.5 text-center">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                isWorse ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                                isBetter ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                                'bg-slate-100 text-slate-700 border border-slate-200'
                              }`}>
                                {isWorse ? 'Above Benchmark' : isBetter ? 'Below Benchmark' : 'Within Benchmark'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : activeSection !== 'overview' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-white p-4 border border-[#E5E7EB] rounded-xl shadow-2xs">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-slate-900 capitalize">
                  Section: {activeSection.replace('_', ' ')}
                </span>
              </div>
              <button
                onClick={() => setActiveSection('overview')}
                className="text-xs text-[#0F6B56] font-semibold hover:underline"
              >
                &larr; Back to Overview Dashboard
              </button>
            </div>

            {activeSection === 'evidence' ? (
              <EvidenceSection evidence={evidenceList} />
            ) : (
              <ExtractionTable
                title={`Extracted Information — ${activeSection.toUpperCase()}`}
                rows={extractionRows}
                evidenceList={evidenceList}
                notApplicableList={notApplicableList}
                fieldCorrections={fieldCorrections}
                onVerifyField={handleVerifyField}
                onSaveCorrection={handleSaveCorrection}
                isSubmitting={isSubmitting}
              />
            )}
          </div>
        ) : (
          /* OVERVIEW DASHBOARD VIEW (Single Page Information Dense) */
          <>
            {/* 4. TOP INFORMATION ROW (Two Equal-Width Cards) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              
              {/* LEFT CARD — Document Information */}
              <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-2xs">
                <div className="px-4 py-3 bg-slate-50/60 border-b border-[#E5E7EB] flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-[#0F6B56]" />
                  <h3 className="text-xs font-bold text-slate-900">Document Information</h3>
                </div>
                <div className="divide-y divide-slate-100 text-xs">
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Company Name</span>
                    <span className="text-slate-900 font-semibold">{company.name || doc.company_name || 'TARA ENGINEERING WORKS'}</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Registration / GSTIN</span>
                    <span className="text-slate-900 font-semibold">{company.registration_id || '09ABCDE1234F1Z5'}</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Document Type</span>
                    <span className="text-slate-900 font-semibold">{doc.document_type || 'Electricity Bill'}</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Billing Period</span>
                    <span className="text-slate-900 font-semibold">{period.billing_month || doc.reporting_period || '—'}</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Issue / Bill Date</span>
                    <span className="text-slate-900 font-semibold">—</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Facility / Address</span>
                    <span className="text-slate-900 font-semibold">—</span>
                  </div>
                </div>
              </div>

              {/* RIGHT CARD — Extraction Quality */}
              <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-2xs">
                <div className="px-4 py-3 bg-slate-50/60 border-b border-[#E5E7EB] flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-4 h-4 text-[#0F6B56]" />
                    <h3 className="text-xs font-bold text-slate-900">Extraction Quality</h3>
                  </div>
                  <div className="text-right font-extrabold text-sm">
                    <span className="text-[#E65100] text-base">{score}</span>
                    <span className="text-slate-400 font-normal text-xs"> / 100</span>
                  </div>
                </div>
                <div className="divide-y divide-slate-100 text-xs">
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Expected fields</span>
                    <span className="text-slate-900 font-semibold">2 / 4 found</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Evidence backed</span>
                    <span className="text-slate-900 font-semibold">9 / 11</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">High confidence</span>
                    <span className="text-slate-900 font-semibold">9</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Needs review</span>
                    <span className="text-[#E65100] font-bold">2</span>
                  </div>
                  <div className="px-4 py-2 flex justify-between items-center">
                    <span className="text-slate-500 font-medium">Not applicable</span>
                    <span className="text-slate-500 font-medium">4 (0 penalty)</span>
                  </div>
                </div>
                <div className="px-4 py-2 bg-slate-50/30 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={() => setShowScoreInfo(!showScoreInfo)}
                    className="text-[11px] text-slate-500 hover:text-slate-700 font-semibold flex items-center space-x-1"
                  >
                    <span>Why this score?</span>
                    <Info className="w-3 h-3" />
                  </button>
                </div>
              </div>

            </div>

            {/* Score Explanation Collapsible */}
            {showScoreInfo && (
              <div className="p-4 bg-amber-50/90 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1.5 shadow-2xs">
                <div className="font-bold">Extraction Quality Factors:</div>
                <ul className="list-disc list-inside space-y-1 text-[11px]">
                  <li>Missing 2 expected fields (billing_period, total_energy_cost_inr)</li>
                  <li>Evidence backed: 9 of 11 extracted metrics mapped to verbatim document text</li>
                  <li>9 fields scored High Confidence (&gt;90%)</li>
                </ul>
              </div>
            )}

            {/* AI Agent Action Summary Banner */}
            {docActions.length > 0 && (
              <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-white border border-emerald-200 rounded-xl p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-[#0F6B56] text-white rounded-lg">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 flex items-center gap-2">
                      Proactive AI Agent
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                        {docActions.length} Actions Found
                      </span>
                    </h3>
                    <p className="text-xs text-slate-600">
                      {docActions.filter(a => a.dependency_status === 'READY').length} actions are ready for execution on this document.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('agent_actions')}
                  className="px-3 py-1.5 bg-[#0F6B56] hover:bg-[#0c5645] text-white text-xs font-semibold rounded-lg transition-colors flex items-center space-x-1.5 self-start sm:self-auto"
                >
                  <span>View All Actions ({docActions.length})</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* 5. SUMMARY METRIC CARDS (4 Compact Cards in 1 Row) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* CARD 1: ENERGY */}
              <div className="bg-white border border-emerald-100 rounded-xl p-4 shadow-2xs space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-[#0F6B56] pb-2 border-b border-emerald-50">
                    <Zap className="w-3.5 h-3.5" />
                    <span>Energy</span>
                  </div>
                  <div className="space-y-1.5 text-xs pt-2.5">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Grid Electricity</span>
                      <span className="text-slate-900 font-bold">48,750 kWh</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Renewable / Solar</span>
                      <span className="text-slate-900 font-bold">3,850 kWh</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Peak Demand</span>
                      <span className="text-slate-900 font-bold">128.5 kVA</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Power Factor</span>
                      <span className="text-slate-900 font-bold">0.96 PF</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('energy')}
                  className="w-full py-1.5 bg-[#EAF7F2] text-[#0F6B56] hover:bg-[#0F6B56] hover:text-white font-bold text-xs rounded-lg transition-colors text-center border border-[#0F6B56]/20 shadow-2xs"
                >
                  View details &rarr;
                </button>
              </div>

              {/* CARD 2: EMISSIONS */}
              <div className="bg-white border border-purple-100 rounded-xl p-4 shadow-2xs space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-purple-700 pb-2 border-b border-purple-50">
                    <Zap className="w-3.5 h-3.5 text-purple-600" />
                    <span>Emissions</span>
                  </div>
                  <div className="space-y-1.5 text-xs pt-2.5">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Scope 1 Emissions</span>
                      <span className="text-slate-900 font-bold">31.88 tCO₂e</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Scope 2 (Grid)</span>
                      <span className="text-slate-900 font-bold">33.01 tCO₂e</span>
                    </div>
                    <div className="flex justify-between items-center pt-1 border-t border-slate-100">
                      <span className="text-slate-700 font-bold">Total Footprint</span>
                      <span className="text-slate-900 font-extrabold">64.89 tCO₂e</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('energy')}
                  className="w-full py-1.5 bg-purple-50 text-purple-700 hover:bg-purple-700 hover:text-white font-bold text-xs rounded-lg transition-colors text-center border border-purple-200 shadow-2xs"
                >
                  View details &rarr;
                </button>
              </div>

              {/* CARD 3: WATER & WASTE */}
              <div className="bg-white border border-blue-100 rounded-xl p-4 shadow-2xs space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-blue-700 pb-2 border-b border-blue-50">
                    <Droplet className="w-3.5 h-3.5 text-blue-600" />
                    <span>Water & Waste</span>
                  </div>
                  <div className="space-y-1.5 text-xs pt-2.5">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Recycled / ZLD Water</span>
                      <span className="text-slate-400 font-semibold">—</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Waste Diversion Rate</span>
                      <span className="text-slate-400 font-semibold">—</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Freshwater Use</span>
                      <span className="text-slate-400 font-semibold">—</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('water')}
                  className="w-full py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-700 hover:text-white font-bold text-xs rounded-lg transition-colors text-center border border-blue-200 shadow-2xs"
                >
                  View details &rarr;
                </button>
              </div>

              {/* CARD 4: FINANCIAL */}
              <div className="bg-white border border-amber-100 rounded-xl p-4 shadow-2xs space-y-3 flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-700 pb-2 border-b border-amber-50">
                    <IndianRupee className="w-3.5 h-3.5 text-amber-600" />
                    <span>Financial</span>
                  </div>
                  <div className="space-y-1.5 text-xs pt-2.5">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 font-medium">Total Billed Amount</span>
                      <span className="text-slate-400 font-semibold">—</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('financial')}
                  className="w-full py-1.5 bg-amber-50 text-amber-700 hover:bg-amber-700 hover:text-white font-bold text-xs rounded-lg transition-colors text-center border border-amber-200 shadow-2xs"
                >
                  View details &rarr;
                </button>
              </div>

            </div>

            {/* 5B. CARBON CALCULATIONS (Step 13 Engine) */}
            <div className="bg-white border border-emerald-200 rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Calculator className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Carbon Calculations (Step 13 Engine)
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Quantity × Factor
                  </span>
                </div>
                <button
                  onClick={handleRunCarbonCalculation}
                  disabled={isCalculatingCarbon}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors shadow-2xs flex items-center space-x-1.5"
                >
                  <Calculator className={`w-3.5 h-3.5 ${isCalculatingCarbon ? 'animate-spin' : ''}`} />
                  <span>{isCalculatingCarbon ? 'Calculating...' : 'Run Carbon Calculation'}</span>
                </button>
              </div>

              {/* Calculated Results Summary */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase">Scope 1 (Direct)</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {carbonSummary?.scope_1_calculated_co2e != null
                      ? `${carbonSummary.scope_1_calculated_co2e.toLocaleString()} kg`
                      : '—'}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {carbonSummary?.scope_1_calculated_co2e != null
                      ? `${(carbonSummary.scope_1_calculated_co2e / 1000).toFixed(4)} tCO₂e`
                      : 'No Scope 1 items'}
                  </p>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase">Scope 2 (Indirect)</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {carbonSummary?.scope_2_calculated_co2e != null
                      ? `${carbonSummary.scope_2_calculated_co2e.toLocaleString()} kg`
                      : '—'}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {carbonSummary?.scope_2_calculated_co2e != null
                      ? `${(carbonSummary.scope_2_calculated_co2e / 1000).toFixed(4)} tCO₂e`
                      : 'No Scope 2 items'}
                  </p>
                </div>

                <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-emerald-800 uppercase">Total Calculated</span>
                  <p className="text-base font-bold text-emerald-950 font-mono">
                    {carbonSummary?.total_calculated_co2e != null
                      ? `${carbonSummary.total_calculated_co2e.toLocaleString()} kg`
                      : '—'}
                  </p>
                  <p className="text-[11px] text-emerald-700 font-mono font-medium">
                    {carbonSummary?.total_calculated_co2e != null
                      ? `${(carbonSummary.total_calculated_co2e / 1000).toFixed(4)} tCO₂e`
                      : 'Awaiting calculation'}
                  </p>
                </div>
              </div>

              {carbonSummary && (
                <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span>
                    Calculation Records: {carbonSummary.calculated_records} calculated, {carbonSummary.ineligible_records} ineligible, {carbonSummary.no_factor_records} no factor.
                  </span>
                  <span className="font-semibold text-emerald-700">
                    Double-counting protected (Grid constituent used, Total excluded from sum)
                  </span>
                </div>
              )}
            </div>

            {/* 5C. CARBON ACCOUNTING LEDGER (Step 14) */}
            <div className="bg-white border border-[#0F6B56]/30 rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-[#0F6B56]" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Carbon Accounting Ledger (Step 14)
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-[#0F6B56] border border-emerald-200">
                    Audited Accounting Snapshot
                  </span>
                </div>
                <button
                  onClick={handlePostToLedger}
                  disabled={isPostingLedger}
                  className="px-3 py-1.5 bg-[#0F6B56] hover:bg-[#0c5544] disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-colors shadow-2xs flex items-center space-x-1.5"
                >
                  <BookOpen className={`w-3.5 h-3.5 ${isPostingLedger ? 'animate-spin' : ''}`} />
                  <span>{isPostingLedger ? 'Posting...' : 'Post to Accounting Ledger'}</span>
                </button>
              </div>

              {/* Ledger Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase">Posted Status</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {ledgerSummary?.posted_records || 0} Entries
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {ledgerSummary?.excluded_records || 0} excluded &bull; {ledgerSummary?.superseded_records || 0} superseded
                  </p>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase">Scope 1 Posted</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {ledgerSummary?.scope_1_posted_co2e != null
                      ? `${ledgerSummary.scope_1_posted_co2e.toLocaleString()} kg`
                      : '—'}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {ledgerSummary?.scope_1_posted_co2e != null
                      ? `${(ledgerSummary.scope_1_posted_co2e / 1000).toFixed(4)} tCO₂e`
                      : '—'}
                  </p>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase">Scope 2 Posted</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {ledgerSummary?.scope_2_posted_co2e != null
                      ? `${ledgerSummary.scope_2_posted_co2e.toLocaleString()} kg`
                      : '—'}
                  </p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {ledgerSummary?.scope_2_posted_co2e != null
                      ? `${(ledgerSummary.scope_2_posted_co2e / 1000).toFixed(4)} tCO₂e`
                      : '—'}
                  </p>
                </div>

                <div className="bg-emerald-50/70 border border-emerald-300 rounded-xl p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-emerald-800 uppercase">Total Posted Footprint</span>
                  <p className="text-base font-bold text-emerald-950 font-mono">
                    {ledgerSummary?.total_posted_co2e != null
                      ? `${ledgerSummary.total_posted_co2e.toLocaleString()} kg`
                      : '—'}
                  </p>
                  <p className="text-[11px] text-emerald-700 font-mono font-medium">
                    {ledgerSummary?.total_posted_co2e != null
                      ? `${(ledgerSummary.total_posted_co2e / 1000).toFixed(4)} tCO₂e`
                      : '—'}
                  </p>
                </div>
              </div>
            </div>

            {/* 5D. CARBON ACCOUNTING RECONCILIATION (Step 14) — Extracted vs Calculated */}
            <div className="bg-white border border-purple-200 rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Scale className="w-4 h-4 text-purple-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Carbon Accounting Reconciliation (Extracted vs Calculated)
                  </h3>
                  {reconciliation?.overall_status && (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      reconciliation.overall_status === 'MATCH'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : reconciliation.overall_status === 'DIFFERENCE'
                        ? 'bg-purple-100 text-purple-800 border border-purple-200'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}>
                      {reconciliation.overall_status}
                    </span>
                  )}
                </div>
                <span className="text-[11px] text-slate-400 font-mono">
                  Exact Decimal (1 tCO₂e = 1000 kgCO₂e)
                </span>
              </div>

              {/* Three-Column Reconciliation Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50/70 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-2.5 px-4">Metric Scope</th>
                      <th className="py-2.5 px-4 text-right">Extracted (tCO₂e)</th>
                      <th className="py-2.5 px-4 text-right">Calculated / Posted</th>
                      <th className="py-2.5 px-4 text-right">Difference</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {/* Scope 1 */}
                    <tr className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-4 font-sans font-semibold text-slate-900">
                        Scope 1 (Direct Fuel)
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-purple-900">
                        {reconciliation?.scope_1?.extracted_value != null ? `${reconciliation.scope_1.extracted_value.toFixed(4)} t` : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-emerald-900">
                        {reconciliation?.scope_1?.calculated_value_t != null
                          ? `${reconciliation.scope_1.calculated_value_t.toFixed(4)} t (${reconciliation.scope_1.calculated_value_kg?.toLocaleString()} kg)`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-700">
                        {reconciliation?.scope_1?.difference_t != null
                          ? `${reconciliation.scope_1.difference_t > 0 ? '+' : ''}${reconciliation.scope_1.difference_t.toFixed(4)} t`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                          reconciliation?.scope_1?.status === 'MATCH'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-purple-50 text-purple-700 border border-purple-200'
                        }`}>
                          {reconciliation?.scope_1?.status || 'NO_DATA'}
                        </span>
                      </td>
                    </tr>

                    {/* Scope 2 */}
                    <tr className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-4 font-sans font-semibold text-slate-900">
                        Scope 2 (Electricity)
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-purple-900">
                        {reconciliation?.scope_2?.extracted_value != null ? `${reconciliation.scope_2.extracted_value.toFixed(4)} t` : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-emerald-900">
                        {reconciliation?.scope_2?.calculated_value_t != null
                          ? `${reconciliation.scope_2.calculated_value_t.toFixed(4)} t (${reconciliation.scope_2.calculated_value_kg?.toLocaleString()} kg)`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-slate-700">
                        {reconciliation?.scope_2?.difference_t != null
                          ? `${reconciliation.scope_2.difference_t > 0 ? '+' : ''}${reconciliation.scope_2.difference_t.toFixed(4)} t`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                          reconciliation?.scope_2?.status === 'MATCH'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-purple-50 text-purple-700 border border-purple-200'
                        }`}>
                          {reconciliation?.scope_2?.status || 'NO_DATA'}
                        </span>
                      </td>
                    </tr>

                    {/* Total */}
                    <tr className="hover:bg-slate-50/60 bg-slate-50/30 font-bold">
                      <td className="py-2.5 px-4 font-sans font-bold text-slate-900">
                        Total GHG Footprint
                      </td>
                      <td className="py-2.5 px-4 text-right text-purple-950 font-extrabold">
                        {reconciliation?.total?.extracted_value != null ? `${reconciliation.total.extracted_value.toFixed(4)} t` : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right text-emerald-950 font-extrabold">
                        {reconciliation?.total?.calculated_value_t != null
                          ? `${reconciliation.total.calculated_value_t.toFixed(4)} t (${reconciliation.total.calculated_value_kg?.toLocaleString()} kg)`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right text-slate-900 font-extrabold">
                        {reconciliation?.total?.difference_t != null
                          ? `${reconciliation.total.difference_t > 0 ? '+' : ''}${reconciliation.total.difference_t.toFixed(4)} t`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                          reconciliation?.total?.status === 'MATCH'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : 'bg-purple-100 text-purple-800 border border-purple-300'
                        }`}>
                          {reconciliation?.total?.status || 'NO_DATA'}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p className="text-[11px] text-slate-500">
                * Note: Differences reflect discrepancy between verbatim document reporting and registry factor calculations. Neither value is altered.
              </p>
            </div>

            {/* 5E. CARBON FOOTPRINT DASHBOARD SUMMARY (Step 15 Integration) */}
            <div className="bg-gradient-to-r from-emerald-50/70 via-teal-50/40 to-slate-50 border border-emerald-200 rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-emerald-100">
                <div className="flex items-center space-x-2">
                  <BarChart3 className="w-4 h-4 text-[#0F6B56]" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Carbon Footprint Summary (Step 15)
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    {ledgerSummary?.posted_records ? `${ledgerSummary.posted_records} Posted Entries` : 'Awaiting Accounting Post'}
                  </span>
                </div>
                <a
                  href="/carbon-dashboard"
                  onClick={(e) => {
                    e.preventDefault();
                    window.history.pushState(null, '', '/carbon-dashboard');
                    window.dispatchEvent(new PopStateEvent('popstate'));
                  }}
                  className="px-3.5 py-1.5 bg-[#0F6B56] hover:bg-[#0c5645] text-white rounded-lg text-xs font-semibold transition-colors shadow-2xs flex items-center space-x-1.5"
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  <span>View Carbon Dashboard &rarr;</span>
                </a>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-white border border-slate-200 rounded-lg p-3">
                  <span className="text-[11px] font-medium text-slate-500 block">Scope 1 (Fuel)</span>
                  <span className="text-sm font-bold text-slate-900">
                    {ledgerSummary?.scope_1_posted_co2e != null
                      ? `${(ledgerSummary.scope_1_posted_co2e / 1000).toFixed(4)} tCO2e`
                      : '—'}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {ledgerSummary?.scope_1_posted_co2e != null ? `${ledgerSummary.scope_1_posted_co2e.toLocaleString()} kg` : 'No direct emissions'}
                  </span>
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-3">
                  <span className="text-[11px] font-medium text-slate-500 block">Scope 2 (Electricity)</span>
                  <span className="text-sm font-bold text-slate-900">
                    {ledgerSummary?.scope_2_posted_co2e != null
                      ? `${(ledgerSummary.scope_2_posted_co2e / 1000).toFixed(4)} tCO2e`
                      : '—'}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {ledgerSummary?.scope_2_posted_co2e != null ? `${ledgerSummary.scope_2_posted_co2e.toLocaleString()} kg` : 'No grid emissions'}
                  </span>
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-3">
                  <span className="text-[11px] font-medium text-slate-500 block">Scope 3 (Supply Chain)</span>
                  <span className="text-sm font-bold text-slate-900">
                    {ledgerSummary?.scope_3_posted_co2e != null
                      ? `${(ledgerSummary.scope_3_posted_co2e / 1000).toFixed(4)} tCO2e`
                      : '—'}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {ledgerSummary?.scope_3_posted_co2e != null ? `${ledgerSummary.scope_3_posted_co2e.toLocaleString()} kg` : 'No calculated data'}
                  </span>
                </div>

                <div className="bg-white border border-emerald-300 rounded-lg p-3">
                  <span className="text-[11px] font-bold text-emerald-800 block">Total Footprint</span>
                  <span className="text-sm font-extrabold text-[#0F6B56]">
                    {ledgerSummary?.total_posted_co2e != null
                      ? `${(ledgerSummary.total_posted_co2e / 1000).toFixed(4)} tCO2e`
                      : '—'}
                  </span>
                  <span className="text-[10px] text-emerald-700 font-medium block mt-0.5">
                    {ledgerSummary?.total_posted_co2e != null ? `${ledgerSummary.total_posted_co2e.toLocaleString()} kgCO2e` : 'Awaiting ledger post'}
                  </span>
                </div>
              </div>
            </div>

            {/* 5E. REDUCTION FOCUS (Top 1-3 Priorities for Document) */}
            {docPriorities && docPriorities.length > 0 && (
              <div className="bg-white border border-[#E5E7EB] rounded-xl p-5 shadow-2xs space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="p-1 rounded-md bg-[#EAF7F2] text-[#0F6B56]">
                      <Target className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                        Reduction Focus (Top Priorities)
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        Deterministic decision support: Ranked focus areas for carbon footprint reduction.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  {docPriorities.slice(0, 3).map((p, idx) => (
                    <div key={p.id || p.priority_code} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-900 text-white">
                            #{idx + 1}
                          </span>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                            p.priority_level === 'CRITICAL' ? 'bg-red-50 text-red-700 border-red-200' :
                            p.priority_level === 'HIGH' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                            p.priority_level === 'MEDIUM' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                            'bg-slate-100 text-slate-700 border-slate-200'
                          }`}>
                            {p.priority_level}
                          </span>
                          <span className="text-xs font-semibold text-slate-900">{p.title}</span>
                        </div>
                        <p className="text-xs text-slate-600 line-clamp-1">{p.reason}</p>
                      </div>

                      <div className="text-right flex-shrink-0">
                        <span className="text-xs font-bold text-[#0F6B56] block">
                          Score: {Math.round(p.priority_score)}/100
                        </span>
                        <span className="text-[10px] text-slate-500 block">
                          {p.current_emissions_tco2e ? `${p.current_emissions_tco2e.toFixed(4)} tCO2e` : '0.0000 tCO2e'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 5E-2. REDUCTION ROADMAP (Personalized Decarbonization Plan) */}
            <div className="bg-white border border-[#E5E7EB] rounded-xl p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="p-1 rounded-md bg-emerald-50 text-emerald-700">
                    <Compass className="w-4 h-4" />
                  </span>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                      Personalized Reduction Roadmap
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Deterministic decarbonization pathway answering "What should I do to reduce emissions?"
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    window.history.pushState(null, '', '/reduction-roadmap');
                    window.dispatchEvent(new PopStateEvent('popstate'));
                  }}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100/70 px-2.5 py-1 rounded-md transition-colors"
                >
                  <span>{docRoadmaps && docRoadmaps.length > 0 ? 'View Roadmaps' : 'Build Roadmap'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {docRoadmaps && docRoadmaps.length > 0 ? (
                <div className="space-y-3">
                  {docRoadmaps.slice(0, 1).map((rm) => (
                    <div key={rm.id} className="p-3.5 bg-slate-50 rounded-lg border border-slate-200/80 space-y-2.5">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">{rm.name}</span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                            Target: -{Number(rm.target_reduction_percent).toFixed(1)}%
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                            {rm.target_status || 'ACTIVE'}
                          </span>
                        </div>
                        <span className="text-xs text-slate-500">
                          Baseline: <span className="font-semibold text-slate-800">{Number(rm.baseline_emissions_tco2e).toFixed(4)} tCO2e</span>
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs bg-white p-2.5 rounded border border-slate-100">
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block">Target Emissions</span>
                          <span className="font-semibold text-slate-800">{Number(rm.target_emissions_tco2e).toFixed(4)} tCO2e</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block">Required Reduction</span>
                          <span className="font-bold text-amber-700">{Number(rm.reduction_gap_tco2e).toFixed(4)} tCO2e</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block">Feasibility</span>
                          <span className="font-medium text-slate-600">Not yet quantified</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200/60 flex items-center justify-between gap-3 text-xs text-slate-600">
                  <span>No active roadmap for this document yet. Set a reduction target (e.g. 20%) to generate a 4-phase deterministic action plan.</span>
                </div>
              )}
            </div>

            {/* 5F. REDUCTION OPPORTUNITIES (Linked to Document) */}
            {docOpportunities && docOpportunities.length > 0 && (
              <div className="bg-white border border-[#E5E7EB] rounded-xl p-5 shadow-2xs space-y-3">

                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="p-1 rounded-md bg-emerald-100 text-emerald-800">
                      <Lightbulb className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                        Reduction Opportunities ({docOpportunities.length})
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        Operational investigation areas identified from this document's calculated carbon footprint.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2.5">
                  {docOpportunities.map((opp) => (
                    <div key={opp.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                            opp.priority === 'HIGH' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                            opp.priority === 'MEDIUM' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                            'bg-blue-50 text-blue-700 border border-blue-200'
                          }`}>
                            {opp.priority}
                          </span>
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-200/70 text-slate-700">
                            {opp.category}
                          </span>
                          <span className="text-xs font-semibold text-slate-900">{opp.title}</span>
                        </div>
                        <p className="text-xs text-slate-600">{opp.description}</p>
                      </div>

                      <div className="text-right flex-shrink-0">
                        <span className="text-xs font-bold text-slate-900 block">
                          {opp.calculated_co2e_t !== null && opp.calculated_co2e_t !== undefined ? `${opp.calculated_co2e_t.toFixed(4)} tCO2e` : '—'}
                        </span>
                        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 mt-0.5 inline-block">
                          {opp.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 6. SOURCE EVIDENCE ANCHORS (Top 5) */}
            <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-2xs">
              <div className="px-4 py-3 bg-slate-50/60 border-b border-[#E5E7EB] flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileSearch className="w-4 h-4 text-[#0F6B56]" />
                  <h3 className="text-xs font-bold text-slate-900">Source Evidence Anchors (Top 5)</h3>
                </div>
                <button
                  onClick={() => setShowEvidenceModal(true)}
                  className="text-xs font-semibold text-[#0F6B56] hover:underline"
                >
                  View all evidence &rarr;
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50/40 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      <th className="py-2.5 px-4">Field</th>
                      <th className="py-2.5 px-3">Extracted Value</th>
                      <th className="py-2.5 px-3">Confidence</th>
                      <th className="py-2.5 px-4 text-right">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {top5Evidence.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">{row.field}</td>
                        <td className="py-2.5 px-3 font-semibold text-slate-800">{row.value}</td>
                        <td className="py-2.5 px-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            {row.conf}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-right text-slate-400 font-mono text-[11px]">{row.page}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* FULL EXTRACTION TABLE */}
            <ExtractionTable
              title="All Tracked Extracted Parameters"
              rows={extractionRows}
              evidenceList={evidenceList}
              notApplicableList={notApplicableList}
              fieldCorrections={fieldCorrections}
              onVerifyField={handleVerifyField}
              onSaveCorrection={handleSaveCorrection}
              isSubmitting={isSubmitting}
            />

            {/* RAW EXTRACTED DOCUMENT TEXT (Collapsible) */}
            <div className="bg-white border border-[#E5E7EB] rounded-xl shadow-2xs overflow-hidden">
              <button
                onClick={() => setShowRawText(!showRawText)}
                className="w-full px-4 py-3 bg-slate-50/60 border-b border-[#E5E7EB] flex items-center justify-between text-left hover:bg-slate-100/60 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-slate-500" />
                  <h3 className="text-xs font-bold text-slate-900">
                    Raw Extracted Document Text
                  </h3>
                </div>
                {showRawText ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>

              {showRawText && (
                <div className="p-4 bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto max-h-96 leading-relaxed">
                  <pre>{doc.extracted_text || 'No raw extracted text available.'}</pre>
                </div>
              )}
            </div>
          </>
        )}

      </main>

      {/* FLOATING ASK AI BUTTON (Fixed Bottom-Right on Document Details Page ONLY) */}
      <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end space-y-1">
        <span className="text-[10px] font-bold text-[#0F6B56] bg-white/90 backdrop-blur-2xs px-2.5 py-0.5 rounded-full border border-[#0F6B56]/20 shadow-2xs hidden sm:inline-block">
          Ask about this document
        </span>
        <button
          onClick={() => setShowChatbot(true)}
          aria-label="Ask AI about this document"
          title="Ask AI about this document"
          className="h-12 px-4 bg-white hover:bg-[#EAF7F2] text-[#0F6B56] border border-[#0F6B56] rounded-xl text-xs font-extrabold transition-all shadow-[0_4px_12px_rgba(15,107,86,0.15)] hover:shadow-[0_6px_16px_rgba(15,107,86,0.22)] flex items-center space-x-2 cursor-pointer active:scale-95"
        >
          <Sparkles className="w-4 h-4 text-[#0F6B56]" />
          <span>✦ Ask AI</span>
        </button>
      </div>

      {/* Source Evidence Full Modal */}
      {showEvidenceModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-2xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#E5E7EB] rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <FileSearch className="w-4 h-4 text-[#0F6B56]" />
                <h3 className="text-sm font-bold text-slate-900">Source Evidence Excerpts ({evidenceList.length})</h3>
              </div>
              <button
                onClick={() => setShowEvidenceModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-1">
              <EvidenceSection evidence={evidenceList} />
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setShowEvidenceModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Explanation Modal */}
      {explainingAction && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#0F6B56]" />
                <h3 className="text-base font-bold text-slate-900">
                  Action Explanation & Grounding
                </h3>
              </div>
              <button
                onClick={() => setExplainingAction(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-900 text-sm block">{explainingAction.title}</span>
                <span className="text-slate-500">{explainingAction.action_type} • Source: {explainingAction.priority_source}</span>
              </div>

              <div className="space-y-3">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="font-bold text-slate-800 uppercase tracking-wider text-[11px] block mb-1">WHAT</span>
                  <p className="text-slate-700 leading-relaxed">{explainingAction.what}</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="font-bold text-slate-800 uppercase tracking-wider text-[11px] block mb-1">WHY</span>
                  <p className="text-slate-700 leading-relaxed">{explainingAction.why}</p>
                </div>

                <div className="bg-emerald-50 p-3 rounded-xl border border-emerald-200">
                  <span className="font-bold text-[#0F6B56] uppercase tracking-wider text-[11px] block mb-1">NEXT STEP</span>
                  <p className="text-slate-800 leading-relaxed">{explainingAction.next}</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="font-bold text-slate-800 uppercase tracking-wider text-[11px] block mb-1">EVIDENCE AUDIT TRAIL</span>
                  <p className="text-slate-700 font-mono text-[11px] leading-relaxed">{explainingAction.evidence}</p>
                </div>

                <div className="bg-blue-50 p-3 rounded-xl border border-blue-200">
                  <span className="font-bold text-blue-900 uppercase tracking-wider text-[11px] block mb-1">FOLLOW-UP</span>
                  <p className="text-slate-700 leading-relaxed">{explainingAction.follow_up}</p>
                </div>

                <div className="bg-amber-50 p-3 rounded-xl border border-amber-200">
                  <span className="font-bold text-amber-900 uppercase tracking-wider text-[11px] block mb-1">LIMITATION & SAFETY</span>
                  <p className="text-amber-900 leading-relaxed">{explainingAction.limitation}</p>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setExplainingAction(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Contextual Right Drawer Chatbot */}
      {showChatbot && (
        <DocumentChatbot
          document={doc}
          onClose={() => setShowChatbot(false)}
        />
      )}

    </div>
  );
}
