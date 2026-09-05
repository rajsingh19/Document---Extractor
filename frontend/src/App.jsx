import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Documents from './pages/Documents';
import DocumentDetail from './pages/DocumentDetail';
import EvidenceReport from './pages/EvidenceReport';
import EmissionFactors from './pages/EmissionFactors';
import ActivityDataPage from './pages/ActivityData';
import CarbonCalculationsPage from './pages/CarbonCalculations';
import CarbonLedger from './pages/CarbonLedger';
import CarbonDashboard from './pages/CarbonDashboard';
import ReductionOpportunities from './pages/ReductionOpportunities';
import ReductionProjects from './pages/ReductionProjects';
import ComplianceReports from './pages/ComplianceReports';
import ComplianceReportDetail from './pages/ComplianceReportDetail';
import GreenFinance from './pages/GreenFinance';
import GreenFinanceDetail from './pages/GreenFinanceDetail';
import CarbonCredit from './pages/CarbonCredit';
import CarbonCreditDetail from './pages/CarbonCreditDetail';
import EmissionForecastPage from './pages/EmissionForecast';
import ReductionIntelligence from './pages/ReductionIntelligence';
import ReductionRoadmap from './pages/ReductionRoadmap';
import EmissionScenarios from './pages/EmissionScenarios';
import AgentCenter from './pages/AgentCenter';
import IndustryBenchmarking from './pages/IndustryBenchmarking';
import Metrics from './pages/Metrics';

