import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  ArrowLeft,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  Info,
  Building2,
  Calendar,
  Layers,
  Sparkles
} from 'lucide-react';
import { getEvidenceReport, downloadEvidenceReportPDF } from '../services/api';

export default function EvidenceReport({ documentId, onBack, onNavigateToDocument }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [error, setError] = useState(null);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEvidenceReport(documentId);
      setReport(data);
    } catch (err) {
      console.error('Failed to load evidence report:', err);
      setError(err.response?.data?.detail || 'Failed to load evidence report.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (documentId) {
      fetchReport();
    }
  }, [documentId]);

  const handleDownloadPdf = async () => {
    if (!report) return;
    setDownloadingPdf(true);
    try {
      const docName = report.metadata?.document_name || `document_${documentId}`;
      const safeName = `${docName.replace(/\.[^/.]+$/, '')}_evidence_report.pdf`;
      await downloadEvidenceReportPDF(documentId, safeName);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="w-full max-w-5xl mx-auto py-12 px-4">
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-xs">
          <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto mb-3" />
          <h2 className="text-base font-bold text-slate-800">Compiling Grounded Evidence Report...</h2>
          <p className="text-xs text-slate-500 mt-1">Retrieving deterministic metrics, provenance, and data quality signals from SQL store.</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="w-full max-w-5xl mx-auto py-12 px-4">
        <div className="bg-white border border-red-200 rounded-xl p-8 text-center shadow-xs">
          <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-3" />
          <h2 className="text-base font-bold text-slate-800">Failed to Load Report</h2>
          <p className="text-xs text-slate-500 mt-1">{error || 'Report data could not be retrieved.'}</p>
          <div className="mt-4 flex justify-center gap-3">
            <button
              onClick={onBack}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back
            </button>
            <button
              onClick={fetchReport}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { metadata, metrics, emissions, evidence, data_quality, missing_data, insights, recommendations, executive_summary } = report;

  const isVerified = metadata.verification_status === 'VERIFIED';
  const needsReview = metadata.review_status === 'NEEDS_REVIEW';

  return (
    <div className="w-full max-w-5xl mx-auto py-4 px-2 sm:px-4 space-y-6">
      
      {/* Navigation & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Document Details</span>
        </button>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={fetchReport}
            disabled={loading}
            className="px-3.5 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-2xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            <span>Regenerate Report</span>
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="px-4 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-2xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloadingPdf ? 'Exporting PDF...' : 'Download PDF'}</span>
          </button>
        </div>
      </div>

      {/* Main Report Container */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        
        {/* REPORT HEADER */}
        <div className="bg-slate-50 border-b border-slate-200 p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 mb-2">
                <FileText className="w-3 h-3" />
                <span>Sustainability Evidence Report</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
                {metadata.company_name || 'Organization Sustainability Report'}
              </h1>
              <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-2 text-xs text-slate-600 font-medium">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  Reporting Period: <strong className="text-slate-800">{metadata.reporting_period || 'Not available'}</strong>
                </span>
                <span className="flex items-center gap-1">
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                  Type: <strong className="text-slate-800">{metadata.document_type || 'Unclassified'}</strong>
                </span>
              </div>
            </div>

            {/* Quality & Verification Badges */}
            <div className="flex flex-col sm:items-end gap-2 shrink-0">
              <div className="flex items-center gap-2">
                {isVerified ? (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    Verified
                  </span>
                ) : needsReview ? (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                    Needs Review
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    {metadata.verification_status || 'Ready'}
                  </span>
                )}

                <div className="px-2.5 py-1 bg-white border border-slate-200 rounded-md text-xs font-bold text-slate-800">
                  Score: <span className="text-emerald-700">{metadata.quality_score ? Math.round(metadata.quality_score) : 80}/100</span>
                </div>
              </div>
              <span className="text-[11px] text-slate-400">
                Generated: {new Date(metadata.generated_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}
              </span>
            </div>
          </div>
        </div>

        {/* REPORT BODY */}
        <div className="p-6 sm:p-8 space-y-8">

          {/* 1. EXECUTIVE SUMMARY */}
          {executive_summary && (
            <section className="space-y-2">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                Executive Summary
              </h2>
              <div className="bg-slate-50/80 border border-slate-200/80 rounded-lg p-4 text-xs text-slate-700 leading-relaxed">
                {executive_summary}
              </div>
            </section>
          )}

          {/* 2. KEY METRICS */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Key Sustainability Metrics
            </h2>
            {metrics && metrics.length > 0 ? (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Metric</th>
                      <th className="py-2.5 px-4 text-right">Value</th>
                      <th className="py-2.5 px-4">Unit</th>
                      <th className="py-2.5 px-4">Reporting Period</th>
                      <th className="py-2.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {metrics.map((m, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">{m.metric_name}</td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-slate-800">
                          {typeof m.value === 'number' ? m.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : m.value}
                        </td>
                        <td className="py-2.5 px-4 font-medium text-slate-500">{m.unit}</td>
                        <td className="py-2.5 px-4 text-slate-500">{m.reporting_period || '—'}</td>
                        <td className="py-2.5 px-4">
                          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">
                            {m.verification_status || 'EXTRACTED'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No structured sustainability metrics available.</p>
            )}
          </section>

          {/* 3. EMISSIONS SUMMARY */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Greenhouse Gas Emissions Summary
            </h2>
            {emissions && emissions.emissions_available ? (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Scope Category</th>
                      <th className="py-2.5 px-4 text-right">Value</th>
                      <th className="py-2.5 px-4">Unit</th>
                      <th className="py-2.5 px-4">Verification / Lineage</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {emissions.scope_1 != null && (
                      <tr className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">Scope 1 (Direct Fuel Combustion)</td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-slate-800">
                          {emissions.scope_1.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">{emissions.scope_1_unit}</td>
                        <td className="py-2.5 px-4 text-slate-500 text-[11px] font-mono">{emissions.scope_1_source || 'AI Extracted'}</td>
                      </tr>
                    )}
                    {emissions.scope_2 != null && (
                      <tr className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">Scope 2 (Purchased Grid Electricity)</td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-slate-800">
                          {emissions.scope_2.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">{emissions.scope_2_unit}</td>
                        <td className="py-2.5 px-4 text-slate-500 text-[11px] font-mono">{emissions.scope_2_source || 'AI Extracted'}</td>
                      </tr>
                    )}
                    {emissions.total_ghg != null && (
                      <tr className="bg-slate-50/70 font-bold">
                        <td className="py-2.5 px-4 text-slate-900">Total Recorded GHG Footprint</td>
                        <td className="py-2.5 px-4 text-right font-mono text-emerald-800">
                          {emissions.total_ghg.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-4 text-slate-600">{emissions.total_ghg_unit}</td>
                        <td className="py-2.5 px-4 text-slate-500 text-[11px] font-mono">{emissions.total_ghg_source || 'Aggregated Total'}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
                {emissions.dominant_scope === 'scope_2' && (
                  <div className="bg-blue-50/50 border-t border-blue-100 p-2.5 text-[11px] text-blue-800 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    <span>Scope 2 (grid electricity) is the larger documented emissions category in this document.</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-500 italic">
                Emissions data was not available in the selected document.
              </div>
            )}
          </section>

          {/* 4. EVIDENCE & PROVENANCE TABLE */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Evidence & Lineage Traceability
            </h2>
            {evidence && evidence.length > 0 ? (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Metric</th>
                      <th className="py-2.5 px-4 text-right">Extracted Value</th>
                      <th className="py-2.5 px-4">Unit</th>
                      <th className="py-2.5 px-4">Source Document Excerpt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {evidence.map((ev, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">{ev.metric_name}</td>
                        <td className="py-2.5 px-4 text-right font-mono text-slate-800">
                          {typeof ev.value === 'number' ? ev.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : (ev.value || '—')}
                        </td>
                        <td className="py-2.5 px-4 font-medium text-slate-500">{ev.unit || '—'}</td>
                        <td className="py-2.5 px-4 font-mono text-[11px] text-slate-600 bg-slate-50/30">
                          {ev.source_text || 'Source text unavailable.'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No supporting source evidence items recorded.</p>
            )}
          </section>

          {/* 5. DATA QUALITY & AUDIT */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Data Quality & Audit Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <span className="text-[11px] text-slate-400 font-semibold uppercase">Verification Status</span>
                <p className="text-sm font-bold text-slate-800 mt-0.5">{data_quality.verification_status || 'AI Extracted'}</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <span className="text-[11px] text-slate-400 font-semibold uppercase">Extraction Quality</span>
                <p className="text-sm font-bold text-slate-800 mt-0.5">{data_quality.quality_score ? Math.round(data_quality.quality_score) : 80}/100</p>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <span className="text-[11px] text-slate-400 font-semibold uppercase">Engine Lineage</span>
                <p className="text-sm font-bold text-slate-800 mt-0.5 capitalize">{data_quality.extraction_method || 'PyMuPDF Engine'}</p>
              </div>
            </div>

            {report.attention_flags && report.attention_flags.length > 0 && (
              <div className="bg-amber-50/70 border border-amber-200 rounded-lg p-3 space-y-1">
                <span className="text-xs font-bold text-amber-900 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  Attention Items
                </span>
                <ul className="text-xs text-amber-800 list-disc list-inside space-y-0.5">
                  {report.attention_flags.map((flag, idx) => (
                    <li key={idx}>{flag}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* 6. DATA NOT REPORTED */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Data Not Reported
            </h2>
            {missing_data && missing_data.length > 0 ? (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Metric / Dimension</th>
                      <th className="py-2.5 px-4">Status</th>
                      <th className="py-2.5 px-4">Reporting Note</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {missing_data.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-semibold text-slate-800">{item.display_name}</td>
                        <td className="py-2.5 px-4">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                            item.is_not_applicable
                              ? 'bg-slate-100 text-slate-500'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            {item.is_not_applicable ? 'Not Applicable' : 'Not Reported'}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">{item.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">All expected domain metrics are present in this document.</p>
            )}
          </section>

          {/* 7. DETERMINISTIC INSIGHTS */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Deterministic Insights
            </h2>
            {insights && insights.length > 0 ? (
              <div className="space-y-2">
                {insights.map((ins, idx) => (
                  <div key={idx} className="border border-slate-200 rounded-lg p-3 bg-white hover:bg-slate-50/50 transition-colors flex items-start gap-3">
                    <span className={`mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 ${
                      ins.severity === 'ATTENTION'
                        ? 'bg-amber-100 text-amber-800'
                        : ins.severity === 'REVIEW'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {ins.severity}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-slate-900">{ins.title}</p>
                      <p className="text-xs text-slate-600 mt-0.5">{ins.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-500 italic">
                No deterministic insights are available for this reporting period.
              </div>
            )}
          </section>

          {/* 8. DETERMINISTIC RECOMMENDATIONS */}
          <section className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Recommended Action Areas
            </h2>
            {recommendations && recommendations.length > 0 ? (
              <div className="space-y-3">
                {recommendations.map((rec, idx) => (
                  <div key={idx} className="border border-slate-200 rounded-lg p-4 bg-white space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-slate-900">{rec.title}</h3>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        rec.priority === 'HIGH'
                          ? 'bg-red-50 text-red-700 border border-red-200'
                          : rec.priority === 'MEDIUM'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        {rec.priority} Priority
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{rec.reason}</p>
                    {rec.suggested_actions && rec.suggested_actions.length > 0 && (
                      <ul className="text-xs text-slate-700 list-disc list-inside space-y-0.5 pt-1">
                        {rec.suggested_actions.map((act, aIdx) => (
                          <li key={aIdx}>{act}</li>
                        ))}
                      </ul>
                    )}
                    {rec.limitations && (
                      <p className="text-[11px] text-slate-400 italic pt-1">
                        Limitation: {rec.limitations}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-500 italic">
                No recommendations are available for this document.
              </div>
            )}
          </section>

          {/* 9. SOURCE DOCUMENT REFERENCE */}
          <section className="pt-4 border-t border-slate-200">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Source Document Verification
            </h2>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-slate-900">
                  {metadata.document_name}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Internal ID: {metadata.document_id} &bull; Company: {metadata.company_name || 'N/A'}
                </p>
              </div>
              <button
                onClick={() => onNavigateToDocument(metadata.document_id)}
                className="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
              >
                <span>View Document Detail</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-4 text-[11px] text-slate-400 flex flex-wrap justify-between items-center gap-2">
              <span>Report ID: {metadata.report_id}</span>
              <span>Senseible Document AI &bull; Grounded Deterministic Verification</span>
            </div>
          </section>

        </div>
      </div>

    </div>
  );
}
