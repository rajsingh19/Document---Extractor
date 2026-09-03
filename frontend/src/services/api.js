import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

export const getDocuments = async (params = {}) => {
  const response = await api.get('/documents', { params });
  return response.data;
};

export const getDocument = async (id) => {
  const response = await api.get(`/documents/${id}`);
  return response.data;
};

export const uploadDocument = async (file, autoProcess = true, forceOcr = false, onProgress = null) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/documents/upload', formData, {
    params: { auto_process: autoProcess, force_ocr: forceOcr },
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
  return response.data;
};

export const processDocument = async (id, forceOcr = false) => {
  const response = await api.post(`/documents/${id}/process`, { force_ocr: forceOcr });
  return response.data;
};

export const verifyField = async (id, fieldName) => {
  const response = await api.put(`/documents/${id}/verify-field`, { field_name: fieldName });
  return response.data;
};

export const correctField = async (id, fieldName, correctedValue, unit = null) => {
  const response = await api.put(`/documents/${id}/correct-field`, {
    field_name: fieldName,
    corrected_value: correctedValue,
    unit: unit
  });
  return response.data;
};

export const updateReviewStatus = async (id, reviewStatus) => {
  const response = await api.put(`/documents/${id}/review-status`, { review_status: reviewStatus });
  return response.data;
};

export const getAuditTrail = async (id) => {
  const response = await api.get(`/documents/${id}/audit-trail`);
  return response.data;
};

export const deleteDocument = async (id) => {
  const response = await api.delete(`/documents/${id}`);
  return response.data;
};

export const seedSampleDocument = async (sampleType = 'electricity') => {
  const response = await api.post('/documents/sample-seed', null, {
    params: { sample_type: sampleType },
  });
  return response.data;
};

export const getMetrics = async (params = {}) => {
  const response = await api.get('/metrics', { params });
  return response.data;
};

export const getMetricsSummary = async () => {
  const response = await api.get('/metrics/summary');
  return response.data;
};

export const getMetricsTrends = async (params = {}) => {
  const response = await api.get('/metrics/trends', { params });
  return response.data;
};

export const getMetricsChange = async (params = {}) => {
  const response = await api.get('/metrics/change', { params });
  return response.data;
};

export const normalizeDocument = async (documentId) => {
  const response = await api.post(`/documents/${documentId}/normalize`);
  return response.data;
};

export const updateDocumentClassification = async (documentId, documentType, notes = null) => {
  const response = await api.put(`/documents/${documentId}/classification`, {
    document_type: documentType,
    notes: notes,
  });
  return response.data;
};

export const getInsights = async (params = {}) => {
  const response = await api.get('/insights', { params });
  return response.data;
};

export const askCopilot = async (message, history = [], documentId = null) => {
  const payload = { message, history };
  if (documentId) {
    payload.document_id = documentId;
  }
  const response = await api.post('/copilot/chat', payload);
  return response.data;
};

export const getAttentionItems = async () => {
  const response = await api.get('/copilot/attention');
  return response.data;
};

export const getEvidenceReport = async (documentId) => {
  const response = await api.get(`/documents/${documentId}/evidence-report`);
  return response.data;
};

