import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  PlusCircle, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  FileDown, 
  ArrowRight, 
  Building2, 
  Layers, 
  Calendar, 
  Filter,
  ExternalLink,
  Info
} from 'lucide-react';
import { 
  getComplianceReports, 
  getComplianceFrameworks, 
  createComplianceReport, 
  generateComplianceReport,
  getComplianceReportPdfUrl
} from '../services/api';

export default function ComplianceReports({ onNavigate }) {
  const [reports, setReports] = useState([]);
  const [frameworks, setFrameworks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [frameworkFilter, setFrameworkFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Create Modal
  const [createModal, setCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    framework: 'GHG_PROTOCOL',
    reporting_period: '2024-10',
    organization_name: 'TARA ENGINEERING WORKS',
    notes: '',
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, [frameworkFilter, statusFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const fwData = await getComplianceFrameworks();
      setFrameworks(fwData || []);

      const params = {};
      if (frameworkFilter) params.framework = frameworkFilter;
      if (statusFilter) params.status = statusFilter;

      const rData = await getComplianceReports(params);
      setReports(rData.items || []);
    } catch (err) {
      console.error("Failed to load compliance reports:", err);
      setError("Unable to load compliance reports.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReport = async (e) => {
    e.preventDefault();
    try {
      setCreating(true);
      // 1. Create draft report
      const rep = await createComplianceReport(createForm);
      // 2. Populate disclosures deterministically
      await generateComplianceReport(rep.id);
      setCreateModal(false);
      
      if (onNavigate) {
        onNavigate('compliance-report-detail', rep.id);
      } else {
        loadData();
      }
    } catch (err) {
      console.error("Failed to create report:", err);
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (st) => {
    switch (st) {
      case 'DRAFT':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">DRAFT</span>;
      case 'GENERATED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">GENERATED</span>;
      case 'NEEDS_REVIEW':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">NEEDS REVIEW</span>;
      case 'FINALIZED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">FINALIZED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">{st}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-7 h-7 text-blue-600" />
              Compliance & Sustainability Report Builder
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Prepare evidence-backed reporting disclosures for GHG Protocol, BRSR, GRI, and CBAM frameworks.
            </p>
          </div>
          <button
            onClick={() => setCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm rounded-xl shadow-sm transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            Prepare New Report
          </button>
        </div>

        {/* FRAMEWORK CARDS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {frameworks.map((fw) => (
            <div
              key={fw.framework_code}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3 flex flex-col justify-between hover:border-slate-300 transition-all"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">
                    {fw.framework_code}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">v{fw.framework_version}</span>
                </div>
                <h3 className="text-sm font-bold text-slate-900">{fw.framework_name}</h3>
                <p className="text-xs text-slate-500 line-clamp-2">{fw.description}</p>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">{fw.sections.length} Sections</span>
                <button
                  onClick={() => {
                    setCreateForm(prev => ({ ...prev, framework: fw.framework_code }));
                    setCreateModal(true);
                  }}
                  className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
                >
                  <span>Prepare</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* FILTERS */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={frameworkFilter}
              onChange={(e) => setFrameworkFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Frameworks</option>
              <option value="GHG_PROTOCOL">GHG Protocol</option>
              <option value="BRSR">BRSR (SEBI)</option>
              <option value="GRI">GRI Standards</option>
              <option value="CBAM">EU CBAM</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Workflow Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="GENERATED">Generated</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="FINALIZED">Finalized</option>
            </select>

            {(frameworkFilter || statusFilter) && (
              <button
                onClick={() => { setFrameworkFilter(''); setStatusFilter(''); }}
                className="text-xs text-rose-600 hover:text-rose-700 font-medium ml-auto"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* REPORTS LIST */}
        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600 mb-2" />
            Loading compliance reports...
          </div>
        ) : reports.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-medium text-slate-800">No compliance reports prepared yet.</p>
            <p className="text-xs text-slate-400 mt-1">Select a framework above to prepare your first report.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((rep) => (
              <div
                key={rep.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all p-5"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {rep.report_code}
                      </span>
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                        {rep.framework}
                      </span>
                      {getStatusBadge(rep.status)}
                      <span className="text-xs text-slate-500 font-medium">
                        Completeness: <strong>{rep.completeness_status}</strong>
                      </span>
                    </div>

                    <div>
                      <h3 
                        onClick={() => onNavigate && onNavigate('compliance-report-detail', rep.id)}
                        className="text-base font-semibold text-slate-900 hover:text-blue-700 transition-colors cursor-pointer"
                      >
                        {rep.report_name}
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Organization: <strong>{rep.organization_name}</strong> | Period: <strong>{rep.reporting_period}</strong>
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
                      <span className="bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-emerald-800">
                        Supported: <strong>{rep.supported_disclosures} / {rep.total_disclosures}</strong>
                      </span>
                      {rep.missing_disclosures > 0 && (
                        <span className="bg-rose-50 px-2 py-0.5 rounded border border-rose-200 text-rose-800">
                          Missing: <strong>{rep.missing_disclosures}</strong>
                        </span>
                      )}
                      <span className="text-slate-400">
                        Version {rep.report_version} | Generated {rep.generated_at ? new Date(rep.generated_at).toLocaleDateString() : 'Draft'}
                      </span>
                    </div>
                  </div>

                  {/* ACTIONS */}
                  <div className="flex items-center gap-2">
                    <a
                      href={getComplianceReportPdfUrl(rep.id)}
                      download
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg border border-slate-200 transition-colors flex items-center gap-1.5"
                    >
                      <FileDown className="w-3.5 h-3.5 text-slate-600" />
                      PDF
                    </a>
                    <button
                      onClick={() => onNavigate && onNavigate('compliance-report-detail', rep.id)}
                      className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1"
                    >
                      <span>Preview Report</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* CREATE REPORT MODAL */}
        {createModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">Prepare Compliance Report</h3>
                <button
                  onClick={() => setCreateModal(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateReport} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Target Framework</label>
                  <select
                    value={createForm.framework}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, framework: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-semibold"
                  >
                    <option value="GHG_PROTOCOL">GHG Protocol Corporate Standard</option>
                    <option value="BRSR">BRSR (SEBI Essential Indicators)</option>
                    <option value="GRI">GRI Environmental Standards (GRI 302 & 305)</option>
                    <option value="CBAM">EU Carbon Border Adjustment Mechanism (CBAM)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Reporting Period</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 2024-10"
                    value={createForm.reporting_period}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, reporting_period: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Reporting Organization</label>
                  <input
                    type="text"
                    required
                    value={createForm.organization_name}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, organization_name: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-500 flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                  <p>
                    Report disclosures will be generated deterministically from <strong>POSTED</strong> carbon ledger entries, extracted metrics, and activity data. Unsupported disclosures will be cleanly flagged as <strong>MISSING</strong> rather than fabricated.
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
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {creating ? 'Generating Report...' : 'Prepare & Populate Report'}
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
