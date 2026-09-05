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

// --- Carbon Reduction Project Measurement & Verification API Methods (Step 17) ---

export const createReductionMeasurement = async (projectId, data) => {
  const response = await api.post(`/reduction-projects/${projectId}/measurements`, data);
  return response.data;
};

export const getReductionMeasurements = async (projectId) => {
  const response = await api.get(`/reduction-projects/${projectId}/measurements`);
  return response.data;
};

export const getReductionMeasurement = async (measurementId) => {
  const response = await api.get(`/reduction-measurements/${measurementId}`);
  return response.data;
};

export const calculateReductionMeasurement = async (measurementId, documentId = null) => {
  const response = await api.post(`/reduction-measurements/${measurementId}/calculate`, null, {
    params: documentId ? { document_id: documentId } : {}
  });
  return response.data;
};

export const updateReductionMeasurementStatus = async (measurementId, status, note = null) => {
  const response = await api.post(`/reduction-measurements/${measurementId}/status`, { status, note });
  return response.data;
};

export const submitVerificationRecord = async (measurementId, data) => {
  const response = await api.post(`/reduction-measurements/${measurementId}/verification`, data);
  return response.data;
};

export const getVerificationRecord = async (measurementId) => {
  const response = await api.get(`/reduction-measurements/${measurementId}/verification`);
  return response.data;
};

export const updateVerificationStatus = async (measurementId, data) => {
  const response = await api.post(`/reduction-measurements/${measurementId}/verification/status`, data);
  return response.data;
};

// --- Compliance & Sustainability Report Builder API Methods (Step 18) ---

export const getComplianceFrameworks = async () => {
  const response = await api.get('/compliance-frameworks');
  return response.data;
};

export const getComplianceFramework = async (framework) => {
  const response = await api.get(`/compliance-frameworks/${framework}`);
  return response.data;
};

export const createComplianceReport = async (data) => {
  const response = await api.post('/compliance-reports', data);
  return response.data;
};

export const getComplianceReports = async (params = {}) => {
  const response = await api.get('/compliance-reports', { params });
  return response.data;
};

export const getComplianceReport = async (reportId) => {
  const response = await api.get(`/compliance-reports/${reportId}`);
  return response.data;
};

export const generateComplianceReport = async (reportId) => {
  const response = await api.post(`/compliance-reports/${reportId}/generate`);
  return response.data;
};

export const updateComplianceReportStatus = async (reportId, status, assuranceStatus = null, note = null) => {
  const response = await api.post(`/compliance-reports/${reportId}/status`, {
    status,
    assurance_status: assuranceStatus,
    note
  });
  return response.data;
};

export const getComplianceReportSections = async (reportId) => {
  const response = await api.get(`/compliance-reports/${reportId}/sections`);
  return response.data;
};

export const getComplianceReportDisclosures = async (reportId, sectionId = null) => {
  const response = await api.get(`/compliance-reports/${reportId}/disclosures`, {
    params: sectionId ? { section_id: sectionId } : {}
  });
  return response.data;
};

export const updateDisclosureUserValue = async (disclosureId, value, valueUnit = null, notes = null) => {
  const response = await api.post(`/compliance-disclosures/${disclosureId}/user-value`, {
    value,
    value_unit: valueUnit,
    notes
  });
  return response.data;
};

export const getComplianceReportPdfUrl = (reportId) => {
  return `/api/compliance-reports/${reportId}/pdf`;
};

// --- Green Finance / Green Loan Readiness Engine API Methods (Step 19) ---

export const getGreenFinanceFramework = async () => {
  const response = await api.get('/green-finance/framework');
  return response.data;
};

export const getGreenFinanceRequirements = async () => {
  const response = await api.get('/green-finance/requirements');
  return response.data;
};

export const createGreenFinanceAssessment = async (data) => {
  const response = await api.post('/green-finance/assessments', data);
  return response.data;
};

export const getGreenFinanceAssessments = async (params = {}) => {
  const response = await api.get('/green-finance/assessments', { params });
  return response.data;
};

