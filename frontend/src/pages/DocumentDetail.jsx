import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  Trash2, 
  FileText, 
  ShieldCheck, 
  ChevronDown,
  ChevronUp,
  History,
  Download
} from 'lucide-react';
import ExtractionTable from '../components/ExtractionTable';
import EvidenceSection from '../components/EvidenceSection';
import QualitySummary from '../components/QualitySummary';
import { 
  verifyField, 
  correctField, 
  updateReviewStatus, 
  getAuditTrail, 
  deleteDocument,
  updateDocumentClassification
} from '../services/api';

export default function DocumentDetail({
  document: initialDoc,
  onBack,
  onDocumentUpdated,
  onDocumentDeleted
}) {
  const [doc, setDoc] = useState(initialDoc);
  const [auditLogs, setAuditLogs] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRawText, setShowRawText] = useState(false);
  const [showAuditTrail, setShowAuditTrail] = useState(false);

  useEffect(() => {
    setDoc(initialDoc);
    if (initialDoc?.id) {
      loadAuditTrail(initialDoc.id);
    }
  }, [initialDoc]);

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
  const score = doc.quality_score != null ? Math.round(doc.quality_score) : 0;
  const isVerified = doc.review_status === 'VERIFIED';
  const needsReview = doc.review_status === 'NEEDS_REVIEW';

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

  return (
    <div className="space-y-5 pb-16 w-full max-w-5xl mx-auto">
      
      {/* 1. TOP BREADCRUMB & PRIMARY ACTIONS */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Documents</span>
        </button>

        <div className="flex items-center space-x-2">
          {!isVerified && (
            <button
              onClick={handleVerifyDocument}
              disabled={isSubmitting}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded text-xs font-semibold transition-colors shadow-2xs disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Verify Document</span>
            </button>
          )}

          <button
            onClick={handleDelete}
            disabled={isSubmitting}
            className="p-1.5 rounded border border-slate-200 bg-white hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition-colors"
            title="Delete document"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. DOCUMENT SUMMARY HEADER CARD */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-900">
                {doc.original_filename || doc.filename}
              </h2>
              {isVerified ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  VERIFIED
                </span>
              ) : needsReview ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                  NEEDS REVIEW
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                  READY
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 pt-1">
              <span><b>Type:</b> {doc.document_type || 'Unknown / Other'}</span>
              <span>&bull;</span>
              <span><b>Company:</b> {doc.company_name || 'Not identified'}</span>
              <span>&bull;</span>
              <span><b>Reporting Period:</b> {doc.reporting_period || '—'}</span>
            </div>
          </div>

          <div className="text-left sm:text-right shrink-0">
            <span className="text-xs text-slate-400 block font-normal">Extraction Quality</span>
            <span className="text-xl font-bold text-slate-900">{score}</span>
            <span className="text-xs text-slate-400 font-normal ml-1">/ 100</span>
          </div>
        </div>

        {/* Informative Alerts */}
        {needsReview && !isVerified && (
          <div className="mt-4 p-3 rounded bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                <b>Review Required:</b> Some expected fields are missing or have medium/low confidence. Please review the values below before verifying.
              </span>
            </div>
          </div>
        )}

        {isVerified && (
          <div className="mt-4 p-3 rounded bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <b>Verified by user:</b> All extracted metrics are confirmed and synced to normalized sustainability analytics.
            </span>
          </div>
        )}
      </div>

      {/* 3. MAIN EXTRACTION & QUALITY SECTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        
        {/* Left 2 Cols: Extracted Information & Evidence */}
        <div className="lg:col-span-2 space-y-5">
          <ExtractionTable
            title="Extracted Information"
            rows={extractionRows}
            evidenceList={evidenceList}
            notApplicableList={notApplicableList}
            fieldCorrections={fieldCorrections}
            onVerifyField={handleVerifyField}
            onSaveCorrection={handleSaveCorrection}
            isSubmitting={isSubmitting}
          />

          <EvidenceSection evidence={evidenceList} />
        </div>

        {/* Right 1 Col: Quality Score Checklist & Audit Log */}
        <div className="space-y-5">
          <QualitySummary
            qualityScore={doc.quality_score}
            qualitySummary={qualitySummary}
            documentType={doc.document_type}
          />

          {/* Clean Audit History Card */}
          <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center space-x-1.5">
                <History className="w-4 h-4 text-slate-500" />
                <h3 className="text-sm font-semibold text-slate-900">Audit Trail</h3>
              </div>
              <span className="text-[11px] text-slate-400">
                {auditLogs.length} events
              </span>
            </div>

            {auditLogs.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No audit events recorded yet.</p>
            ) : (
              <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                {auditLogs.map((log) => (
                  <div key={log.id} className="text-xs border-l-2 border-slate-200 pl-2.5 py-0.5 space-y-0.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="font-semibold text-slate-700">{log.action}</span>
                      <span>{log.created_at ? new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent'}</span>
                    </div>
                    {log.details && (
                      <p className="text-slate-600 text-[11px]">
                        {typeof log.details === 'object' ? JSON.stringify(log.details) : log.details}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* 4. RAW DOCUMENT TEXT (COLLAPSIBLE AT BOTTOM) */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-2xs overflow-hidden">
        <button
          onClick={() => setShowRawText(!showRawText)}
          className="w-full px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left hover:bg-slate-100/60 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-slate-500" />
            <h3 className="text-xs font-semibold text-slate-800">
              Raw Extracted Document Text
            </h3>
          </div>
          {showRawText ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
        </button>

        {showRawText && (
          <div className="p-4 bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto max-h-96 leading-relaxed">
            <pre>{doc.extracted_text || 'No raw extracted text available.'}</pre>
          </div>
        )}
      </div>

    </div>
  );
}
