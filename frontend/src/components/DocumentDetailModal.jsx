import React, { useState, useEffect } from 'react';
import { 
  X, 
  Download, 
  Copy, 
  Check, 
  FileText, 
  Building, 
  Calendar, 
  Zap, 
  Flame, 
  Droplets, 
  Recycle, 
  ShieldCheck, 
  ListTree, 
  Code2, 
  AlignLeft, 
  Info,
  CheckCircle2,
  AlertTriangle,
  FileSearch,
  Cpu,
  Edit3,
  CheckSquare,
  History,
  AlertCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  MinusCircle
} from 'lucide-react';
import { verifyField, correctField, updateReviewStatus, getAuditTrail } from '../services/api';

export default function DocumentDetailModal({ document: initialDocument, onClose, onDocumentUpdated }) {
  const [doc, setDoc] = useState(initialDocument);
  const [activeTab, setActiveTab] = useState('overview');
  const [copied, setCopied] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [editingField, setEditingField] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [editUnit, setEditUnit] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false);

  useEffect(() => {
    setDoc(initialDocument);
  }, [initialDocument]);

  useEffect(() => {
    if (doc?.id && activeTab === 'audit') {
      loadAuditTrail();
    }
  }, [doc?.id, activeTab]);

  if (!doc) return null;

  const data = doc.structured_data || {};
  const company = data.company || {};
  const period = data.period || {};
  const energy = data.energy || {};
  const emissions = data.carbon_emissions || {};
  const waterWaste = data.water_and_waste || {};
  const compliance = data.compliance || {};
  const lineItems = data.line_items || [];
  const evidence = data.evidence || [];
  const metadata = data.metadata || {};
  const qualitySummary = doc.quality_summary || data.quality_summary || {};
  const fieldCorrections = doc.field_corrections || {};

  const loadAuditTrail = async () => {
    try {
      const res = await getAuditTrail(doc.id);
      setAuditLogs(res.audit_logs || []);
    } catch (err) {
      console.error('Failed to load audit trail:', err);
    }
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleVerifyField = async (fieldName) => {
    setIsSubmitting(true);
    try {
      const updated = await verifyField(doc.id, fieldName);
      setDoc(updated);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Verification failed:', err);
      alert('Failed to verify field');
    } finally {
      setIsSubmitting(false);
    }
  };

  const startEditing = (fieldName, currentValue, currentUnit = '') => {
    setEditingField(fieldName);
    setEditValue(currentValue != null ? String(currentValue) : '');
    setEditUnit(currentUnit || '');
  };

  const handleSaveCorrection = async (fieldName) => {
    setIsSubmitting(true);
    try {
      let finalVal = editValue.trim();
      if (!isNaN(finalVal) && finalVal !== '') {
        finalVal = parseFloat(finalVal);
      }
      const updated = await correctField(doc.id, fieldName, finalVal, editUnit.trim() || null);
      setDoc(updated);
      setEditingField(null);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Correction failed:', err);
      alert('Failed to save field correction');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateReviewStatus = async (newStatus) => {
    setIsSubmitting(true);
    try {
      const updated = await updateReviewStatus(doc.id, newStatus);
      setDoc(updated);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Status update failed:', err);
      alert('Failed to update review status');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper to find evidence entry for a field
  const getEvidenceForField = (fieldName) => {
    return evidence.find((e) => e.field === fieldName) || null;
  };

  const notApplicableList = qualitySummary.not_applicable_list || [];
  const expectedMissingList = qualitySummary.expected_missing_list || qualitySummary.missing_fields || [];
  const scoringBreakdown = qualitySummary.scoring_breakdown || {};

  const renderConfidenceBadge = (ev, fieldVal, fieldName) => {
    if (!ev && (fieldVal == null || fieldVal === '')) {
      const isNA = notApplicableList.includes(fieldName);
      if (isNA) {
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800/80 text-slate-400 border border-slate-700/60 flex items-center gap-1">
            <MinusCircle className="w-3 h-3 text-slate-500" />
            Not Applicable
          </span>
        );
      }
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-700/60 flex items-center gap-1">
          <AlertCircle className="w-3 h-3 text-amber-400" />
          Missing (Needs Review)
        </span>
      );
    }

    const level = ev?.confidence_level || (ev?.confidence >= 0.9 ? 'HIGH' : ev?.confidence >= 0.7 ? 'MEDIUM' : 'LOW');
    const scorePct = ev?.confidence ? Math.round(ev.confidence * 100) : 90;

    if (level === 'HIGH') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          HIGH ({scorePct}%)
        </span>
      );
    }
    if (level === 'MEDIUM') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-700/60 flex items-center gap-1">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          MEDIUM ({scorePct}%)
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950/80 text-rose-300 border border-rose-700/60 flex items-center gap-1">
        <AlertTriangle className="w-3 h-3 text-rose-400" />
        LOW ({scorePct}%)
      </span>
    );
  };

  const renderFieldVerificationCard = (fieldName, label, currentValue, currentUnit, icon = null) => {
    const ev = getEvidenceForField(fieldName);
    const correction = fieldCorrections[fieldName];
    const isEditing = editingField === fieldName;
    const isNA = (!currentValue && currentValue !== 0) && notApplicableList.includes(fieldName);

    return (
      <div key={fieldName} className="glass-card p-3.5 rounded-xl border border-slate-800 space-y-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            {icon}
            <span className="text-xs font-bold text-slate-200">{label}</span>
          </div>
          <div className="flex items-center space-x-2">
            {correction && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950/80 text-purple-300 border border-purple-700/60">
                Human Corrected
              </span>
            )}
            {ev?.is_verified && !correction && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-700/60">
                Verified
              </span>
            )}
            {renderConfidenceBadge(ev, currentValue, fieldName)}
          </div>
        </div>

        {/* Value Display or Inline Edit Form */}
        {isEditing ? (
          <div className="p-3 rounded-lg bg-slate-950 border border-emerald-500/50 space-y-2">
            <div className="grid grid-cols-3 gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder="Enter corrected value"
                className="col-span-2 px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-400"
              />
              <input
                type="text"
                value={editUnit}
                onChange={(e) => setEditUnit(e.target.value)}
                placeholder="Unit (e.g. kWh)"
                className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-400"
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setEditingField(null)}
                className="px-2.5 py-1 rounded bg-slate-800 text-slate-400 text-xs hover:bg-slate-750"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSaveCorrection(fieldName)}
                disabled={isSubmitting}
                className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors"
              >
                Save Correction
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between bg-slate-900/70 p-2.5 rounded-lg border border-slate-800">
            <div>
              {currentValue != null && currentValue !== '' ? (
                <div className="text-sm font-bold text-white flex items-center gap-1.5">
                  <span>{typeof currentValue === 'number' ? currentValue.toLocaleString() : currentValue}</span>
                  {currentUnit && <span className="text-xs text-emerald-400 font-medium">{currentUnit}</span>}
                </div>
              ) : isNA ? (
                <span className="text-xs text-slate-500 italic">Not applicable for this document type</span>
              ) : (
                <span className="text-xs text-amber-400/90 font-medium italic">Missing expected field (Needs review)</span>
              )}
              {correction && (
                <p className="text-[10px] text-slate-400 mt-0.5">
                  Original AI value: <span className="line-through text-slate-500">{String(correction.original_ai_value ?? 'null')}</span>
                </p>
              )}
            </div>

            <div className="flex items-center space-x-1.5">
              {!ev?.is_verified && currentValue != null && (
                <button
                  onClick={() => handleVerifyField(fieldName)}
                  disabled={isSubmitting}
                  className="flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-400 border border-emerald-800 text-[11px] font-semibold transition-colors"
                >
                  <CheckSquare className="w-3 h-3" />
                  <span>Verify</span>
                </button>
              )}
              <button
                onClick={() => startEditing(fieldName, currentValue, currentUnit)}
                disabled={isSubmitting}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 text-[11px] font-semibold transition-colors"
              >
                <Edit3 className="w-3 h-3 text-amber-400" />
                <span>Edit</span>
              </button>
            </div>
          </div>
        )}

        {/* Source Text Evidence Anchor */}
        {ev?.source_text && (
          <div className="p-2 rounded bg-slate-950/80 border border-slate-800/80 text-[11px] font-mono text-slate-300 flex items-start gap-1.5">
            <span className="text-emerald-400 font-bold shrink-0">&gt;</span>
            <span className="truncate" title={ev.source_text}>"{ev.source_text}"</span>
          </div>
        )}
      </div>
    );
  };

  const reviewStatus = doc.review_status || 'NEEDS_REVIEW';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        
        {/* Modal Top Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold text-white tracking-tight">
                  {doc.original_filename}
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {data.document_type || doc.document_type || 'Sustainability Record'}
                </span>
                
                {/* PROMINENT REVIEW STATUS BADGE */}
                {reviewStatus === 'VERIFIED' && (
                  <span className="text-xs font-bold px-3 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-700 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                    Human Verified
                  </span>
                )}
                {reviewStatus === 'NEEDS_REVIEW' && (
                  <span className="text-xs font-bold px-3 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-700 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    Needs Human Review
                  </span>
                )}
                {reviewStatus === 'COMPLETED' && (
                  <span className="text-xs font-bold px-3 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    AI Extracted
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {company.name || doc.company_name || 'MSME Enterprise'} • Extracted via{' '}
                <span className="text-slate-300 font-medium">
                  {doc.extraction_method === 'ocr_fallback' ? 'Tesseract OCR Fallback' : 'PyMuPDF Text Engine'}
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {reviewStatus !== 'VERIFIED' && (
              <button
                onClick={() => handleUpdateReviewStatus('VERIFIED')}
                disabled={isSubmitting}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-cyan-600/20"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Mark as Fully Verified</span>
              </button>
            )}
            {doc.structured_data && (
              <a
                href={`/api/documents/${doc.id}/download-json`}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-400 hover:text-white border border-slate-700 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* EXTRACTION QUALITY SUMMARY HEADER BAR */}
        <div className="px-6 py-3 bg-slate-950/90 border-b border-slate-800 flex flex-col gap-3">
          <div className="flex items-center justify-between text-xs gap-4 flex-wrap">
            <div className="flex items-center space-x-4 flex-wrap gap-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 font-medium">Extraction Quality:</span>
                <span className={`px-2.5 py-0.5 rounded-lg border font-bold text-sm ${
                  (doc.quality_score ?? qualitySummary.quality_score ?? 85) >= 85
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                    : (doc.quality_score ?? qualitySummary.quality_score ?? 85) >= 70
                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                    : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                }`}>
                  {doc.quality_score ?? qualitySummary.quality_score ?? 85} / 100
                </span>
              </div>
              <div className="h-4 w-px bg-slate-800 hidden sm:block" />
              <div className="flex items-center space-x-3 text-slate-300 flex-wrap gap-y-1">
                <span>Expected fields: <strong className="text-emerald-400">{qualitySummary.expected_fields_found ?? qualitySummary.total_expected_fields ?? 4} / {qualitySummary.total_expected_fields ?? 4} found</strong></span>
                <span>Evidence backed: <strong className="text-emerald-400">{qualitySummary.evidence_backed ?? evidence.length} / {qualitySummary.expected_fields_found ?? evidence.length}</strong></span>
                <span>High confidence: <strong className="text-emerald-400">{qualitySummary.high_confidence ?? 0}</strong></span>
                {(qualitySummary.medium_confidence || 0) > 0 && (
                  <span>Medium: <strong className="text-amber-400">{qualitySummary.medium_confidence}</strong></span>
                )}
                {(qualitySummary.low_confidence || 0) > 0 && (
                  <span>Low: <strong className="text-rose-400">{qualitySummary.low_confidence}</strong></span>
                )}
                <span>Needs review: <strong className={(qualitySummary.expected_fields_missing || 0) > 0 ? "text-amber-400" : "text-slate-400"}>{qualitySummary.expected_fields_missing ?? 0}</strong></span>
                {(qualitySummary.not_applicable_fields || 0) > 0 && (
                  <span>N/A: <strong className="text-slate-400">{qualitySummary.not_applicable_fields}</strong></span>
                )}
                <span>Human verified: <strong className="text-cyan-400">{qualitySummary.human_verified ?? 0}</strong></span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowScoreBreakdown(!showScoreBreakdown)}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
              >
                <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
                <span>Why this score?</span>
                {showScoreBreakdown ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Expandable Deterministic Scoring Breakdown */}
          {showScoreBreakdown && (
            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-700/80 text-xs space-y-2.5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-bold text-slate-200 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  Deterministic Quality Scoring Breakdown
                </span>
                <span className="text-slate-400 text-[11px]">
                  Formula: Base (100) - Penalties = Final Score ({doc.quality_score ?? qualitySummary.quality_score ?? 85}/100)
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Base Score</span>
                  <span className="font-bold text-emerald-400 text-sm">+{scoringBreakdown.base_score || 100}</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">OCR Fallback Penalty</span>
                  <span className={`font-bold text-sm ${(scoringBreakdown.ocr_penalty || 0) > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                    {(scoringBreakdown.ocr_penalty || 0) > 0 ? `-${scoringBreakdown.ocr_penalty}` : '0 (Digital PDF)'}
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Missing Expected Fields</span>
                  <span className={`font-bold text-sm ${(scoringBreakdown.expected_missing_penalty || 0) > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                    {(scoringBreakdown.expected_missing_penalty || 0) > 0 
                      ? `-${scoringBreakdown.expected_missing_penalty} (${qualitySummary.expected_fields_missing || 0} missing)` 
                      : '0 (Complete)'}
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Confidence & Evidence Penalties</span>
                  <span className={`font-bold text-sm ${(scoringBreakdown.low_confidence_penalty || 0) + (scoringBreakdown.medium_confidence_penalty || 0) + (scoringBreakdown.evidence_penalty || 0) > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                    {(scoringBreakdown.low_confidence_penalty || 0) + (scoringBreakdown.medium_confidence_penalty || 0) + (scoringBreakdown.evidence_penalty || 0) > 0
                      ? `-${(scoringBreakdown.low_confidence_penalty || 0) + (scoringBreakdown.medium_confidence_penalty || 0) + (scoringBreakdown.evidence_penalty || 0)}`
                      : '0 (High Confidence)'}
                  </span>
                </div>
              </div>
              {expectedMissingList.length > 0 && (
                <div className="p-2 rounded bg-amber-950/40 border border-amber-800/50 text-amber-200 text-[11px] flex items-start gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-amber-300">Missing Expected Fields for {data.document_type || doc.document_type || 'this document'}:</span>{' '}
                    <span className="font-mono text-amber-200">{expectedMissingList.join(', ')}</span> (-10 pts each)
                  </div>
                </div>
              )}
              {notApplicableList.length > 0 && (
                <div className="p-2 rounded bg-slate-950 border border-slate-800 text-slate-400 text-[11px] flex items-start gap-1.5">
                  <MinusCircle className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-300">Not Applicable (0 penalty):</span>{' '}
                    <span className="font-mono text-slate-400">{notApplicableList.join(', ')}</span> (Outside document scope)
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <div className="px-6 border-b border-slate-800 bg-slate-900/50 flex space-x-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'overview'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ListTree className="w-4 h-4" />
            Field Verification & KPIs
          </button>

          <button
            onClick={() => setActiveTab('evidence')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'evidence'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileSearch className="w-4 h-4" />
            Source Evidence ({evidence.length})
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'audit'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <History className="w-4 h-4" />
            Audit Trail
          </button>

          <button
            onClick={() => setActiveTab('json')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'json'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code2 className="w-4 h-4" />
            Structured JSON
          </button>

          <button
            onClick={() => setActiveTab('raw_text')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'raw_text'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlignLeft className="w-4 h-4" />
            Raw Extracted Text
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {/* TAB 1: FIELD VERIFICATION & KPIS */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              
              {/* Executive Summary */}
              {data.executive_summary && (
                <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-200 text-xs leading-relaxed">
                  <p className="font-semibold text-emerald-400 uppercase tracking-wider text-[10px] mb-1">
                    Executive Summary (Non-Hallucinated Extraction)
                  </p>
                  <p>{data.executive_summary}</p>
                </div>
              )}

              {/* SECTION: COMPANY & PERIOD VERIFICATION */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Building className="w-4 h-4 text-emerald-400" />
                  Company & Period Verification
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {renderFieldVerificationCard('company_name', 'Company Name', company.name || doc.company_name, '')}
                  {renderFieldVerificationCard('registration_id', 'GSTIN / Udyam ID', company.registration_id, '')}
                  {renderFieldVerificationCard('billing_period', 'Billing Period', period.billing_month || doc.reporting_period, '')}
                  {renderFieldVerificationCard('issue_date', 'Issue Date', period.issue_date, '')}
                </div>
              </div>

              {/* SECTION: ENERGY & FUEL METRICS VERIFICATION */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Energy & Fuel Metrics
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {renderFieldVerificationCard('electricity_kwh', 'Electricity Consumption', energy.electricity_kwh, 'kWh', <Zap className="w-3.5 h-3.5 text-amber-400" />)}
                  {renderFieldVerificationCard('peak_demand_kva_kw', 'Recorded Peak Demand', energy.peak_demand_kva_kw, 'kVA', <Zap className="w-3.5 h-3.5 text-amber-400" />)}
                  {renderFieldVerificationCard('power_factor', 'Average Power Factor', energy.power_factor, 'PF', <Zap className="w-3.5 h-3.5 text-amber-400" />)}
                  {renderFieldVerificationCard('fuel_diesel_liters', 'Diesel Fuel Usage', energy.fuel_diesel_liters, 'Liters', <Flame className="w-3.5 h-3.5 text-orange-400" />)}
                  {renderFieldVerificationCard('total_energy_cost_inr', 'Total Billed Amount', energy.total_energy_cost_inr, 'INR')}
                  {renderFieldVerificationCard('renewable_energy_kwh', 'Renewable Solar Energy', energy.renewable_energy_kwh, 'kWh')}
                </div>
              </div>

              {/* SECTION: GHG CARBON EMISSIONS */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Flame className="w-4 h-4 text-emerald-400" />
                  GHG Carbon Emissions
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {renderFieldVerificationCard('scope_1_direct_tco2e', 'Scope 1 Direct Emissions', emissions.scope_1_direct_tco2e, 'tCO2e')}
                  {renderFieldVerificationCard('scope_2_indirect_tco2e', 'Scope 2 Grid Electricity Emissions', emissions.scope_2_indirect_tco2e, 'tCO2e')}
                  {renderFieldVerificationCard('total_ghg_emissions_tco2e', 'Total GHG Operational Footprint', emissions.total_ghg_emissions_tco2e, 'tCO2e')}
                </div>
              </div>

              {/* SECTION: WATER, WASTE & COMPLIANCE */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Droplets className="w-4 h-4 text-cyan-400" />
                  Water, Waste & Compliance
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {renderFieldVerificationCard('water_consumption_kl', 'Freshwater Consumption', waterWaste.water_consumption_kl, 'kL', <Droplets className="w-3.5 h-3.5 text-cyan-400" />)}
                  {renderFieldVerificationCard('non_hazardous_waste_kg', 'Non-Hazardous Waste', waterWaste.non_hazardous_waste_kg, 'kg', <Recycle className="w-3.5 h-3.5 text-emerald-400" />)}
                  {renderFieldVerificationCard('hazardous_waste_kg', 'Hazardous Waste', waterWaste.hazardous_waste_kg, 'kg', <Recycle className="w-3.5 h-3.5 text-amber-400" />)}
                  {renderFieldVerificationCard('compliance_status', 'Compliance Status', compliance.compliance_status || doc.compliance_status, '', <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />)}
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: SOURCE EVIDENCE */}
          {activeTab === 'evidence' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <FileSearch className="w-4 h-4 text-emerald-400" />
                    Preserved Source Evidence Snippets
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Verifiable raw text lines from the document corresponding to each key extracted metric.
                  </p>
                </div>
                <span className="text-xs font-mono bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700 text-slate-300">
                  {evidence.length} Evidence Anchors
                </span>
              </div>

              {evidence.length === 0 ? (
                <div className="p-8 text-center glass-card rounded-xl text-slate-400 text-xs">
                  No source evidence anchors recorded for this document.
                </div>
              ) : (
                <div className="space-y-3">
                  {evidence.map((item, idx) => (
                    <div key={idx} className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-slate-700 text-[11px] font-mono font-semibold">
                            {item.field}
                          </span>
                          <span className="text-xs font-bold text-white">
                            {item.human_corrected_value != null 
                              ? `${item.human_corrected_value} ${item.unit || ''} (Corrected)`
                              : `${item.value != null ? item.value.toLocaleString() : '-'} ${item.unit || ''}`}
                          </span>
                        </div>
                        {renderConfidenceBadge(item, item.value)}
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-slate-300 font-mono text-xs leading-relaxed">
                        <span className="text-emerald-500 font-bold mr-2">&gt;</span>
                        "{item.source_text}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: AUDIT TRAIL */}
          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <History className="w-4 h-4 text-emerald-400" />
                    Human Review & Verification Audit Trail
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Immutable history of field corrections, manual verifications, and status changes.
                  </p>
                </div>
              </div>

              {auditLogs.length === 0 ? (
                <div className="p-8 text-center glass-card rounded-xl text-slate-400 text-xs">
                  No human corrections or status changes recorded yet. Click <b>Edit</b> on any field to record a correction.
                </div>
              ) : (
                <div className="space-y-3">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="glass-card p-4 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200 flex items-center gap-1.5">
                          <Edit3 className="w-3.5 h-3.5 text-amber-400" />
                          Field: <span className="text-emerald-400 font-mono">{log.field_name}</span>
                        </span>
                        <span className="text-[11px] text-slate-500">
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-slate-300 pt-1">
                        <div className="bg-slate-950 p-2 rounded border border-slate-800">
                          <span className="text-[10px] text-slate-500 uppercase block">Original AI Value</span>
                          <span className="font-mono text-slate-400">{String(log.original_ai_value ?? 'null')}</span>
                        </div>
                        <div className="bg-slate-950 p-2 rounded border border-emerald-800/60">
                          <span className="text-[10px] text-emerald-400 uppercase block font-semibold">Human Corrected</span>
                          <span className="font-mono text-emerald-300 font-bold">{String(log.corrected_value ?? 'null')}</span>
                        </div>
                      </div>
                      {log.notes && (
                        <p className="text-[11px] text-slate-400 italic pt-1">{log.notes}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: STRUCTURED JSON */}
          {activeTab === 'json' && (
            <div className="relative">
              <button
                onClick={handleCopyJson}
                className="absolute top-3 right-3 flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
              </button>
              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 font-mono text-xs overflow-x-auto leading-relaxed max-h-[550px]">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          )}

          {/* TAB 5: RAW EXTRACTED TEXT */}
          {activeTab === 'raw_text' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Original extracted document text via <b>{doc.extraction_method}</b></span>
                <span>{doc.extracted_text ? doc.extracted_text.length : 0} characters</span>
              </div>
              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-[550px] overflow-y-auto">
                {doc.extracted_text || 'No text extracted.'}
              </pre>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
