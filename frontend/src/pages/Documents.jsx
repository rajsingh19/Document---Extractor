import React, { useState } from 'react';
import { Plus, Search } from 'lucide-react';
import UploadDocument from '../components/UploadDocument';
import DocumentTable from '../components/DocumentTable';

export default function Documents({
  documents = [],
  totalDocs = 0,
  page = 1,
  setPage,
  limit = 10,
  setLimit,
  searchTerm = '',
  setSearchTerm,
  statusFilter = '',
  setStatusFilter,
  onSelectDocument,
  onDeleteDocument,
  onReprocessDocument,
  onRefresh,
  isRefreshing,
  loadingActionId
}) {
  const [showUpload, setShowUpload] = useState(false);

  // Compute live counts
  const readyCount = documents.filter((d) => d.review_status === 'COMPLETED' || d.status === 'COMPLETED').length;
  const needsReviewCount = documents.filter((d) => d.review_status === 'NEEDS_REVIEW').length;
  const verifiedCount = documents.filter((d) => d.review_status === 'VERIFIED').length;

  const filters = [
    { label: 'All', count: totalDocs || documents.length, value: '' },
    { label: 'Needs Review', count: needsReviewCount, value: 'NEEDS_REVIEW' },
    { label: 'Ready', count: readyCount, value: 'COMPLETED' },
    { label: 'Verified', count: verifiedCount, value: 'VERIFIED' },
  ];

  const handleUploadSuccess = (newDoc) => {
    setShowUpload(false);
    onRefresh();
    if (newDoc) {
      onSelectDocument(newDoc);
    }
  };

  return (
    <div className="space-y-5 pb-12 w-full">
      
      {/* 1. TOP HEADER & MAIN ACTION */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Documents</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload business documents and review extracted sustainability data.
          </p>
        </div>

        <button
          onClick={() => setShowUpload(!showUpload)}
          className="inline-flex items-center justify-center space-x-1.5 px-3.5 py-2 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded-md text-xs font-semibold transition-colors shadow-xs self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Expandable Upload Panel */}
      {showUpload && (
        <UploadDocument
          onUploadSuccess={handleUploadSuccess}
          onCancel={() => setShowUpload(false)}
        />
      )}

      {/* 2. FILTERS & SEARCH ROW */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        {/* Filter Badges with Counts */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
          {filters.map((f) => {
            const isActive = statusFilter === f.value;
            return (
              <button
                key={f.label}
                onClick={() => {
                  setStatusFilter(f.value);
                  if (setPage) setPage(1);
                }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap flex items-center space-x-1.5 border ${
                  isActive
                    ? 'bg-slate-900 text-white border-slate-900 font-semibold'
                    : 'bg-white text-slate-700 hover:bg-slate-50 border-slate-200'
                }`}
              >
                <span>{f.label}</span>
                <span className={`text-[11px] ${isActive ? 'text-white/80' : 'text-slate-400 font-normal'}`}>
                  ({f.count})
                </span>
              </button>
            );
          })}
        </div>

        {/* Search Input Box */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              if (setPage) setPage(1);
            }}
            placeholder="Search documents..."
            className="w-full pl-8 pr-3 py-1.5 rounded-md bg-white border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-teal-700 shadow-2xs"
          />
        </div>
      </div>

      {/* 3. MAIN DOCUMENT TABLE */}
      <DocumentTable
        documents={documents}
        totalDocs={totalDocs}
        page={page}
        setPage={setPage}
        limit={limit}
        setLimit={setLimit}
        onSelectDocument={onSelectDocument}
        onDeleteDocument={onDeleteDocument}
        onReprocessDocument={onReprocessDocument}
        onOpenUpload={() => setShowUpload(true)}
        loadingActionId={loadingActionId}
      />

    </div>
  );
}
