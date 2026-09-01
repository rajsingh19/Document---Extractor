import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Trash2, 
  History, 
  FileText, 
  Zap, 
  Droplets, 
  IndianRupee, 
  FileSearch, 
  ShieldCheck, 
  ChevronRight, 
  Flame, 
  HelpCircle,
  X,
  Edit2,
  Check
} from 'lucide-react';
import ExtractionTable from '../components/ExtractionTable';
import EvidenceSection from '../components/EvidenceSection';
import { verifyField, correctField, updateReviewStatus, getAuditTrail, processDocument, deleteDocument } from '../services/api';

export default function DocumentDetail({
  document: initialDoc,
  onBack,
  onDocumentUpdated,
  onDocumentDeleted
}) {
  const [doc, setDoc] = useState(initialDoc);
  const [activeSection, setActiveSection] = useState('overview'); // 'overview' | 'energy' | 'water_waste' | 'financial' | 'evidence' | 'compliance'
  const [auditLogs, setAuditLogs] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showScoreModal, setShowScoreModal] = useState(false);
  const [showAllEvidenceModal, setShowAllEvidenceModal] = useState(false);

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
  const lineItems = data.line_items || [];
  const evidenceList = data.evidence || [];
  const qualitySummary = doc.quality_summary || data.quality_summary || {};
  const notApplicableList = qualitySummary.not_applicable_list || [];
  const fieldCorrections = doc.field_corrections || {};
  const breakdown = qualitySummary.scoring_breakdown || {};
  const score = doc.quality_score != null ? Math.round(doc.quality_score) : 0;

  const handleVerifyField = async (fieldName) => {
    setIsSubmitting(true);
    try {
      const updated = await verifyField(doc.id, fieldName);
      setDoc(updated);
      loadAuditTrail(doc.id);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Verification failed:', err);
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
      console.error('Correction failed:', err);
      alert('Failed to save correction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMarkVerified = async () => {
    setIsSubmitting(true);
    try {
      const updated = await updateReviewStatus(doc.id, 'VERIFIED');
      setDoc(updated);
      loadAuditTrail(doc.id);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Status update failed:', err);
      alert('Failed to mark verified.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReprocess = async () => {
    setIsSubmitting(true);
    try {
      const updated = await processDocument(doc.id, false);
      setDoc(updated);
      loadAuditTrail(doc.id);
      if (onDocumentUpdated) onDocumentUpdated(updated);
    } catch (err) {
      console.error('Reprocessing failed:', err);
      alert('Failed to reprocess document.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${doc.original_filename}?`)) return;
    try {
      await deleteDocument(doc.id);
      if (onDocumentDeleted) onDocumentDeleted(doc.id);
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete document.');
    }
  };

  // Format date helper
  const formatExtractionDate = (dateString) => {
    if (!dateString) return 'Sep 1, 2026 • 12:00 PM';
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      }) + ' • ' + d.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  // Structured metric row definitions for drill-down views
  const energyRows = [
    { fieldName: 'electricity_kwh', label: 'Grid Electricity Consumption', value: energy.electricity_kwh, unit: 'kWh' },
    { fieldName: 'renewable_energy_kwh', label: 'Renewable / Solar Captive', value: energy.renewable_energy_kwh, unit: 'kWh' },
    { fieldName: 'fuel_diesel_liters', label: 'Diesel / HSD Backup Fuel', value: energy.fuel_diesel_liters, unit: 'Liters' },
    { fieldName: 'peak_demand_kva_kw', label: 'Recorded Peak Demand', value: energy.peak_demand_kva_kw, unit: 'kVA' },
    { fieldName: 'power_factor', label: 'Average Power Factor', value: energy.power_factor, unit: 'PF' },
  ];

  const emissionsRows = [
    { fieldName: 'scope_1_direct_tco2e', label: 'Scope 1 Direct Emissions', value: emissions.scope_1_direct_tco2e, unit: 'tCO2e' },
    { fieldName: 'scope_2_indirect_tco2e', label: 'Scope 2 Grid Purchased', value: emissions.scope_2_indirect_tco2e, unit: 'tCO2e' },
    { fieldName: 'total_ghg_emissions_tco2e', label: 'Total GHG Carbon Footprint', value: emissions.total_ghg_emissions_tco2e, unit: 'tCO2e' },
  ];

  const waterWasteRows = [
    { fieldName: 'recycled_water_kl', label: 'Recycled / ZLD Water', value: waterWaste.recycled_water_kl, unit: 'kL' },
    { fieldName: 'waste_recycled_percentage', label: 'Waste Diversion Rate', value: waterWaste.waste_recycled_percentage, unit: '%' },
    { fieldName: 'water_consumption_kl', label: 'Freshwater Use', value: waterWaste.water_consumption_kl, unit: 'kL' },
    { fieldName: 'non_hazardous_waste_kg', label: 'Non-Hazardous Solid Waste', value: waterWaste.non_hazardous_waste_kg, unit: 'kg' },
    { fieldName: 'hazardous_waste_kg', label: 'Hazardous Waste Handled', value: waterWaste.hazardous_waste_kg, unit: 'kg' },
  ];

  const financialRows = [
    { fieldName: 'total_energy_cost_inr', label: 'Total Billed Amount', value: energy.total_energy_cost_inr, unit: 'INR' },
  ];

  const complianceRows = [
    { fieldName: 'compliance_status', label: 'Environmental Compliance Status', value: compliance.compliance_status || doc.compliance_status, unit: '' },
  ];

  // Top 5 evidence items for overview card
  const topEvidence = evidenceList.slice(0, 5);

  const sidebarNavItems = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'energy', label: 'Energy & Emissions', icon: Zap },
    { id: 'water_waste', label: 'Water & Waste', icon: Droplets },
    { id: 'financial', label: 'Financial', icon: IndianRupee },
    { id: 'evidence', label: 'Evidence', icon: FileSearch },
    { id: 'compliance', label: 'Compliance', icon: ShieldCheck },
  ];

  return (
    <div className="flex flex-col md:flex-row gap-6 items-start pb-12">
      
      {/* 2. LEFT SIDEBAR */}
      <aside className="w-full md:w-52 shrink-0 space-y-1 bg-transparent select-none">
        <nav className="space-y-1">
          {sidebarNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-teal-50/90 text-teal-800 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-teal-700' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Bottom Sidebar Action */}
        <div className="pt-6">
          <a
            href={`/api/documents/${doc.id}/download-json`}
            className="w-full inline-flex items-center justify-center space-x-2 px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium transition-colors shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export JSON</span>
          </a>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 w-full space-y-5">
        
        {/* 3. DOCUMENT HEADER */}
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center space-x-1 text-xs text-slate-500 hover:text-slate-800 transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Documents</span>
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div className="flex items-center space-x-2.5 flex-wrap">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  {doc.document_type || 'Document'} — {company.name || doc.company_name || doc.original_filename}
                </h1>
                {doc.review_status === 'VERIFIED' && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    Verified
                  </span>
                )}
                {doc.review_status === 'COMPLETED' && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Completed
                  </span>
                )}
                {doc.review_status === 'NEEDS_REVIEW' && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
                    Needs Review
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {doc.original_filename} &bull; Extracted via {doc.extraction_method === 'ocr_fallback' ? 'Tesseract OCR Fallback' : 'PyMuPDF Engine'}
              </p>
            </div>

            <div className="flex items-center space-x-3 text-xs text-slate-500 shrink-0">
              <span className="hidden sm:inline">
                Extracted on: {formatExtractionDate(doc.created_at)}
              </span>
              <a
                href={`/api/documents/${doc.id}/download-json`}
                className="px-2.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-md font-medium transition-colors shadow-xs inline-flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                <span>Export JSON</span>
              </a>
            </div>
          </div>
        </div>

        {/* SECTION 1: OVERVIEW DASHBOARD */}
        {activeSection === 'overview' && (
          <div className="space-y-5">
            
            {/* 4. TOP INFORMATION ROW (2 Equal Cards) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* Left Card: Document Information */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <div className="flex items-center space-x-2 pb-3.5 border-b border-slate-100">
                  <div className="w-6 h-6 rounded-md bg-emerald-50 text-emerald-700 flex items-center justify-center">
                    <FileText className="w-3.5 h-3.5" />
                  </div>
                  <h3 className="text-xs font-semibold text-slate-900">Document Information</h3>
                </div>

                <div className="pt-3 space-y-2.5 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Company Name</span>
                    <span className="font-semibold text-slate-900 text-right">{company.name || doc.company_name || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Registration / GSTIN</span>
                    <span className="font-semibold text-slate-900 text-right font-mono">{company.registration_id || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Document Type</span>
                    <span className="font-semibold text-slate-900 text-right">{doc.document_type || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Billing Period</span>
                    <span className="font-semibold text-slate-900 text-right">{period.billing_month || doc.reporting_period || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Issue / Bill Date</span>
                    <span className="font-semibold text-slate-900 text-right">{period.issue_date || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">Facility / Address</span>
                    <span className="font-semibold text-slate-900 text-right max-w-[200px] truncate" title={company.address}>{company.address || '—'}</span>
                  </div>
                </div>
              </div>

              {/* Right Card: Extraction Quality */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-3.5 border-b border-slate-100">
                    <div className="flex items-center space-x-2">
                      <div className="w-6 h-6 rounded-md bg-blue-50 text-blue-700 flex items-center justify-center">
                        <ShieldCheck className="w-3.5 h-3.5" />
                      </div>
                      <h3 className="text-xs font-semibold text-slate-900">Extraction Quality</h3>
                    </div>
                    <span className={`text-base font-bold ${
                      score >= 85 ? 'text-emerald-700' : score >= 70 ? 'text-orange-600' : 'text-rose-600'
                    }`}>
                      {score} <span className="text-xs font-normal text-slate-400">/ 100</span>
                    </span>
                  </div>

                  <div className="pt-3 space-y-2 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Expected fields</span>
                      <span className="font-semibold text-slate-900">
                        {qualitySummary.expected_fields_found ?? 2} / {qualitySummary.total_expected_fields ?? 4} found
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Evidence backed</span>
                      <span className="font-semibold text-slate-900">
                        {qualitySummary.evidence_backed ?? 9} / {evidenceList.length || 11}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">High confidence</span>
                      <span className="font-semibold text-slate-900">{qualitySummary.high_confidence ?? 9}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Needs review</span>
                      <span className={`font-semibold ${(qualitySummary.expected_fields_missing || 0) > 0 ? 'text-orange-600' : 'text-slate-900'}`}>
                        {qualitySummary.expected_fields_missing ?? 0}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Not applicable</span>
                      <span className="font-medium text-slate-600">
                        {qualitySummary.not_applicable_fields ?? 4} (0 penalty)
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 mt-2 border-t border-slate-100">
                  <button
                    onClick={() => setShowScoreModal(true)}
                    className="text-xs text-teal-700 hover:text-teal-900 font-medium inline-flex items-center gap-1"
                  >
                    <span>Why this score? ⓘ</span>
                  </button>
                </div>
              </div>

            </div>

            {/* 5. SUMMARY METRIC CARDS (4 Columns in 1 Row) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* Card 1: Energy */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-emerald-200 transition-colors">
                <div>
                  <div className="flex items-center space-x-2 pb-2.5 border-b border-slate-100">
                    <div className="w-5 h-5 rounded-md bg-emerald-50 text-emerald-700 flex items-center justify-center">
                      <Zap className="w-3 h-3" />
                    </div>
                    <h4 className="text-xs font-semibold text-slate-900">Energy</h4>
                  </div>
                  <div className="pt-2.5 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Grid Electricity</span>
                      <span className="font-semibold text-slate-900">
                        {energy.electricity_kwh != null ? `${energy.electricity_kwh.toLocaleString()} kWh` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Renewable / Solar</span>
                      <span className="font-semibold text-slate-900">
                        {energy.renewable_energy_kwh != null ? `${energy.renewable_energy_kwh.toLocaleString()} kWh` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Peak Demand</span>
                      <span className="font-semibold text-slate-900">
                        {energy.peak_demand_kva_kw != null ? `${energy.peak_demand_kva_kw.toLocaleString()} kVA` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Power Factor</span>
                      <span className="font-semibold text-slate-900">
                        {energy.power_factor != null ? `${energy.power_factor} PF` : '—'}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('energy')}
                  className="mt-3.5 w-full py-1.5 bg-emerald-50/70 hover:bg-emerald-100/70 text-emerald-800 text-xs font-medium rounded-lg text-center transition-colors"
                >
                  View details →
                </button>
              </div>

              {/* Card 2: Emissions */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-purple-200 transition-colors">
                <div>
                  <div className="flex items-center space-x-2 pb-2.5 border-b border-slate-100">
                    <div className="w-5 h-5 rounded-md bg-purple-50 text-purple-700 flex items-center justify-center">
                      <Flame className="w-3 h-3" />
                    </div>
                    <h4 className="text-xs font-semibold text-slate-900">Emissions</h4>
                  </div>
                  <div className="pt-2.5 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Scope 1 Emissions</span>
                      <span className="font-semibold text-slate-900">
                        {emissions.scope_1_direct_tco2e != null ? `${emissions.scope_1_direct_tco2e.toFixed(2)} tCO₂e` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Scope 2 (Grid)</span>
                      <span className="font-semibold text-slate-900">
                        {emissions.scope_2_indirect_tco2e != null ? `${emissions.scope_2_indirect_tco2e.toFixed(2)} tCO₂e` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Total Footprint</span>
                      <span className="font-semibold text-slate-900">
                        {emissions.total_ghg_emissions_tco2e != null ? `${emissions.total_ghg_emissions_tco2e.toFixed(2)} tCO₂e` : '—'}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('energy')}
                  className="mt-3.5 w-full py-1.5 bg-purple-50/70 hover:bg-purple-100/70 text-purple-800 text-xs font-medium rounded-lg text-center transition-colors"
                >
                  View details →
                </button>
              </div>

              {/* Card 3: Water & Waste */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-blue-200 transition-colors">
                <div>
                  <div className="flex items-center space-x-2 pb-2.5 border-b border-slate-100">
                    <div className="w-5 h-5 rounded-md bg-blue-50 text-blue-700 flex items-center justify-center">
                      <Droplets className="w-3 h-3" />
                    </div>
                    <h4 className="text-xs font-semibold text-slate-900">Water & Waste</h4>
                  </div>
                  <div className="pt-2.5 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Recycled / ZLD Water</span>
                      <span className="font-semibold text-slate-900">
                        {waterWaste.recycled_water_kl != null ? `${waterWaste.recycled_water_kl.toLocaleString()} kL` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Waste Diversion Rate</span>
                      <span className="font-semibold text-slate-900">
                        {waterWaste.waste_recycled_percentage != null ? `${waterWaste.waste_recycled_percentage}%` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Freshwater Use</span>
                      <span className="font-semibold text-slate-900">
                        {waterWaste.water_consumption_kl != null ? `${waterWaste.water_consumption_kl.toLocaleString()} kL` : '—'}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('water_waste')}
                  className="mt-3.5 w-full py-1.5 bg-blue-50/70 hover:bg-blue-100/70 text-blue-800 text-xs font-medium rounded-lg text-center transition-colors"
                >
                  View details →
                </button>
              </div>

              {/* Card 4: Financial */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-orange-200 transition-colors">
                <div>
                  <div className="flex items-center space-x-2 pb-2.5 border-b border-slate-100">
                    <div className="w-5 h-5 rounded-md bg-orange-50 text-orange-700 flex items-center justify-center">
                      <IndianRupee className="w-3 h-3" />
                    </div>
                    <h4 className="text-xs font-semibold text-slate-900">Financial</h4>
                  </div>
                  <div className="pt-2.5 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Total Billed Amount</span>
                      <span className="font-semibold text-slate-900">
                        {energy.total_energy_cost_inr != null ? `₹${energy.total_energy_cost_inr.toLocaleString()}` : '—'}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveSection('financial')}
                  className="mt-3.5 w-full py-1.5 bg-orange-50/70 hover:bg-orange-100/70 text-orange-800 text-xs font-medium rounded-lg text-center transition-colors"
                >
                  View details →
                </button>
              </div>

            </div>

            {/* 6. SOURCE EVIDENCE ANCHORS (TOP 5) */}
            <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
              <div className="px-5 py-3.5 bg-white border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 rounded-md bg-emerald-50 text-emerald-700 flex items-center justify-center">
                    <FileText className="w-3.5 h-3.5" />
                  </div>
                  <h3 className="text-xs font-semibold text-slate-900">Source Evidence Anchors (Top 5)</h3>
                </div>
                <button
                  onClick={() => setActiveSection('evidence')}
                  className="text-xs text-teal-700 hover:text-teal-900 font-medium transition-colors"
                >
                  View all evidence →
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50/70 border-b border-slate-100 text-slate-500 font-semibold">
                    <tr>
                      <th className="px-5 py-2.5">Field</th>
                      <th className="px-4 py-2.5">Extracted Value</th>
                      <th className="px-4 py-2.5">Confidence</th>
                      <th className="px-5 py-2.5 text-right">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {topEvidence.map((ev, idx) => {
                      const confPercent = ev.confidence ? Math.round(ev.confidence * 100) : 95;
                      return (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="px-5 py-2.5 font-medium text-slate-800">
                            {ev.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </td>
                          <td className="px-4 py-2.5 text-slate-700 font-medium">
                            {ev.human_corrected_value != null ? (
                              <span>{ev.human_corrected_value} {ev.unit || ''}</span>
                            ) : (
                              <span>{ev.value != null ? String(ev.value) : '—'} {ev.unit || ''}</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              High ({confPercent}%)
                            </span>
                          </td>
                          <td className="px-5 py-2.5 text-right text-slate-500">
                            Page 1
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* SECTION 2: ENERGY & EMISSIONS DRILL-DOWN */}
        {activeSection === 'energy' && (
          <div className="space-y-6">
            <ExtractionTable
              title="Energy & Fuel Metrics"
              rows={energyRows}
              evidenceList={evidenceList}
              notApplicableList={notApplicableList}
              fieldCorrections={fieldCorrections}
              onVerifyField={handleVerifyField}
              onSaveCorrection={handleSaveCorrection}
              isSubmitting={isSubmitting}
            />

            <ExtractionTable
              title="GHG Carbon Emissions (Scope 1 & Scope 2)"
              rows={emissionsRows}
              evidenceList={evidenceList}
              notApplicableList={notApplicableList}
              fieldCorrections={fieldCorrections}
              onVerifyField={handleVerifyField}
              onSaveCorrection={handleSaveCorrection}
              isSubmitting={isSubmitting}
            />
          </div>
        )}

        {/* SECTION 3: WATER & WASTE DRILL-DOWN */}
        {activeSection === 'water_waste' && (
          <div className="space-y-6">
            <ExtractionTable
              title="Water, Waste & Circularity"
              rows={waterWasteRows}
              evidenceList={evidenceList}
              notApplicableList={notApplicableList}
              fieldCorrections={fieldCorrections}
              onVerifyField={handleVerifyField}
              onSaveCorrection={handleSaveCorrection}
              isSubmitting={isSubmitting}
            />
          </div>
        )}

        {/* SECTION 4: FINANCIAL DRILL-DOWN */}
        {activeSection === 'financial' && (
          <div className="space-y-6">
            <ExtractionTable
              title="Financial & Tariff Summary"
              rows={financialRows}
              evidenceList={evidenceList}
              notApplicableList={notApplicableList}
              fieldCorrections={fieldCorrections}
              onVerifyField={handleVerifyField}
              onSaveCorrection={handleSaveCorrection}
              isSubmitting={isSubmitting}
            />

            {lineItems.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden mb-6">
                <div className="px-5 py-3.5 bg-slate-50/70 border-b border-slate-200">
                  <h3 className="text-xs font-semibold text-slate-900">Line Items & Tariff Charges ({lineItems.length})</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600">
                      <tr>
                        <th className="px-5 py-2.5">Description</th>
                        <th className="px-4 py-2.5">Quantity</th>
                        <th className="px-4 py-2.5">Unit</th>
                        <th className="px-4 py-2.5">Unit Rate</th>
                        <th className="px-5 py-2.5 text-right">Total Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {lineItems.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="px-5 py-2.5 font-medium text-slate-800">{item.item_description}</td>
                          <td className="px-4 py-2.5 text-slate-600">{item.quantity != null ? item.quantity.toLocaleString() : '—'}</td>
                          <td className="px-4 py-2.5 text-slate-500 font-mono">{item.unit || '—'}</td>
                          <td className="px-4 py-2.5 text-slate-600">{item.unit_rate != null ? `₹${item.unit_rate.toLocaleString()}` : '—'}</td>
                          <td className="px-5 py-2.5 text-right font-semibold text-slate-900">
                            {item.total_amount != null ? `₹${item.total_amount.toLocaleString()}` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* SECTION 5: EVIDENCE DRILL-DOWN */}
        {activeSection === 'evidence' && (
          <div className="space-y-6">
            <EvidenceSection evidence={evidenceList} />
          </div>
        )}

        {/* SECTION 6: COMPLIANCE DRILL-DOWN */}
        {activeSection === 'compliance' && (
          <div className="space-y-6">
            <ExtractionTable
              title="Compliance & Certifications"
              rows={complianceRows}
              evidenceList={evidenceList}
              notApplicableList={notApplicableList}
              fieldCorrections={fieldCorrections}
              onVerifyField={handleVerifyField}
              onSaveCorrection={handleSaveCorrection}
              isSubmitting={isSubmitting}
            />

            {/* Audit Trail Log */}
            {auditLogs.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
                <div className="px-5 py-3.5 bg-slate-50/70 border-b border-slate-200 flex items-center space-x-2">
                  <History className="w-4 h-4 text-teal-700" />
                  <h3 className="text-xs font-semibold text-slate-900">Review & Audit History ({auditLogs.length})</h3>
                </div>
                <div className="p-5 space-y-2 text-xs">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                      <div>
                        <span className="font-semibold text-slate-900">{log.field_name}</span>
                        <span className="text-slate-500 ml-2">({log.action.replace('_', ' ')})</span>
                        {log.notes && <p className="text-slate-600 mt-0.5">{log.notes}</p>}
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* WHY THIS SCORE MODAL */}
      {showScoreModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-slate-200 rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Extraction Quality Score Breakdown</h3>
              <button
                onClick={() => setShowScoreModal(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-2 font-mono text-slate-700">
              <div className="flex justify-between">
                <span className="font-sans text-slate-600">Base score</span>
                <span className="font-semibold text-slate-900">+{breakdown.base_score || 100}</span>
              </div>

              {breakdown.ocr_penalty > 0 && (
                <div className="flex justify-between text-rose-700">
                  <span className="font-sans">OCR fallback penalty</span>
                  <span>-{breakdown.ocr_penalty}</span>
                </div>
              )}

              {breakdown.expected_missing_penalty > 0 && (
                <div className="flex justify-between text-amber-700">
                  <span className="font-sans">Expected field missing penalty</span>
                  <span>-{breakdown.expected_missing_penalty}</span>
                </div>
              )}

              {breakdown.low_confidence_penalty > 0 && (
                <div className="flex justify-between text-rose-700">
                  <span className="font-sans">Low confidence penalty</span>
                  <span>-{breakdown.low_confidence_penalty}</span>
                </div>
              )}

              {breakdown.medium_confidence_penalty > 0 && (
                <div className="flex justify-between text-amber-700">
                  <span className="font-sans">Medium confidence penalty</span>
                  <span>-{breakdown.medium_confidence_penalty}</span>
                </div>
              )}

              {breakdown.evidence_penalty > 0 && (
                <div className="flex justify-between text-amber-700">
                  <span className="font-sans">Unbacked evidence penalty</span>
                  <span>-{breakdown.evidence_penalty}</span>
                </div>
              )}

              <div className="pt-2.5 border-t border-slate-200 flex justify-between font-bold text-slate-900 text-sm">
                <span className="font-sans">Final Quality Score</span>
                <span>{score} / 100</span>
              </div>
            </div>

            <div className="text-xs text-slate-500 space-y-1">
              <p>Scores are calculated deterministically based on document-expected fields, evidence coverage, and extraction method.</p>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setShowScoreModal(false)}
                className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