export const getGreenFinanceAssessment = async (assessmentId) => {
  const response = await api.get(`/green-finance/assessments/${assessmentId}`);
  return response.data;
};

export const generateGreenFinanceAssessment = async (assessmentId) => {
  const response = await api.post(`/green-finance/assessments/${assessmentId}/generate`);
  return response.data;
};

export const updateGreenFinanceAssessmentStatus = async (assessmentId, status, notes = null) => {
  const response = await api.post(`/green-finance/assessments/${assessmentId}/status`, { status, notes });
  return response.data;
};

export const finalizeGreenFinanceAssessment = async (assessmentId) => {
  const response = await api.post(`/green-finance/assessments/${assessmentId}/finalize`);
  return response.data;
};

export const getGreenFinanceAssessmentPdfUrl = (assessmentId) => {
  return `/api/green-finance/assessments/${assessmentId}/pdf`;
};

// --- Carbon Credit Readiness & Project Eligibility Assessment API Methods (Step 20) ---

export const getCarbonCreditFramework = async () => {
  const response = await api.get('/carbon-credit/framework');
  return response.data;
};

export const getCarbonCreditRequirements = async () => {
  const response = await api.get('/carbon-credit/requirements');
  return response.data;
};

export const createCarbonCreditAssessment = async (data) => {
  const response = await api.post('/carbon-credit/assessments', data);
  return response.data;
};

export const getCarbonCreditAssessments = async (params = {}) => {
  const response = await api.get('/carbon-credit/assessments', { params });
  return response.data;
};

export const getCarbonCreditAssessment = async (assessmentId) => {
  const response = await api.get(`/carbon-credit/assessments/${assessmentId}`);
  return response.data;
};

export const generateCarbonCreditAssessment = async (assessmentId) => {
  const response = await api.post(`/carbon-credit/assessments/${assessmentId}/generate`);
  return response.data;
};

export const updateCarbonCreditAssessmentStatus = async (assessmentId, status, notes = null) => {
  const response = await api.post(`/carbon-credit/assessments/${assessmentId}/status`, { status, notes });
  return response.data;
};

export const finalizeCarbonCreditAssessment = async (assessmentId) => {
  const response = await api.post(`/carbon-credit/assessments/${assessmentId}/finalize`);
  return response.data;
};

export const getCarbonCreditRequirementsList = async (assessmentId) => {
  const response = await api.get(`/carbon-credit/assessments/${assessmentId}/requirements`);
  return response.data;
};

export const getCarbonCreditEvidence = async (assessmentId) => {
  const response = await api.get(`/carbon-credit/assessments/${assessmentId}/evidence`);
  return response.data;
};

export const getCarbonCreditActions = async (assessmentId) => {
  const response = await api.get(`/carbon-credit/assessments/${assessmentId}/actions`);
  return response.data;
};

export const getCarbonCreditChecklist = async (assessmentId) => {
  const response = await api.get(`/carbon-credit/assessments/${assessmentId}/checklist`);
  return response.data;
};

export const getCarbonCreditMethodology = async (assessmentId) => {
  const response = await api.get(`/carbon-credit/assessments/${assessmentId}/methodology`);
  return response.data;
};

export const getCarbonCreditAssessmentPdfUrl = (assessmentId) => {
  return `/api/carbon-credit/assessments/${assessmentId}/pdf`;
};

// ============================================================================
// STEP 21: EMISSION FORECASTING API SERVICES
// ============================================================================

export const getEmissionsForecast = async (params = {}) => {
  const response = await api.get('/emissions/forecast', { params });
  return response.data;
};

export const createEmissionsForecast = async (data) => {
  const response = await api.post('/emissions/forecast', data);
  return response.data;
};

export const getForecastModels = async () => {
  const response = await api.get('/emissions/forecast/models');
  return response.data;
};

export const getForecastDataQuality = async (params = {}) => {
  const response = await api.get('/emissions/forecast/data-quality', { params });
  return response.data;
};

