import React, { useState } from 'react';
import { 
  FileText, 
  Eye, 
  Trash2, 
  Download, 
  RefreshCw, 
  Search, 
  Filter, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Zap, 
  ScanLine, 
  Layers,
  Building2,
  ExternalLink
} from 'lucide-react';
import { deleteDocument, processDocument } from '../services/api';

export default function DocumentList({ 
  documents, 
  total, 
  page, 
  setPage, 
  limit, 
  searchTerm, 
  setSearchTerm, 
  statusFilter, 
  setStatusFilter, 
  typeFilter, 
  setTypeFilter, 
  onSelectDocument, 
  onRefreshList 
}) {
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      setActionLoadingId(id);
      await deleteDocument(id);
      onRefreshList();
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('Failed to delete document');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReprocess = async (id, forceOcr, e) => {
    e.stopPropagation();
    try {
      setActionLoadingId(id);
      await processDocument(id, forceOcr);
      onRefreshList();
    } catch (err) {
      console.error('Failed to reprocess document:', err);
      alert('Failed to reprocess document');
    } finally {
      setActionLoadingId(null);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            Extracted
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3 h-3" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <Clock className="w-3 h-3 animate-spin" />
            {status}
          </span>
        );
    }
  };

  const getMethodBadge = (method) => {
    if (method === 'ocr_fallback') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/10 text-blue-300 border border-blue-500/20">
          <ScanLine className="w-3 h-3 text-blue-400" />
          Tesseract OCR
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
        <Zap className="w-3 h-3 text-amber-400" />
        PyMuPDF Text
      </span>
    );
  };

  return (
    <div className="glass-panel rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
      
      {/* Table Header & Controls */}
      <div className="p-5 border-b border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            MSME Sustainability Document Repository
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Showing {documents.length} of {total} documents
          </p>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search company, document..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/70 border-b border-slate-800 uppercase tracking-wider text-[11px] font-semibold text-slate-400">
            <tr>
              <th className="px-5 py-3.5">Document / Company</th>
              <th className="px-4 py-3.5">Category</th>
              <th className="px-4 py-3.5">Extraction Method</th>
              <th className="px-4 py-3.5">Key Metrics</th>
              <th className="px-4 py-3.5">Confidence</th>
              <th className="px-4 py-3.5">Status</th>
              <th className="px-5 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {documents.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <FileText className="w-8 h-8 text-slate-600" />
                    <p className="text-sm font-medium text-slate-400">No sustainability documents found</p>
                    <p className="text-xs text-slate-500">Upload a PDF or test with a sample document above</p>
                  </div>
                </td>
              </tr>
            ) : (
              documents.map((doc) => (
                <tr
                  key={doc.id}
                  onClick={() => onSelectDocument(doc)}
                  className="hover:bg-slate-800/40 cursor-pointer transition-colors group"
                >
                  {/* File & Company */}
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-slate-800 border border-slate-700/80 text-emerald-400 group-hover:border-emerald-500/40 transition-colors">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-200 group-hover:text-emerald-300 transition-colors">
                          {doc.original_filename}
                        </p>
                        <div className="flex items-center gap-1.5 text-slate-400 text-[11px] mt-0.5">
                          <Building2 className="w-3 h-3 text-slate-500" />
                          <span>{doc.company_name || 'MSME Enterprise'}</span>
                          <span>•</span>
                          <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Document Type */}
                  <td className="px-4 py-4">
                    <span className="font-medium text-slate-300">
                      {doc.document_type || 'Unclassified'}
                    </span>
                    {doc.reporting_period && (
                      <p className="text-[11px] text-slate-500">{doc.reporting_period}</p>
                    )}
                  </td>

                  {/* Method */}
                  <td className="px-4 py-4">
                    {getMethodBadge(doc.extraction_method)}
                  </td>

                  {/* Metrics Snapshot */}
                  <td className="px-4 py-4">
                    <div className="space-y-0.5 font-medium">
                      {doc.total_energy_kwh != null && (
                        <p className="text-amber-300">⚡ {doc.total_energy_kwh.toLocaleString()} kWh</p>
                      )}
                      {doc.total_emissions_tco2e != null && (
                        <p className="text-emerald-300">🌱 {doc.total_emissions_tco2e.toFixed(2)} tCO2e</p>
                      )}
                      {doc.total_water_kl != null && (
                        <p className="text-cyan-300">💧 {doc.total_water_kl.toLocaleString()} kL</p>
                      )}
                      {doc.total_energy_kwh == null && doc.total_emissions_tco2e == null && doc.total_water_kl == null && (
                        <span className="text-slate-500">-</span>
                      )}
                    </div>
                  </td>

                  {/* Confidence */}
                  <td className="px-4 py-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-14 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-400 rounded-full"
                          style={{ width: `${(doc.confidence_score || 0.85) * 100}%` }}
                        />
                      </div>
                      <span className="text-slate-400 font-mono text-[11px]">
                        {Math.round((doc.confidence_score || 0.85) * 100)}%
                      </span>
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-4">
                    {getStatusBadge(doc.status)}
                  </td>

                  {/* Actions */}
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end space-x-1.5">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDocument(doc);
                        }}
                        className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-emerald-400 transition-colors"
                        title="View Extracted Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      {doc.structured_data && (
                        <a
                          href={`/api/documents/${doc.id}/download-json`}
                          onClick={(e) => e.stopPropagation()}
                          className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-blue-400 transition-colors"
                          title="Export Structured JSON"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      )}

                      <button
                        onClick={(e) => handleReprocess(doc.id, false, e)}
                        disabled={actionLoadingId === doc.id}
                        className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-amber-400 transition-colors disabled:opacity-50"
                        title="Reprocess Document"
                      >
                        <RefreshCw className={`w-4 h-4 ${actionLoadingId === doc.id ? 'animate-spin text-amber-400' : ''}`} />
                      </button>

                      <button
                        onClick={(e) => handleDelete(doc.id, e)}
                        disabled={actionLoadingId === doc.id}
                        className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-rose-400 transition-colors disabled:opacity-50"
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
}
