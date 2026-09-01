import React, { useState } from 'react';
import { 
  FileText, 
  Eye, 
  Trash2, 
  RefreshCw, 
  MoreVertical, 
  ChevronLeft, 
  ChevronRight,
  AlertCircle
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

  const getStatusBadge = (doc) => {
    const status = doc.status;
    const reviewStatus = doc.review_status;

    if (status === 'PROCESSING' || status === 'RUNNING_OCR' || status === 'RUNNING_LLM') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
          PROCESSING
        </span>
      );
    }
    if (status === 'FAILED') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200">
          FAILED
        </span>
      );
    }
    if (reviewStatus === 'VERIFIED') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          VERIFIED
        </span>
      );
    }
    if (reviewStatus === 'NEEDS_REVIEW') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
          NEEDS REVIEW
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
        READY
      </span>
    );
  };

  const formatRelativeTime = (dateString) => {
    if (!dateString) return 'Just now';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffMin = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMin / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMin < 2) return 'Just now';
      if (diffMin < 60) return `${diffMin} min ago`;
      if (diffHours < 24) return `${diffHours} hr ago`;
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Recent';
    }
  };

  const totalPages = Math.ceil(totalDocs / limit) || 1;

  if (documents.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-10 text-center space-y-3 shadow-2xs">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
          <FileText className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-slate-900">No documents found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Upload your first electricity bill, fuel receipt, water bill, or waste manifest to begin extraction.
          </p>
        </div>
        <div className="pt-2">
          <button
            onClick={onOpenUpload}
            className="px-3.5 py-1.5 bg-[#0f6b56] hover:bg-[#0c5947] text-white text-xs font-semibold rounded transition-colors shadow-2xs"
          >
            Upload Document
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-2xs overflow-hidden">
      
      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <th className="py-2.5 px-4">Document</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3">Reporting Period</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Quality</th>
              <th className="py-2.5 px-3">Uploaded</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {documents.map((doc) => {
              const quality = doc.quality_score != null ? Math.round(doc.quality_score) : null;
              const period = doc.reporting_period || doc.structured_data?.period?.billing_month || '—';
              const docType = doc.document_type || 'Unknown / Other';
              const isSample = doc.original_filename?.toLowerCase().includes('sample') || doc.filename?.toLowerCase().includes('sample');

              return (
                <tr 
                  key={doc.id}
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  onClick={() => onSelectDocument(doc)}
                >
                  {/* Document Column */}
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-6 h-6 rounded bg-slate-100 text-slate-600 flex items-center justify-center shrink-0 border border-slate-200">
                        <FileText className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0 max-w-xs sm:max-w-sm">
                        <div className="flex items-center space-x-1.5">
                          <span className="font-medium text-slate-900 truncate block">
                            {doc.original_filename || doc.filename}
                          </span>
                          {isSample && (
                            <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] font-medium bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                              DEMO DATA
                            </span>
                          )}
                        </div>
                        {doc.company_name && (
                          <span className="text-[11px] text-slate-400 truncate block">
                            {doc.company_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Type Column */}
                  <td className="py-3 px-3">
                    <span className="text-slate-700 font-medium">
                      {docType}
                    </span>
                  </td>

                  {/* Reporting Period Column */}
                  <td className="py-3 px-3 text-slate-600">
                    {period}
                  </td>

                  {/* Status Badge Column */}
                  <td className="py-3 px-3">
                    {getStatusBadge(doc)}
                  </td>

                  {/* Quality Score Column */}
                  <td className="py-3 px-3">
                    {quality != null ? (
                      <span className="font-medium text-slate-800">
                        {quality} <span className="text-slate-400 font-normal">/ 100</span>
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>

                  {/* Uploaded Timestamp Column */}
                  <td className="py-3 px-3 text-slate-500 whitespace-nowrap">
                    {formatRelativeTime(doc.created_at)}
                  </td>

                  {/* Action Column */}
                  <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end space-x-1.5">
                      <button
                        onClick={() => onSelectDocument(doc)}
                        className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded text-slate-700 text-xs font-medium transition-colors shadow-2xs"
                      >
                        View
                      </button>

                      {/* Optional Dropdown Menu */}
                      <div className="relative">
                        <button
                          onClick={() => setActiveMenuId(activeMenuId === doc.id ? null : doc.id)}
                          className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                        >
                          <MoreVertical className="w-3.5 h-3.5" />
                        </button>

                        {activeMenuId === doc.id && (
                          <div className="absolute right-0 top-full mt-1 w-36 bg-white border border-slate-200 rounded-md shadow-md z-20 py-1 text-xs text-slate-700">
                            <button
                              onClick={() => {
                                setActiveMenuId(null);
                                onReprocessDocument(doc.id, false);
                              }}
                              className="w-full text-left px-3 py-1.5 hover:bg-slate-50 flex items-center space-x-1.5"
                            >
                              <RefreshCw className="w-3 h-3 text-slate-400" />
                              <span>Reprocess</span>
                            </button>
                            <button
                              onClick={() => {
                                setActiveMenuId(null);
                                onDeleteDocument(doc.id);
                              }}
                              className="w-full text-left px-3 py-1.5 hover:bg-rose-50 text-rose-600 flex items-center space-x-1.5"
                            >
                              <Trash2 className="w-3 h-3 text-rose-500" />
                              <span>Delete</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalDocs > limit && (
        <div className="border-t border-slate-100 px-4 py-2.5 bg-slate-50/50 flex items-center justify-between text-xs text-slate-600">
          <div>
            Showing <span className="font-medium text-slate-900">{(page - 1) * limit + 1}</span> to{' '}
            <span className="font-medium text-slate-900">{Math.min(page * limit, totalDocs)}</span> of{' '}
            <span className="font-medium text-slate-900">{totalDocs}</span> documents
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="p-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 font-medium">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="p-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