export const downloadEvidenceReportPDF = async (documentId, filename = null) => {
  const response = await api.get(`/documents/${documentId}/evidence-report/pdf`, {
    responseType: 'blob',
  });
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename || `sustainability_report_doc_${documentId}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const getEmissionFactors = async (params = {}) => {
  const response = await api.get('/emission-factors', { params });
  return response.data;
};

export const getEmissionFactor = async (factorId) => {
  const response = await api.get(`/emission-factors/${factorId}`);
  return response.data;
};

export const findEmissionFactorCandidates = async (params = {}) => {
  const response = await api.get('/emission-factors/candidates', { params });
  return response.data;
};

export const resolveEmissionFactor = async (payload) => {
  const response = await api.post('/emission-factors/resolve', payload);
  return response.data;
};

export const getActivityData = async (params = {}) => {
  const response = await api.get('/activity-data', { params });
  return response.data;
};

export const getActivityDataById = async (activityId) => {
  const response = await api.get(`/activity-data/${activityId}`);
  return response.data;
};

export const getDocumentActivityData = async (documentId) => {
  const response = await api.get(`/documents/${documentId}/activity-data`);
  return response.data;
};

export const previewNormalizeActivity = async (payload) => {
  const response = await api.post('/activity-data/normalize', payload);
  return response.data;
};

export const calculateActivityCarbon = async (activityDataId, forceRecalculate = false) => {
  const response = await api.post('/carbon-calculations/calculate', {
    activity_data_id: activityDataId,
    force_recalculate: forceRecalculate,
  });
  return response.data;
};

export const getCarbonCalculations = async (params = {}) => {
  const response = await api.get('/carbon-calculations', { params });
  return response.data;
};

export const getCarbonCalculationById = async (calcId) => {
  const response = await api.get(`/carbon-calculations/${calcId}`);
  return response.data;
};

export const getDocumentCarbonCalculations = async (documentId) => {
  const response = await api.get(`/documents/${documentId}/carbon-calculations`);
  return response.data;
};

export const calculateDocumentCarbonEmissions = async (documentId) => {
  const response = await api.post(`/documents/${documentId}/carbon-calculations/calculate`);
  return response.data;
};

// ==========================================
// Carbon Accounting Ledger (Step 14)
// ==========================================

export const postCarbonLedgerEntry = async (carbonCalculationId) => {
  const response = await api.post('/carbon-ledger/post', {
    carbon_calculation_id: carbonCalculationId,
  });
  return response.data;
};

export const postDocumentCarbonLedger = async (documentId) => {
  const response = await api.post(`/documents/${documentId}/carbon-ledger/post`);
  return response.data;
};

export const getCarbonLedger = async (params = {}) => {
  const response = await api.get('/carbon-ledger', { params });
  return response.data;
};

export const getCarbonLedgerEntry = async (id) => {
  const response = await api.get(`/carbon-ledger/${id}`);
  return response.data;
};

export const getDocumentCarbonLedger = async (documentId) => {
  const response = await api.get(`/documents/${documentId}/carbon-ledger`);
  return response.data;
};

export const getDocumentCarbonReconciliation = async (documentId) => {
  const response = await api.get(`/documents/${documentId}/carbon-ledger/reconciliation`);
  return response.data;
};

export const getCarbonLedgerSummary = async (params = {}) => {
  const response = await api.get('/carbon-ledger/summary', { params });
  return response.data;
};

// --- Carbon Footprint Dashboard API Methods (Step 15) ---

export const getCarbonDashboard = async (params = {}) => {
  const response = await api.get('/carbon-dashboard', { params });
  return response.data;
};

export const getCarbonDashboardSummary = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/summary', { params });
  return response.data;
};

export const getCarbonDashboardScopes = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/scopes', { params });
  return response.data;
};

export const getCarbonDashboardCategories = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/categories', { params });
  return response.data;
};

export const getCarbonDashboardActivities = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/activities', { params });
  return response.data;
};

export const getCarbonDashboardDocuments = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/documents', { params });
  return response.data;
};

export const getCarbonDashboardTrends = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/trends', { params });
  return response.data;
};

export const getCarbonDashboardCoverage = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/coverage', { params });
  return response.data;
};

export const getCarbonDashboardTopSources = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/top-sources', { params });
  return response.data;
};

export const getCarbonDashboardReconciliation = async (params = {}) => {
  const response = await api.get('/carbon-dashboard/reconciliation', { params });
  return response.data;
};

// --- Carbon Reduction Opportunities API Methods (Step 16) ---

export const getReductionOpportunities = async (params = {}) => {
  const response = await api.get('/reduction-opportunities', { params });
  return response.data;
};

export const getReductionOpportunity = async (id) => {
  const response = await api.get(`/reduction-opportunities/${id}`);
  return response.data;
};

export const getReductionOpportunitySummary = async () => {
  const response = await api.get('/reduction-opportunities/summary');
  return response.data;
};

export const generateReductionOpportunities = async (params = {}) => {
  const response = await api.post('/reduction-opportunities/generate', null, { params });
  return response.data;
};

export const updateReductionOpportunityStatus = async (id, status, note = null) => {
  const response = await api.post(`/reduction-opportunities/${id}/status`, { status, note });
  return response.data;
};

export const createProjectFromOpportunity = async (opportunityId, customData = {}) => {
  const response = await api.post(`/reduction-opportunities/${opportunityId}/create-project`, customData);
  return response.data;
};

// --- Carbon Reduction Projects API Methods (Step 16) ---

export const getReductionProjects = async (params = {}) => {
  const response = await api.get('/reduction-projects', { params });
  return response.data;
};

export const getReductionProject = async (id) => {
  const response = await api.get(`/reduction-projects/${id}`);
  return response.data;
};

export const createReductionProject = async (data) => {
  const response = await api.post('/reduction-projects', data);
  return response.data;
};

export const updateReductionProject = async (id, data) => {
  const response = await api.patch(`/reduction-projects/${id}`, data);
  return response.data;
};

export const updateReductionProjectStatus = async (id, status, note = null) => {
  const response = await api.post(`/reduction-projects/${id}/status`, { status, note });
  return response.data;
};

export default api;