import { getDocuments, getStats, getHealth, getDocument, seedSampleDocument, deleteDocument, processDocument, getAttentionItems } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('documents'); // 'documents' | 'metrics' | 'emission-factors' | 'carbon-ledger' | 'compliance-reports'
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [reportDocId, setReportDocId] = useState(null);
  const [complianceReportId, setComplianceReportId] = useState(null);
  const [greenFinanceAssessmentId, setGreenFinanceAssessmentId] = useState(null);
  const [carbonCreditAssessmentId, setCarbonCreditAssessmentId] = useState(null);

  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [attentionData, setAttentionData] = useState(null);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [loadingActionId, setLoadingActionId] = useState(null);

  // Synchronize route based on URL pathname
  const resolveRoute = useCallback(async (pathname) => {
    const reportMatch = pathname.match(/^\/documents\/(\d+)\/report$/);
    if (reportMatch) {
      const docId = parseInt(reportMatch[1], 10);
      setReportDocId(docId);
      setSelectedDocument(null);
      return;
    }

    const docMatch = pathname.match(/^\/documents\/(\d+)$/);
    if (docMatch) {
      const docId = parseInt(docMatch[1], 10);
      setReportDocId(null);
      setActiveTab('documents');
      try {
        const fullDoc = await getDocument(docId);
        setSelectedDocument(fullDoc);
      } catch (err) {
        console.error('Failed to load document from URL:', err);
      }
      return;
    }

    if (pathname === '/emission-factors') {
      setActiveTab('emission-factors');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/activity-data') {
      setActiveTab('activity-data');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/carbon-calculations') {
      setActiveTab('carbon-calculations');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/carbon-ledger') {
      setActiveTab('carbon-ledger');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/carbon-dashboard') {
      setActiveTab('carbon-dashboard');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/forecast') {
      setActiveTab('forecast');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }


    if (pathname === '/reduction-opportunities') {
      setActiveTab('reduction-opportunities');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/reduction-projects') {
      setActiveTab('reduction-projects');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      return;
    }

    const compMatch = pathname.match(/^\/compliance-reports\/(\d+)$/);
    if (compMatch) {
      const cId = parseInt(compMatch[1], 10);
      setComplianceReportId(cId);
      setActiveTab('compliance-report-detail');
      setSelectedDocument(null);
      setReportDocId(null);
      return;
    }

    if (pathname === '/compliance-reports') {
      setActiveTab('compliance-reports');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      return;
    }

    const gfMatch = pathname.match(/^\/green-finance\/(\d+)$/);
    if (gfMatch) {
      const gfId = parseInt(gfMatch[1], 10);
      setGreenFinanceAssessmentId(gfId);
      setActiveTab('green-finance-detail');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      return;
    }

    if (pathname === '/green-finance') {
      setActiveTab('green-finance');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    const ccaMatch = pathname.match(/^\/carbon-credit\/(\d+)$/);
    if (ccaMatch) {
      const ccaId = parseInt(ccaMatch[1], 10);
      setCarbonCreditAssessmentId(ccaId);
      setActiveTab('carbon-credit-detail');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      return;
    }

    if (pathname === '/carbon-credit') {
      setActiveTab('carbon-credit');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    if (pathname === '/reduction-intelligence') {
      setActiveTab('reduction-intelligence');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    if (pathname === '/reduction-roadmap') {
      setActiveTab('reduction-roadmap');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    if (pathname === '/emission-scenarios') {
      setActiveTab('emission-scenarios');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    if (pathname === '/agent' || pathname === '/ai-agent') {
      setActiveTab('ai-agent');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    if (pathname === '/benchmarks' || pathname === '/industry-benchmarks') {
      setActiveTab('industry-benchmarks');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }

    if (pathname === '/metrics') {

      setActiveTab('metrics');
      setSelectedDocument(null);
      setReportDocId(null);
      setComplianceReportId(null);
      setGreenFinanceAssessmentId(null);
      setCarbonCreditAssessmentId(null);
      return;
    }


    // Default fallback to /documents
    setActiveTab('documents');
    setSelectedDocument(null);
    setReportDocId(null);
    if (pathname === '/ai-copilot' || pathname === '/' || pathname === '') {
      window.history.replaceState(null, '', '/documents');
    }
  }, []);

  useEffect(() => {
    resolveRoute(window.location.pathname);

    const handlePopState = () => {
      resolveRoute(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [resolveRoute]);

  const fetchAppData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const [healthData, statsData, docsData, attData] = await Promise.all([
        getHealth().catch(() => null),
        getStats().catch(() => null),
        getDocuments({
          page,
          limit,
          search: searchTerm || undefined,
          status: statusFilter || undefined,
        }).catch(() => ({ documents: [], total: 0 })),
        getAttentionItems().catch(() => null),
      ]);

      if (healthData) setHealth(healthData);
      if (statsData) setStats(statsData);
      if (attData) setAttentionData(attData);
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
      window.history.pushState(null, '', `/documents/${doc.id}`);
    } catch (err) {
      setSelectedDocument(doc);
      window.history.pushState(null, '', `/documents/${doc.id}`);
    }
  };

  const handleBackFromDocument = () => {
    setSelectedDocument(null);
    window.history.pushState(null, '', '/documents');
  };

  const handleDocumentUpdated = (updatedDoc) => {
    setSelectedDocument(updatedDoc);
    fetchAppData();
  };

  const handleDocumentDeleted = (deletedId) => {
    setSelectedDocument(null);
    window.history.pushState(null, '', '/documents');
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
    if (tab === 'ai-agent') {
      window.history.pushState(null, '', '/agent');
    } else if (tab === 'industry-benchmarks') {
      window.history.pushState(null, '', '/benchmarks');
    } else {
      window.history.pushState(null, '', `/${tab}`);
    }
  };

  const handleNavigate = (dest) => {
    if (!dest) return;
    if (dest.startsWith('/')) {
      window.history.pushState(null, '', dest);
      resolveRoute(dest);
    } else {
      handleNavTab(dest);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      
      {/* Top Navbar */}
      <Navbar
        activeTab={reportDocId || selectedDocument ? 'documents' : activeTab}
        onSelectTab={handleNavTab}
        health={health}
        onSeedSample={handleSeedSample}
        isSeeding={isSeeding}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {reportDocId ? (
          <EvidenceReport
            documentId={reportDocId}
            onBack={() => {
              const id = reportDocId;
              setReportDocId(null);
              window.history.pushState(null, '', `/documents/${id}`);
              handleSelectDocument({ id });
            }}
            onNavigateToDocument={(id) => {
              setReportDocId(null);
              window.history.pushState(null, '', `/documents/${id}`);
              handleSelectDocument({ id });
            }}
          />
        ) : selectedDocument ? (
          <DocumentDetail
            document={selectedDocument}
            onBack={handleBackFromDocument}
            onDocumentUpdated={handleDocumentUpdated}
            onDocumentDeleted={handleDocumentDeleted}
            onViewReport={(id) => {
              setReportDocId(id);
              window.history.pushState(null, '', `/documents/${id}/report`);
            }}
          />
        ) : activeTab === 'emission-factors' ? (
          <EmissionFactors />
        ) : activeTab === 'activity-data' ? (
          <ActivityDataPage />
        ) : activeTab === 'carbon-calculations' ? (
          <CarbonCalculationsPage />
        ) : activeTab === 'carbon-ledger' ? (
          <CarbonLedger />
        ) : activeTab === 'carbon-dashboard' ? (
          <CarbonDashboard onNavigate={handleNavigate} />
        ) : activeTab === 'reduction-opportunities' ? (
          <ReductionOpportunities />
        ) : activeTab === 'reduction-projects' ? (
          <ReductionProjects />
        ) : activeTab === 'compliance-reports' ? (
          <ComplianceReports
            onNavigate={(tab, repId) => {
              if (repId) {
                setComplianceReportId(repId);
                setActiveTab('compliance-report-detail');
                window.history.pushState(null, '', `/compliance-reports/${repId}`);
              } else {
                setActiveTab(tab);
                window.history.pushState(null, '', `/${tab}`);
              }
            }}
          />
        ) : activeTab === 'compliance-report-detail' ? (
          <ComplianceReportDetail
            reportId={complianceReportId}
            onNavigate={(tab) => {
              setActiveTab('compliance-reports');
              setComplianceReportId(null);
              window.history.pushState(null, '', '/compliance-reports');
            }}
          />
        ) : activeTab === 'green-finance' ? (
          <GreenFinance
            onNavigate={(tab, gfId) => {
              if (gfId) {
                setGreenFinanceAssessmentId(gfId);
                setActiveTab('green-finance-detail');
                window.history.pushState(null, '', `/green-finance/${gfId}`);
              } else {
                setActiveTab(tab);
                window.history.pushState(null, '', `/${tab}`);
              }
            }}
          />
        ) : activeTab === 'green-finance-detail' ? (
          <GreenFinanceDetail
            assessmentId={greenFinanceAssessmentId}
            onNavigate={(tab) => {
              setActiveTab('green-finance');
              setGreenFinanceAssessmentId(null);
              window.history.pushState(null, '', '/green-finance');
            }}
          />
        ) : activeTab === 'carbon-credit' ? (
          <CarbonCredit
            onNavigate={(tab, ccaId) => {
              if (ccaId) {
                setCarbonCreditAssessmentId(ccaId);
                setActiveTab('carbon-credit-detail');
                window.history.pushState(null, '', `/carbon-credit/${ccaId}`);
              } else {
                setActiveTab(tab);
                window.history.pushState(null, '', `/${tab}`);
              }
            }}
          />
        ) : activeTab === 'carbon-credit-detail' ? (
          <CarbonCreditDetail
            assessmentId={carbonCreditAssessmentId}
            onNavigate={(tab) => {
              setActiveTab('carbon-credit');
              setCarbonCreditAssessmentId(null);
              window.history.pushState(null, '', '/carbon-credit');
            }}
          />
        ) : activeTab === 'forecast' ? (
          <EmissionForecastPage />
        ) : activeTab === 'reduction-intelligence' ? (
          <ReductionIntelligence
            onSelectDocument={handleSelectDocument}
            onSelectOpportunity={(oppId) => {
              setActiveTab('reduction-opportunities');
              window.history.pushState(null, '', '/reduction-opportunities');
            }}
          />
        ) : activeTab === 'reduction-roadmap' ? (
          <ReductionRoadmap
            onSelectDocument={handleSelectDocument}
          />
        ) : activeTab === 'emission-scenarios' ? (
          <EmissionScenarios />
        ) : activeTab === 'industry-benchmarks' ? (
          <IndustryBenchmarking
            onSelectDocument={handleSelectDocument}
          />
        ) : activeTab === 'ai-agent' ? (
          <AgentCenter
            onSelectDocument={handleSelectDocument}
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
