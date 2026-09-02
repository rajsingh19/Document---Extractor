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

export default api;



