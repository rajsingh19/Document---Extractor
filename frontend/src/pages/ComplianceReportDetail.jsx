import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  ArrowLeft, 
  FileDown, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle, 
  RefreshCw, 
  ShieldCheck, 
  Layers, 
  Clock, 
  Building2, 
  FileCheck,
  Edit3,
  ExternalLink,
  History,
  Info,
  AlertTriangle
} from 'lucide-react';
import { 
  getComplianceReport, 
  generateComplianceReport, 
  updateComplianceReportStatus, 
  updateDisclosureUserValue,
  getComplianceReportPdfUrl
} from '../services/api';

export default function ComplianceReportDetail({ reportId, onNavigate }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);

  // Evidence Drawer / Edit Modal
  const [selectedDisclosure, setSelectedDisclosure] = useState(null);
  const [editUserValue, setEditUserValue] = useState('');
  const [editUnit, setEditUnit] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [savingUserValue, setSavingUserValue] = useState(false);

  // Status Modal
  const [statusModal, setStatusModal] = useState(false);
  const [newStatus, setNewStatus] = useState('FINALIZED');
  const [newAssurance, setNewAssurance] = useState('NOT_ASSURED');
  const [statusNote, setStatusNote] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    loadReport();
  }, [reportId]);

  const loadReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getComplianceReport(reportId);
      setReport(data);
    } catch (err) {
      console.error("Failed to load compliance report:", err);
      setError("Unable to load compliance report details.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      setGenerating(true);
      const data = await generateComplianceReport(reportId);
      setReport(data);
    } catch (err) {
      console.error("Failed to regenerate report:", err);
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveUserValue = async (e) => {
    e.preventDefault();
    if (!selectedDisclosure) return;
    try {
      setSavingUserValue(true);
      await updateDisclosureUserValue(selectedDisclosure.id, editUserValue, editUnit || null, editNotes || null);
      setSelectedDisclosure(null);
      loadReport();
    } catch (err) {
      console.error("Failed to update disclosure user value:", err);
    } finally {
      setSavingUserValue(false);
    }
  };

  const handleStatusUpdate = async (e) => {
    e.preventDefault();
    try {
      setUpdatingStatus(true);
      await updateComplianceReportStatus(reportId, newStatus, newAssurance, statusNote || null);
      setStatusModal(false);
      loadReport();
    } catch (err) {
      console.error("Failed to update report status:", err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const getDisclosureBadge = (st) => {
    switch (st) {
      case 'SUPPORTED':
        return <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 rounded border border-emerald-200">SUPPORTED</span>;
      case 'PARTIALLY_SUPPORTED':
        return <span className="px-2 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 rounded border border-blue-200">PARTIAL</span>;
      case 'NEEDS_REVIEW':
        return <span className="px-2 py-0.5 text-xs font-semibold bg-amber-50 text-amber-700 rounded border border-amber-200">NEEDS REVIEW</span>;
      case 'MISSING':
        return <span className="px-2 py-0.5 text-xs font-semibold bg-rose-50 text-rose-700 rounded border border-rose-200">MISSING</span>;
      case 'NOT_APPLICABLE':
        return <span className="px-2 py-0.5 text-xs font-semibold bg-slate-100 text-slate-600 rounded">N/A</span>;
      default:
        return <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">{st}</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-12 text-center text-slate-500">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-600 mb-2" />
        Loading report payload...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-slate-50 p-12 text-center text-slate-500">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <p className="font-semibold text-slate-800">{error || "Report not found."}</p>
        <button
          onClick={() => onNavigate && onNavigate('compliance-reports')}
          className="mt-4 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium"
        >
          Back to Reports
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
            onClick={() => onNavigate && onNavigate('compliance-reports')}
            className="inline-flex items-center gap-1.5 text-slate-600 hover:text-slate-900 text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Compliance Reports
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRegenerate}
              disabled={generating || report.status === 'FINALIZED'}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl border border-slate-200 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
              Regenerate Content
            </button>
            <button
              onClick={() => {
                setStatusModal(true);
                setNewStatus(report.status);
                setNewAssurance(report.assurance_status);
                setStatusNote('');
              }}
              className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl transition-colors"
            >
              Update Workflow Status
            </button>
            <a
              href={getComplianceReportPdfUrl(report.id)}
              download
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors shadow-sm flex items-center gap-1.5"
            >
              <FileDown className="w-4 h-4" />
              Download PDF Report
            </a>
          </div>
        </div>

        {/* REPORT HEADER */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-bold px-2.5 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">
                  {report.framework} v{report.framework_version}
                </span>
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  {report.report_code}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
                  {report.status}
                </span>
              </div>
              <h1 className="text-xl font-bold text-slate-900">{report.report_name}</h1>
            </div>

            <div className="text-right text-xs text-slate-500">
              <div>Reporting Period: <strong className="text-slate-800">{report.reporting_period}</strong></div>
              <div>Organization: <strong className="text-slate-800">{report.organization_name}</strong></div>
            </div>
          </div>

          {/* SUMMARY CARDS */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span className="text-slate-400 block uppercase font-medium">Completeness</span>
              <strong className="text-sm font-bold text-slate-800 mt-0.5 block">{report.completeness_status}</strong>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span className="text-slate-400 block uppercase font-medium">Supported Disclosures</span>
              <strong className="text-sm font-bold text-emerald-700 mt-0.5 block">{report.supported_disclosures} / {report.total_disclosures}</strong>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span className="text-slate-400 block uppercase font-medium">Missing Disclosures</span>
              <strong className="text-sm font-bold text-rose-700 mt-0.5 block">{report.missing_disclosures}</strong>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span className="text-slate-400 block uppercase font-medium">Assurance Workflow</span>
              <strong className="text-sm font-bold text-purple-700 mt-0.5 block">{report.assurance_status}</strong>
            </div>
          </div>

          {/* DISCLAIMER BOX */}
          <div className="bg-amber-50/70 p-3.5 rounded-xl border border-amber-200 flex items-start gap-2.5 text-xs text-amber-900">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="block font-semibold">REPORT PREPARATION NOTICE</strong>
              <p className="mt-0.5">{report.disclaimer}</p>
            </div>
          </div>
        </div>

        {/* SECTIONS & DISCLOSURES TABLE */}
        <div className="space-y-6">
          {report.sections.map((sec) => (
            <div key={sec.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{sec.section_title}</h3>
                  <span className="text-xs text-slate-400 font-medium">Code: {sec.section_code}</span>
                </div>
                <span className="text-xs font-semibold px-2.5 py-1 bg-white rounded-lg border border-slate-200 text-slate-700">
                  Section Completeness: {sec.completeness}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200">
                      <th className="py-3 px-4 w-32">Code</th>
                      <th className="py-3 px-4">Disclosure Title</th>
                      <th className="py-3 px-4 w-44">Reported Value</th>
                      <th className="py-3 px-4 w-28">Status</th>
                      <th className="py-3 px-4 w-28">Source</th>
                      <th className="py-3 px-4 w-24 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sec.disclosures.map((d) => (
                      <tr key={d.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-slate-600">{d.disclosure_code}</td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-slate-800">{d.disclosure_title}</div>
                          {d.disclosure_description && (
                            <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">{d.disclosure_description}</div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {d.value ? (
                            <span className="font-bold text-slate-900">
                              {d.value} {d.value_unit || ''}
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">Missing / Unavailable</span>
                          )}
                        </td>
                        <td className="py-3 px-4">{getDisclosureBadge(d.status)}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono text-[10px]">
                            {d.source_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedDisclosure(d);
                              setEditUserValue(d.value || '');
                              setEditUnit(d.value_unit || '');
                              setEditNotes(d.notes || '');
                            }}
                            className="text-blue-600 hover:text-blue-800 font-semibold"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>

        {/* DISCLOSURE DETAILS / EDIT DRAWER MODAL */}
        {selectedDisclosure && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                    {selectedDisclosure.disclosure_code}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 mt-1">{selectedDisclosure.disclosure_title}</h3>
                </div>
                <button
                  onClick={() => setSelectedDisclosure(null)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
                >
                  ✕
                </button>
              </div>

              {selectedDisclosure.disclosure_description && (
                <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  {selectedDisclosure.disclosure_description}
                </p>
              )}

              {/* EVIDENCE LINEAGE */}
              <div className="space-y-2 text-xs">
                <h4 className="font-semibold text-slate-500 uppercase tracking-wider">Provenance & Evidence Lineage</h4>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-1.5 text-slate-700">
                  <div>Source Type: <strong>{selectedDisclosure.source_type}</strong></div>
                  {selectedDisclosure.source_document_id && (
                    <div>Source Document ID: <strong>#{selectedDisclosure.source_document_id}</strong></div>
                  )}
                  {selectedDisclosure.source_ledger_entry_id && (
                    <div>Source Carbon Ledger Entry ID: <strong>#{selectedDisclosure.source_ledger_entry_id}</strong></div>
                  )}
                  {selectedDisclosure.source_text && (
                    <div className="pt-1 text-slate-600 italic">"{selectedDisclosure.source_text}"</div>
                  )}
                </div>
              </div>

              {/* USER OVERRIDE FORM */}
              <form onSubmit={handleSaveUserValue} className="space-y-3 pt-2 border-t border-slate-200 text-xs">
                <h4 className="font-semibold text-slate-700 uppercase">User Override / Manual Input</h4>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Value</label>
                  <input
                    type="text"
                    placeholder="Enter explicit disclosure value..."
                    value={editUserValue}
                    onChange={(e) => setEditUserValue(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Unit</label>
                  <input
                    type="text"
                    placeholder="e.g. tCO2e, kWh, L"
                    value={editUnit}
                    onChange={(e) => setEditUnit(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedDisclosure(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    disabled={savingUserValue || report.status === 'FINALIZED'}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {savingUserValue ? 'Saving...' : 'Save User Value'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* STATUS UPDATE MODAL */}
        {statusModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">Update Report Status</h3>
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
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="DRAFT">DRAFT</option>
                    <option value="GENERATED">GENERATED</option>
                    <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                    <option value="FINALIZED">FINALIZED (Immutable)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Assurance Status</label>
                  <select
                    value={newAssurance}
                    onChange={(e) => setNewAssurance(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="NOT_ASSURED">NOT_ASSURED</option>
                    <option value="INTERNAL_REVIEW">INTERNAL_REVIEW</option>
                    <option value="EXTERNAL_ASSURANCE_PENDING">EXTERNAL_ASSURANCE_PENDING</option>
                    <option value="EXTERNALLY_ASSURED">EXTERNALLY_ASSURED</option>
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
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
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
