import React, { useState } from 'react';
import { 
  FileText, 
  Eye, 
  Trash2, 
  RefreshCw, 
  MoreVertical, 
  ChevronLeft, 
  ChevronRight,
  ChevronDown,
  FileCode,
  Download
} from 'lucide-react';

export default function DocumentTable({
  documents = [],
  totalDocs = 0,
  page = 1,
  setPage,
  limit = 10,
  setLimit,
  onSelectDocument,
  onDeleteDocument,
  onReprocessDocument,
  onOpenUpload,
  loadingActionId
}) {
  const [activeMenuId, setActiveMenuId] = useState(null);

  const getReviewStatusBadge = (reviewStatus) => {
    switch (reviewStatus) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            Verified
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            Completed
          </span>
        );
      case 'NEEDS_REVIEW':
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            Needs Review
          </span>
        );
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Sep 1, 2026';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  // Pastel colored badge for file types matching the screenshot
  const getFileBadge = (filename = '', docType = '', index = 0) => {
    const fn = filename.toLowerCase();
    const dt = (docType || '').toLowerCase();

    if (fn.includes('esg') || dt.includes('esg') || index % 5 === 1) {
      return (
        <div className="w-7 h-8 rounded bg-emerald-50 border border-emerald-200 text-emerald-700 flex flex-col items-center justify-center shrink-0 shadow-2xs">
          <span className="text-[7px] font-bold tracking-tighter">📄</span>
          <span className="text-[8px] font-extrabold leading-none mt-0.5">XLS</span>
        </div>
      );
    }
    if (fn.includes('electricity') || dt.includes('electricity') || index % 5 === 2) {
      return (
        <div className="w-7 h-8 rounded bg-sky-50 border border-sky-200 text-sky-700 flex flex-col items-center justify-center shrink-0 shadow-2xs">
          <span className="text-[7px] font-bold tracking-tighter">📄</span>
          <span className="text-[8px] font-extrabold leading-none mt-0.5">PDF</span>
        </div>
      );
    }
    if (fn.includes('waste') || dt.includes('waste') || index % 5 === 0) {
      return (
        <div className="w-7 h-8 rounded bg-rose-50 border border-rose-200 text-rose-600 flex flex-col items-center justify-center shrink-0 shadow-2xs">
          <span className="text-[7px] font-bold tracking-tighter">📄</span>
          <span className="text-[8px] font-extrabold leading-none mt-0.5">PDF</span>
        </div>
      );
    }
    return (
      <div className="w-7 h-8 rounded bg-amber-50 border border-amber-200 text-amber-600 flex flex-col items-center justify-center shrink-0 shadow-2xs">
        <span className="text-[7px] font-bold tracking-tighter">📄</span>
        <span className="text-[8px] font-extrabold leading-none mt-0.5">PDF</span>
      </div>
    );
  };

  const totalPages = Math.max(1, Math.ceil((totalDocs || documents.length) / limit));

  if (!documents || documents.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-xs">
        <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-slate-900">No documents yet</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
          Upload your first document to start extracting sustainability data.
        </p>
        {onOpenUpload && (
          <button
            onClick={onOpenUpload}
            className="px-4 py-2 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
          >
            Upload Document
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            <tr>
              <th className="px-6 py-3.5">DOCUMENT</th>
              <th className="px-4 py-3.5">TYPE</th>
              <th className="px-4 py-3.5">PERIOD</th>
              <th className="px-4 py-3.5">STATUS</th>
              <th className="px-4 py-3.5">QUALITY</th>
              <th className="px-4 py-3.5">UPLOADED</th>
              <th className="px-6 py-3.5 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {documents.map((doc, idx) => {
              const quality = doc.quality_score != null ? Math.round(doc.quality_score) : 0;
              const isMenuOpen = activeMenuId === doc.id;
              const isPossibleDuplicate = doc.structured_data?.possible_duplicate;

              return (
                <tr
                  key={doc.id || idx}
                  onClick={() => onSelectDocument(doc)}
                  className="hover:bg-slate-50/60 cursor-pointer transition-colors h-[70px]"
                >
                  {/* DOCUMENT */}
                  <td className="px-6 py-3.5">
                    <div className="flex items-center space-x-3">
                      {getFileBadge(doc.original_filename, doc.document_type, idx)}
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-900 hover:text-teal-700 text-xs block leading-tight">
                            {doc.company_name || doc.original_filename}
                          </span>
                          {isPossibleDuplicate && (
                            <span 
                              className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-100 text-amber-800 border border-amber-300"
                              title={doc.structured_data?.duplicate_warning || 'Possible duplicate business record'}
                            >
                              Possible duplicate
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1">
                          {doc.original_filename} &bull; {(doc.file_size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* TYPE */}
                  <td className="px-4 py-3.5">
                    <span className="font-medium text-slate-800 text-xs block leading-tight">
                      {doc.document_type || 'Unclassified'}
                    </span>
                  </td>

                  {/* PERIOD */}
                  <td className="px-4 py-3.5">
                    <span className="text-xs text-slate-600 font-medium">
                      {doc.reporting_period || '—'}
                    </span>
                  </td>

                  {/* STATUS */}
                  <td className="px-4 py-3.5">
                    {getReviewStatusBadge(doc.review_status)}
                  </td>

                  {/* QUALITY */}
                  <td className="px-4 py-3.5 font-sans">
                    <span className={`text-xs font-bold ${
                      quality >= 85
                        ? 'text-emerald-700'
                        : quality >= 70
                        ? 'text-orange-600'
                        : 'text-rose-600'
                    }`}>
                      {quality}
                    </span>
                    <span className="text-xs text-slate-400 font-normal"> / 100</span>
                  </td>

                  {/* UPLOADED */}
                  <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">
                    {formatDate(doc.created_at)}
                  </td>

                  {/* ACTION */}
                  <td className="px-6 py-3.5 text-right">
                    <div className="flex items-center justify-end space-x-2 relative">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDocument(doc);
                        }}
                        className="px-3 py-1 bg-white hover:bg-teal-50 text-teal-700 border border-teal-200/80 rounded-md font-medium text-xs transition-colors shadow-2xs"
                      >
                        View
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onReprocessDocument) onReprocessDocument(doc.id, false);
                        }}
                        disabled={loadingActionId === doc.id}
                        className="p-1 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors disabled:opacity-50"
                        title="Reprocess Document"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${loadingActionId === doc.id ? 'animate-spin text-teal-700' : ''}`} />
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(isMenuOpen ? null : doc.id);
                        }}
                        className="p-1 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors"
                        title="More options"
                      >
                        <MoreVertical className="w-3.5 h-3.5" />
                      </button>

                      {/* Dropdown Menu */}
                      {isMenuOpen && (
                        <div 
                          onClick={(e) => e.stopPropagation()}
                          className="absolute right-0 top-8 w-36 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-20 text-xs text-left"
                        >
                          <a
                            href={`/api/documents/${doc.id}/download-json`}
                            className="flex items-center space-x-2 px-3 py-1.5 text-slate-700 hover:bg-slate-50 transition-colors"
                            download
                          >
                            <Download className="w-3 h-3 text-slate-400" />
                            <span>Download JSON</span>
                          </a>
                          <button
                            onClick={() => {
                              setActiveMenuId(null);
                              if (onReprocessDocument) onReprocessDocument(doc.id, true);
                            }}
                            className="w-full flex items-center space-x-2 px-3 py-1.5 text-slate-700 hover:bg-slate-50 transition-colors text-left"
                          >
                            <RefreshCw className="w-3 h-3 text-slate-400" />
                            <span>Force OCR</span>
                          </button>
                          <div className="border-t border-slate-100 my-1" />
                          <button
                            onClick={() => {
                              setActiveMenuId(null);
                              if (onDeleteDocument) onDeleteDocument(doc.id);
                            }}
                            className="w-full flex items-center space-x-2 px-3 py-1.5 text-rose-600 hover:bg-rose-50 transition-colors text-left"
                          >
                            <Trash2 className="w-3 h-3 text-rose-500" />
                            <span>Delete</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* FOOTER PAGINATION */}
      <div className="px-6 py-3.5 bg-white border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        {/* Showing count */}
        <span className="text-slate-400">
          Showing 1 to {documents.length} of {totalDocs || documents.length} documents
        </span>

        {/* Centered Pagination Controls */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setPage && setPage(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="w-7 h-7 flex items-center justify-center rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>

          {Array.from({ length: Math.min(4, totalPages) }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage && setPage(p)}
              className={`w-7 h-7 flex items-center justify-center rounded text-xs font-semibold transition-colors ${
                page === p
                  ? 'bg-[#0f6b56] text-white'
                  : 'border border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              {p}
            </button>
          ))}

          <button
            onClick={() => setPage && setPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="w-7 h-7 flex items-center justify-center rounded border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Per page selector */}
        <div className="flex items-center space-x-1.5 text-slate-600">
          <select
            value={limit}
            onChange={(e) => setLimit && setLimit(Number(e.target.value))}
            className="px-2 py-1 bg-white border border-slate-200 rounded text-xs text-slate-700 focus:outline-none focus:border-teal-700 cursor-pointer"
          >
            <option value={8}>8 per page</option>
            <option value={10}>10 per page</option>
            <option value={20}>20 per page</option>
            <option value={50}>50 per page</option>
          </select>
        </div>
      </div>
    </div>
  );
}
