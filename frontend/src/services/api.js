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

export default api;