export const getForecastBacktest = async (params = {}) => {
  const response = await api.get('/emissions/forecast/backtest', { params });
  return response.data;
};

export const getForecastHistory = async (limit = 20) => {
  const response = await api.get('/emissions/forecast/history', { params: { limit } });
  return response.data;
};

export const getForecastById = async (forecastId) => {
  const response = await api.get(`/emissions/forecast/${forecastId}`);
  return response.data;
};

// ============================================================================
// STEP 22A: REDUCTION OPPORTUNITY INTELLIGENCE API SERVICES
// ============================================================================

export const getReductionIntelligencePriorities = async (params = {}) => {
  const response = await api.get('/reduction-intelligence', { params });
  return response.data;
};

export const getReductionIntelligenceSummary = async (params = {}) => {
  const response = await api.get('/reduction-intelligence/summary', { params });
  return response.data;
};

export const getReductionIntelligenceById = async (priorityId) => {
  const response = await api.get(`/reduction-intelligence/${priorityId}`);
  return response.data;
};

export const getDocumentReductionIntelligence = async (documentId) => {
  const response = await api.get(`/reduction-intelligence/document/${documentId}`);
  return response.data;
};

export const recalculateReductionIntelligence = async (documentId = null) => {
  const params = documentId ? { document_id: documentId } : {};
  const response = await api.post('/reduction-intelligence/recalculate', null, { params });
  return response.data;
};

// ============================================================================
// STEP 22B: PERSONALIZED EMISSIONS REDUCTION ROADMAP API SERVICES
// ============================================================================

export const getReductionRoadmaps = async (params = {}) => {
  const response = await api.get('/reduction-roadmaps', { params });
  return response.data;
};

export const getReductionRoadmapById = async (roadmapId) => {
  const response = await api.get(`/reduction-roadmaps/${roadmapId}`);
  return response.data;
};

export const createReductionRoadmap = async (data) => {
  const response = await api.post('/reduction-roadmaps', data);
  return response.data;
};

export const regenerateReductionRoadmap = async (roadmapId) => {
  const response = await api.post(`/reduction-roadmaps/${roadmapId}/generate`);
  return response.data;
};

export const getReductionRoadmapProgress = async (roadmapId) => {
  const response = await api.get(`/reduction-roadmaps/${roadmapId}/progress`);
  return response.data;
};

export const updateReductionRoadmap = async (roadmapId, data) => {
  const response = await api.patch(`/reduction-roadmaps/${roadmapId}`, data);
  return response.data;
};

export const updateReductionRoadmapItemStatus = async (roadmapId, itemId, data) => {
  const response = await api.patch(`/reduction-roadmaps/${roadmapId}/items/${itemId}`, data);
  return response.data;
};

export const getReductionRoadmapEvents = async (roadmapId) => {
  const response = await api.get(`/reduction-roadmaps/${roadmapId}/events`);
  return response.data;
};

// --- Emission Scenarios & What-If Analysis API Methods (Step 22C) ---

export const getEmissionScenarios = async (params = {}) => {
  const response = await api.get('/emission-scenarios', { params });
  return response.data;
};

export const getDocumentEmissionScenarios = async (documentId, params = {}) => {
  const response = await api.get(`/emission-scenarios/document/${documentId}`, { params });
  return response.data;
};

export const getEmissionScenario = async (scenarioId) => {
  const response = await api.get(`/emission-scenarios/${scenarioId}`);
  return response.data;
};

export const createEmissionScenario = async (data) => {
  const response = await api.post('/emission-scenarios', data);
  return response.data;
};

export const recalculateEmissionScenario = async (scenarioId) => {
  const response = await api.post(`/emission-scenarios/${scenarioId}/calculate`);
  return response.data;
};

export const getScenarioResults = async (scenarioId) => {
  const response = await api.get(`/emission-scenarios/${scenarioId}/results`);
  return response.data;
};

export const updateEmissionScenario = async (scenarioId, data) => {
  const response = await api.patch(`/emission-scenarios/${scenarioId}`, data);
  return response.data;
};

