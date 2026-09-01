import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Documents from './pages/Documents';
import DocumentDetail from './pages/DocumentDetail';
import Metrics from './pages/Metrics';
import { getDocuments, getStats, getHealth, getDocument, seedSampleDocument, deleteDocument, processDocument } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' | 'metrics'
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [loadingActionId, setLoadingActionId] = useState(null);

  const fetchAppData = useCallback(async () => {
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
        }).catch(() => ({ documents: [], total: 0 })),
      ]);

      if (healthData) setHealth(healthData);
      if (statsData) setStats(statsData);
      if (docsData) {
        setDocuments(docsData.documents || []);
        setTotalDocs(docsData.total || 0);
      }
    } catch (err) {
      console.error('Error fetching application data:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [page, limit, searchTerm, statusFilter]);

  useEffect(() => {
    fetchAppData();
  }, [fetchAppData]);

  // Open Document Detail
  const handleSelectDocument = async (doc) => {
    try {
      const fullDoc = await getDocument(doc.id);
      setSelectedDocument(fullDoc);
    } catch (err) {
      setSelectedDocument(doc);
    }
  };

  const handleDocumentUpdated = (updatedDoc) => {
    setSelectedDocument(updatedDoc);
    fetchAppData();
  };

  const handleDocumentDeleted = (deletedId) => {
    setSelectedDocument(null);
    fetchAppData();
  };

  const handleDeleteDocument = async (id) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    setLoadingActionId(id);
    try {
      await deleteDocument(id);
      fetchAppData();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete document.');
    } finally {
      setLoadingActionId(null);
    }
  };

  const handleReprocessDocument = async (id, forceOcr = false) => {
    setLoadingActionId(id);
    try {
      const updated = await processDocument(id, forceOcr);
      fetchAppData();
      if (selectedDocument?.id === id) {
        setSelectedDocument(updated);
      }
    } catch (err) {
      console.error('Reprocess failed:', err);
      alert('Failed to reprocess document.');
    } finally {
      setLoadingActionId(null);
    }
  };

  const handleSeedSample = async (sampleType) => {
    setIsSeeding(true);
    try {
      const result = await seedSampleDocument(sampleType);
      await fetchAppData();
      if (result) {
        handleSelectDocument(result);
      }
    } catch (err) {
      console.error('Sample generation failed:', err);
      alert('Failed to generate sample document.');
    } finally {
      setIsSeeding(false);
    }
  };

  const handleNavTab = (tab) => {
    setSelectedDocument(null);
    setActiveTab(tab);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      
      {/* Top Navbar */}
      <Navbar
        activeTab={selectedDocument ? 'documents' : activeTab}
        onSelectTab={handleNavTab}
        health={health}
        onSeedSample={handleSeedSample}
        isSeeding={isSeeding}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {selectedDocument ? (
          <DocumentDetail
            document={selectedDocument}
            onBack={() => setSelectedDocument(null)}
            onDocumentUpdated={handleDocumentUpdated}
            onDocumentDeleted={handleDocumentDeleted}
          />
        ) : activeTab === 'metrics' ? (
          <Metrics
            stats={stats}
            documents={documents}
            onSelectDocument={handleSelectDocument}
          />
        ) : (
          <Documents
            documents={documents}
            totalDocs={totalDocs}
            page={page}
            setPage={setPage}
            limit={limit}
            setLimit={setLimit}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            onSelectDocument={handleSelectDocument}
            onDeleteDocument={handleDeleteDocument}
            onReprocessDocument={handleReprocessDocument}
            onRefresh={fetchAppData}
            isRefreshing={isRefreshing}
            loadingActionId={loadingActionId}
          />
        )}
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        <p>Senseible Document Extractor &bull; Enterprise Sustainability Intelligence</p>
      </footer>

    </div>
  );
}
