import React, { useState, useEffect, useCallback } from 'react';
import Navbar from '../components/Navbar';
import StatsCards from '../components/StatsCards';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import DocumentDetailModal from '../components/DocumentDetailModal';
import { getDocuments, getStats, getHealth, getDocument } from '../services/api';

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const [healthData, statsData, docsData] = await Promise.all([
        getHealth().catch(() => null),
        getStats().catch(() => null),
        getDocuments({
          page,
          limit,
          search: searchTerm || undefined,
          status: statusFilter || undefined,
          doc_type: typeFilter || undefined,
        }).catch(() => ({ documents: [], total: 0 })),
      ]);

      if (healthData) setHealth(healthData);
      if (statsData) setStats(statsData);
      if (docsData) {
        setDocuments(docsData.documents || []);
        setTotalDocs(docsData.total || 0);
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [page, limit, searchTerm, statusFilter, typeFilter]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Open full details when a document is clicked
  const handleSelectDocument = async (doc) => {
    try {
      const fullDoc = await getDocument(doc.id);
      setSelectedDocument(fullDoc);
    } catch (err) {
      setSelectedDocument(doc);
    }
  };

  const handleUploadSuccess = (newDoc) => {
    fetchDashboardData();
    if (newDoc) {
      handleSelectDocument(newDoc);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-white">
      {/* Top Navbar */}
      <Navbar
        health={health}
        onRefresh={fetchDashboardData}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8">
        
        {/* Intro banner */}
        <div className="mb-6">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            MSME Sustainability Intelligence Dashboard
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Extract structured energy metrics, Scope 1 & 2 carbon emissions, water/waste circularity, and ESG compliance from PDFs with PyMuPDF, OCR fallback, and AI.
          </p>
        </div>

        {/* Stats KPI Overview Cards */}
        <StatsCards stats={stats} />

        {/* Upload & Sample Generator Section */}
        <DocumentUpload onUploadSuccess={handleUploadSuccess} />

        {/* Document Repository & Extraction Table */}
        <DocumentList
          documents={documents}
          total={totalDocs}
          page={page}
          setPage={setPage}
          limit={limit}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          typeFilter={typeFilter}
          setTypeFilter={setTypeFilter}
          onSelectDocument={handleSelectDocument}
          onRefreshList={fetchDashboardData}
        />

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
        <p>Senseible Document AI &bull; Production-ready MVP &bull; FastAPI + PyMuPDF + Tesseract + OpenAI + React</p>
      </footer>

      {/* Detailed Extraction Modal */}
      {selectedDocument && (
        <DocumentDetailModal
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
        />
      )}
    </div>
  );
}