export const archiveEmissionScenario = async (scenarioId) => {
  const response = await api.delete(`/emission-scenarios/${scenarioId}`);
  return response.data;
};

// --- Proactive AI Sustainability Agent API Methods (Step 23) ---

export const getAgentBrief = async (params = {}) => {
  const response = await api.get('/agent/brief', { params });
  return response.data;
};

export const runAgent = async (data = {}) => {
  const response = await api.post('/agent/run', data);
  return response.data;
};

export const getAgentStatus = async () => {
  const response = await api.get('/agent/status');
  return response.data;
};

export const getAgentActions = async (params = {}) => {
  const response = await api.get('/agent/actions', { params });
  return response.data;
};

export const getAgentAction = async (actionId) => {
  const response = await api.get(`/agent/actions/${actionId}`);
  return response.data;
};

export const patchAgentAction = async (actionId, data) => {
  const response = await api.patch(`/agent/actions/${actionId}`, data);
  return response.data;
};

export const startAgentAction = async (actionId, reason = null) => {
  const response = await api.post(`/agent/actions/${actionId}/start`, null, { params: reason ? { reason } : {} });
  return response.data;
};

export const completeAgentAction = async (actionId, reason = null) => {
  const response = await api.post(`/agent/actions/${actionId}/complete`, null, { params: reason ? { reason } : {} });
  return response.data;
};

export const dismissAgentAction = async (actionId, reason = null) => {
  const response = await api.post(`/agent/actions/${actionId}/dismiss`, null, { params: reason ? { reason } : {} });
  return response.data;
};

export const getAgentActionEvents = async (actionId) => {
  const response = await api.get(`/agent/actions/${actionId}/events`);
  return response.data;
};

export const explainAgentAction = async (actionId) => {
  const response = await api.post(`/agent/explain/${actionId}`);
  return response.data;
};

export const getAgentActionExplanation = explainAgentAction;

// ===========================================================================
// STEP 24 — INDUSTRY BENCHMARKING & INTELLIGENCE API CLIENT
// ===========================================================================

export const getBusinessProfile = async () => {
  const response = await api.get('/benchmarks/profile');
  return response.data;
};

export const updateBusinessProfile = async (profileData) => {
  const response = await api.put('/benchmarks/profile', profileData);
  return response.data;
};

export const getBenchmarkEligibility = async (params = {}) => {
  const response = await api.get('/benchmarks/eligibility', { params });
  return response.data;
};

export const evaluateBenchmarks = async (data = {}, params = {}) => {
  const response = await api.post('/benchmarks/evaluate', data, { params });
  return response.data;
};

export const recalculateBenchmarks = async (params = {}) => {
  const response = await api.post('/benchmarks/recalculate', null, { params });
  return response.data;
};

export const getBenchmarks = async (params = {}) => {
  const response = await api.get('/benchmarks', { params });
  return response.data;
};

export const getBenchmarkDetail = async (benchmarkId) => {
  const response = await api.get(`/benchmarks/${benchmarkId}`);
  return response.data;
};

export const getBenchmarkSummary = async (params = {}) => {
  const response = await api.get('/benchmarks/summary', { params });
  return response.data;
};

export const getBenchmarkComparisons = async (params = {}) => {
  const response = await api.get('/benchmarks/comparisons', { params });
  return response.data;
};

export const getBenchmarkComparisonDetail = async (comparisonId) => {
  const response = await api.get(`/benchmarks/comparisons/${comparisonId}`);
  return response.data;
};

export const getBenchmarkInsights = async (params = {}) => {
  const response = await api.get('/benchmarks/insights', { params });
  return response.data;
};

export const getBenchmarkDataQuality = async () => {
  const response = await api.get('/benchmarks/data-quality');
  return response.data;
};

export const getBenchmarkSources = async (params = {}) => {
  const response = await api.get('/benchmarks/sources', { params });
  return response.data;
};

export const getBenchmarkHistory = async (params = {}) => {
  const response = await api.get('/benchmarks/history', { params });
  return response.data;
};

export default api;
