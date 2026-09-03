import React, { useState, useEffect } from 'react';
import { 
  FolderKanban, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  PlusCircle, 
  Calendar, 
  User, 
  Layers, 
  Tag, 
  RefreshCw, 
  History, 
  ChevronRight,
  TrendingDown,
  Info,
  BarChart3,
  ShieldCheck,
  FileCheck,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';
import { 
  getReductionProjects, 
  createReductionProject, 
  updateReductionProjectStatus, 
  updateReductionProject,
  getReductionMeasurements,
  createReductionMeasurement,
  calculateReductionMeasurement,
  updateReductionMeasurementStatus,
  submitVerificationRecord,
  getVerificationRecord,
  updateVerificationStatus
} from '../services/api';

export default function ReductionProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  // Project Detail & Audit
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectMeasurements, setProjectMeasurements] = useState([]);
  const [loadingMeasurements, setLoadingMeasurements] = useState(false);

  // Status Update Modal
  const [statusModal, setStatusModal] = useState(null);
  const [newStatus, setNewStatus] = useState('IN_PROGRESS');
  const [statusNote, setStatusNote] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Create Project Modal
  const [createModal, setCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: '',
    description: '',
    category: 'ENERGY',
    scope: 'SCOPE_2',
    owner: '',
    target_description: '',
    notes: '',
  });
  const [creating, setCreating] = useState(false);

  // Step 17: Measurement Flow Modal
  const [measurementModal, setMeasurementModal] = useState(null);
  const [measurementForm, setMeasurementForm] = useState({
    reference_period: '2024-10',
    measurement_period: '2025-10',
    measurement_scope_type: 'TOTAL',
    measurement_scope: '',
    measurement_category: '',
    measurement_activity_type: '',
  });
  const [calculatingMeasurement, setCalculatingMeasurement] = useState(false);
  const [measurementResult, setMeasurementResult] = useState(null);

  // Step 17: Verification Modal
  const [verificationModal, setVerificationModal] = useState(null);
  const [verificationForm, setVerificationForm] = useState({
    verification_status: 'INTERNAL_REVIEW',
    verifier_name: '',
    verifier_organization: '',
    verification_reference: '',
    verification_date: '',
    verification_notes: '',
  });
  const [submittingVerification, setSubmittingVerification] = useState(false);
  const [verificationError, setVerificationError] = useState(null);

  useEffect(() => {
    loadProjects();
  }, [statusFilter, categoryFilter]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (categoryFilter) params.category = categoryFilter;

      const data = await getReductionProjects(params);
      setProjects(data.items || []);
    } catch (err) {
      console.error("Failed to load reduction projects:", err);
      setError("Unable to load reduction projects.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectProject = async (prj) => {
    setSelectedProject(prj);
    if (prj) {
      try {
        setLoadingMeasurements(true);
        const data = await getReductionMeasurements(prj.id);
        setProjectMeasurements(data.items || []);
      } catch (err) {
        console.error("Failed to load measurements:", err);
        setProjectMeasurements([]);
      } finally {
        setLoadingMeasurements(false);
      }
    }
  };

  const handleStatusUpdate = async (e) => {
    e.preventDefault();
    if (!statusModal) return;
    try {
      setUpdatingStatus(true);
      await updateReductionProjectStatus(statusModal.id, newStatus, statusNote || null);
      setStatusModal(null);
      loadProjects();
      if (selectedProject && selectedProject.id === statusModal.id) {
        handleSelectProject(statusModal);
      }
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    try {
      setCreating(true);
      await createReductionProject(createForm);
      setCreateModal(false);
      setCreateForm({
        title: '',
        description: '',
        category: 'ENERGY',
        scope: 'SCOPE_2',
        owner: '',
        target_description: '',
        notes: '',
      });
      loadProjects();
    } catch (err) {
      console.error("Failed to create project:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleRunMeasurement = async (e) => {
    e.preventDefault();
    if (!measurementModal) return;
    try {
      setCalculatingMeasurement(true);
      setMeasurementResult(null);

      // 1. Create measurement record
      const meas = await createReductionMeasurement(measurementModal.id, measurementForm);
      // 2. Calculate observed comparison
      const result = await calculateReductionMeasurement(meas.id);
      setMeasurementResult(result);

      // Refresh measurements list for project
      if (selectedProject && selectedProject.id === measurementModal.id) {
        handleSelectProject(selectedProject);
      }
    } catch (err) {
      console.error("Measurement calculation failed:", err);
      setMeasurementResult({
        is_comparable: false,
        reason: err.response?.data?.detail || "Failed to compute measurement comparison."
      });
    } finally {
      setCalculatingMeasurement(false);
    }
  };

  const handleOpenVerificationModal = async (meas) => {
    try {
      setVerificationError(null);
      const rec = await getVerificationRecord(meas.id);
      setVerificationForm({
        verification_status: rec.verification_status || 'INTERNAL_REVIEW',
        verifier_name: rec.verifier_name || '',
        verifier_organization: rec.verifier_organization || '',
        verification_reference: rec.verification_reference || '',
        verification_date: rec.verification_date ? rec.verification_date.split('T')[0] : '',
        verification_notes: rec.verification_notes || '',
      });
      setVerificationModal(meas);
    } catch (err) {
      console.error("Failed to load verification record:", err);
    }
  };

  const handleSaveVerification = async (e) => {
    e.preventDefault();
    if (!verificationModal) return;
    try {
      setSubmittingVerification(true);
      setVerificationError(null);

      const payload = {
        verification_status: verificationForm.verification_status,
        verifier_name: verificationForm.verifier_name || null,
        verifier_organization: verificationForm.verifier_organization || null,
        verification_reference: verificationForm.verification_reference || null,
        verification_date: verificationForm.verification_date ? new Date(verificationForm.verification_date).toISOString() : null,
        verification_notes: verificationForm.verification_notes || null,
      };

      await updateVerificationStatus(verificationModal.id, payload);
      setVerificationModal(null);

      if (selectedProject) {
        handleSelectProject(selectedProject);
      }
    } catch (err) {
      console.error("Verification update failed:", err);
      setVerificationError(err.response?.data?.detail || "Failed to update verification status.");
    } finally {
      setSubmittingVerification(false);
    }
  };

  const getStatusBadge = (st) => {
    switch (st) {
      case 'PLANNED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">PLANNED</span>;
      case 'IN_PROGRESS':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">IN PROGRESS</span>;
      case 'ON_HOLD':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">ON HOLD</span>;
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">COMPLETED</span>;
      case 'CANCELLED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">CANCELLED</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">{st}</span>;
    }
  };

  const getVerificationBadge = (vst) => {
    switch (vst) {
      case 'NOT_SUBMITTED':
        return <span className="px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 rounded">Not Submitted</span>;
      case 'INTERNAL_REVIEW':
        return <span className="px-2 py-0.5 text-xs font-medium bg-blue-50 text-blue-700 rounded border border-blue-200">Internal Review</span>;
      case 'ACCEPTED':
        return <span className="px-2 py-0.5 text-xs font-medium bg-emerald-50 text-emerald-700 rounded border border-emerald-200">Accepted</span>;
      case 'REJECTED':
        return <span className="px-2 py-0.5 text-xs font-medium bg-rose-50 text-rose-700 rounded border border-rose-200">Rejected</span>;
      case 'EXTERNAL_VERIFICATION_PENDING':
        return <span className="px-2 py-0.5 text-xs font-medium bg-amber-50 text-amber-800 rounded border border-amber-200">External Verification Pending</span>;
      case 'EXTERNALLY_VERIFIED':
        return <span className="px-2 py-0.5 text-xs font-semibold bg-purple-50 text-purple-700 rounded border border-purple-200 flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-purple-600" /> Externally Verified
        </span>;
      default:
        return <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">{vst}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <FolderKanban className="w-7 h-7 text-emerald-600" />
              Reduction Project Measurement & Verification
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Track business reduction projects and measure observed accounting changes between reference and post-implementation periods.
            </p>
          </div>
          <button
            onClick={() => setCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-xl shadow-sm transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            New Reduction Project
          </button>
        </div>

        {/* FILTERS */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Statuses</option>
              <option value="PLANNED">Planned</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="ON_HOLD">On Hold</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Categories</option>
              <option value="ENERGY">Energy</option>
              <option value="FUEL">Fuel</option>
              <option value="TRANSPORT">Transport</option>
              <option value="DATA_QUALITY">Data Quality</option>
            </select>

            {(statusFilter || categoryFilter) && (
              <button
                onClick={() => { setStatusFilter(''); setCategoryFilter(''); }}
                className="text-xs text-rose-600 hover:text-rose-700 font-medium ml-auto"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* PROJECTS LIST */}
        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
            Loading reduction projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <FolderKanban className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-medium text-slate-800">No reduction projects found.</p>
            <p className="text-xs text-slate-400 mt-1">Create a project from the Reduction Opportunities page or click "New Reduction Project" above.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((prj) => (
              <div
                key={prj.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all p-5"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {prj.project_code}
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {prj.category}
                      </span>
                      {prj.scope && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {prj.scope}
                        </span>
                      )}
                      {getStatusBadge(prj.status)}
                    </div>

                    <div>
                      <h3 
                        onClick={() => handleSelectProject(prj)}
                        className="text-base font-semibold text-slate-900 hover:text-emerald-700 transition-colors cursor-pointer"
                      >
                        {prj.title}
                      </h3>
                      {prj.target_description && (
                        <p className="text-sm text-slate-600 mt-0.5">{prj.target_description}</p>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                      {prj.owner && (
                        <span className="flex items-center gap-1">
                          <User className="w-3.5 h-3.5 text-slate-400" />
                          Owner: <strong className="text-slate-700">{prj.owner}</strong>
                        </span>
                      )}
                      {prj.baseline_co2e_t !== null && prj.baseline_co2e_t !== undefined && (
                        <span className="bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                          Reference Footprint: <strong>{prj.baseline_co2e_t.toFixed(4)} tCO2e</strong>
                        </span>
                      )}
                      {prj.opportunity_id && (
                        <span className="bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-emerald-800">
                          Linked to Opportunity #{prj.opportunity_id}
                        </span>
                      )}
                      <span className="text-slate-400">
                        Created {new Date(prj.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  {/* ACTIONS */}
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => setMeasurementModal(prj)}
                      className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-lg border border-emerald-200 transition-colors flex items-center gap-1"
                    >
                      <BarChart3 className="w-3.5 h-3.5 text-emerald-600" />
                      Measure Results
                    </button>
                    <button
                      onClick={() => {
                        setStatusModal(prj);
                        setNewStatus(prj.status);
                        setStatusNote('');
                      }}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg border border-slate-200 transition-colors"
                    >
                      Update Status
                    </button>
                    <button
                      onClick={() => handleSelectProject(prj)}
                      className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium rounded-lg transition-colors"
                    >
                      Details & Audit
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* STATUS UPDATE MODAL */}
        {statusModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">Update Project Status</h3>
                <button
                  onClick={() => setStatusModal(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleStatusUpdate} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="PLANNED">PLANNED</option>
                    <option value="IN_PROGRESS">IN_PROGRESS</option>
                    <option value="ON_HOLD">ON_HOLD</option>
                    <option value="COMPLETED">COMPLETED</option>
                    <option value="CANCELLED">CANCELLED</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Status Change Note / Milestone</label>
                  <textarea
                    rows={3}
                    placeholder="Describe progress or milestone achieved..."
                    value={statusNote}
                    onChange={(e) => setStatusNote(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setStatusModal(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updatingStatus}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {updatingStatus ? 'Updating...' : 'Record Status Change'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* STEP 17: MEASURE RESULTS MODAL */}
        {measurementModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto shadow-xl border border-slate-200 p-6 space-y-5">
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                    Step 17 Measurement Engine
                  </span>
                  <h2 className="text-xl font-bold text-slate-900 mt-1">
                    Measure Observed Accounting Changes
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {measurementModal.title}
                  </p>
                </div>
                <button
                  onClick={() => { setMeasurementModal(null); setMeasurementResult(null); }}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
                >
                  ✕
                </button>
              </div>

              {!measurementResult ? (
                <form onSubmit={handleRunMeasurement} className="space-y-4 text-sm">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Reference Period</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. 2024-10"
                        value={measurementForm.reference_period}
                        onChange={(e) => setMeasurementForm(prev => ({ ...prev, reference_period: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Measurement Period</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. 2025-10"
                        value={measurementForm.measurement_period}
                        onChange={(e) => setMeasurementForm(prev => ({ ...prev, measurement_period: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Measurement Scope Type</label>
                    <select
                      value={measurementForm.measurement_scope_type}
                      onChange={(e) => setMeasurementForm(prev => ({ ...prev, measurement_scope_type: e.target.value }))}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="TOTAL">TOTAL (All Scopes)</option>
                      <option value="SCOPE">SCOPE (Scope 1 / Scope 2 / Scope 3)</option>
                      <option value="CATEGORY">CATEGORY (Energy, Fuel, etc.)</option>
                      <option value="ACTIVITY">ACTIVITY TYPE (purchased_electricity, diesel, etc.)</option>
                    </select>
                  </div>

                  {measurementForm.measurement_scope_type === 'SCOPE' && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Target Scope</label>
                      <select
                        value={measurementForm.measurement_scope}
                        onChange={(e) => setMeasurementForm(prev => ({ ...prev, measurement_scope: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        <option value="">Select Scope...</option>
                        <option value="SCOPE_1">SCOPE 1</option>
                        <option value="SCOPE_2">SCOPE 2</option>
                        <option value="SCOPE_3">SCOPE 3</option>
                      </select>
                    </div>
                  )}

                  {measurementForm.measurement_scope_type === 'CATEGORY' && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Target Category</label>
                      <input
                        type="text"
                        placeholder="e.g. ENERGY, FUEL"
                        value={measurementForm.measurement_category}
                        onChange={(e) => setMeasurementForm(prev => ({ ...prev, measurement_category: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  )}

                  {measurementForm.measurement_scope_type === 'ACTIVITY' && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Activity Type</label>
                      <input
                        type="text"
                        placeholder="e.g. purchased_electricity, diesel"
                        value={measurementForm.measurement_activity_type}
                        onChange={(e) => setMeasurementForm(prev => ({ ...prev, measurement_activity_type: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  )}

                  <div className="bg-amber-50 p-3 rounded-lg border border-amber-200 flex items-start gap-2.5 text-xs text-amber-800">
                    <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p>
                      The system retrieves actual <strong>POSTED</strong> carbon ledger entries for both periods. If no POSTED data exists for the selected measurement period, the system safely returns <strong>MEASUREMENT_DATA_UNAVAILABLE</strong> rather than calculating a false reduction.
                    </p>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setMeasurementModal(null)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={calculatingMeasurement}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {calculatingMeasurement ? 'Comparing Ledger Data...' : 'Calculate Observed Comparison'}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="space-y-4 text-sm">
                  {measurementResult.is_comparable ? (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                          <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">Reference Footprint</span>
                          <span className="text-lg font-bold text-slate-900">
                            {measurementResult.reference_co2e_t !== null ? `${measurementResult.reference_co2e_t.toFixed(4)} tCO2e` : '—'}
                          </span>
                          <span className="block text-xs text-slate-400 mt-0.5">Period: {measurementResult.reference_period}</span>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                          <span className="text-xs text-slate-500 uppercase tracking-wider block mb-1">Measured Footprint</span>
                          <span className="text-lg font-bold text-slate-900">
                            {measurementResult.measurement_co2e_t !== null ? `${measurementResult.measurement_co2e_t.toFixed(4)} tCO2e` : '—'}
                          </span>
                          <span className="block text-xs text-slate-400 mt-0.5">Period: {measurementResult.measurement_period}</span>
                        </div>
                      </div>

                      <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200 space-y-1 text-center">
                        <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider block">Observed Accounting Change</span>
                        <div className="text-2xl font-black text-emerald-700">
                          {measurementResult.observed_change_t !== null ? (
                            `${measurementResult.observed_change_t > 0 ? '+' : ''}${measurementResult.observed_change_t.toFixed(4)} tCO2e`
                          ) : '—'}
                          {measurementResult.observed_change_percentage !== None && measurementResult.observed_change_percentage !== undefined && (
                            <span className="text-sm font-semibold ml-2">
                              ({measurementResult.observed_change_percentage > 0 ? '+' : ''}{measurementResult.observed_change_percentage.toFixed(2)}%)
                            </span>
                          )}
                        </div>
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-900 mt-1">
                          Evidence: {measurementResult.evidence_status}
                        </span>
                      </div>

                      {/* MANDATORY CAUSALITY WARNING */}
                      <div className="bg-rose-50 p-3.5 rounded-xl border border-rose-200 flex items-start gap-2.5 text-xs text-rose-900">
                        <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <strong className="block font-semibold">IMPORTANT ACCOUNTING NOTICE</strong>
                          <p className="mt-0.5">{measurementResult.limitations}</p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 text-amber-900 space-y-2 text-xs">
                      <div className="flex items-center gap-2 font-bold text-amber-800">
                        <AlertCircle className="w-4 h-4 text-amber-600" />
                        Measurement Data Unavailable
                      </div>
                      <p>{measurementResult.reason}</p>
                    </div>
                  )}

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      onClick={() => setMeasurementResult(null)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                    >
                      Re-configure Comparison
                    </button>
                    <button
                      onClick={() => { setMeasurementModal(null); setMeasurementResult(null); }}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg"
                    >
                      Done
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 17: VERIFICATION MODAL */}
        {verificationModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-1.5">
                  <ShieldCheck className="w-5 h-5 text-purple-600" />
                  Measurement Verification
                </h3>
                <button
                  onClick={() => setVerificationModal(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              {verificationError && (
                <div className="bg-rose-50 p-3 rounded-lg border border-rose-200 text-xs text-rose-800">
                  {verificationError}
                </div>
              )}

              <form onSubmit={handleSaveVerification} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Verification Status</label>
                  <select
                    value={verificationForm.verification_status}
                    onChange={(e) => setVerificationForm(prev => ({ ...prev, verification_status: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="NOT_SUBMITTED">NOT_SUBMITTED</option>
                    <option value="INTERNAL_REVIEW">INTERNAL_REVIEW</option>
                    <option value="ACCEPTED">ACCEPTED (Internal)</option>
                    <option value="REJECTED">REJECTED (Internal)</option>
                    <option value="EXTERNAL_VERIFICATION_PENDING">EXTERNAL_VERIFICATION_PENDING</option>
                    <option value="EXTERNALLY_VERIFIED">EXTERNALLY_VERIFIED (Third-Party Audit)</option>
                  </select>
                </div>

                {verificationForm.verification_status === 'EXTERNALLY_VERIFIED' && (
                  <div className="space-y-3 pt-2 border-t border-slate-200">
                    <p className="text-xs text-purple-800 font-medium bg-purple-50 p-2 rounded">
                      Required Third-Party Verifier Provenance Metadata:
                    </p>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Verifier Name *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Dr. Aris Thorne"
                        value={verificationForm.verifier_name}
                        onChange={(e) => setVerificationForm(prev => ({ ...prev, verifier_name: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Verifier Organization *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. TUV Rheinland / DNV GL"
                        value={verificationForm.verifier_organization}
                        onChange={(e) => setVerificationForm(prev => ({ ...prev, verifier_organization: e.target.value }))}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Ref ID / Statement *</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. VREF-2026-992"
                          value={verificationForm.verification_reference}
                          onChange={(e) => setVerificationForm(prev => ({ ...prev, verification_reference: e.target.value }))}
                          className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Audit Date *</label>
                        <input
                          type="date"
                          required
                          value={verificationForm.verification_date}
                          onChange={(e) => setVerificationForm(prev => ({ ...prev, verification_date: e.target.value }))}
                          className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-xs"
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-slate-50 p-2.5 rounded border border-slate-200 text-xs text-slate-500">
                  Disclaimer: Senseible records verification metadata but does not perform independent third-party carbon accreditation.
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setVerificationModal(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingVerification}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {submittingVerification ? 'Saving...' : 'Save Verification'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* PROJECT DETAIL & AUDIT MODAL */}
        {selectedProject && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-xl border border-slate-200 p-6 space-y-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {selectedProject.project_code}
                    </span>
                    {getStatusBadge(selectedProject.status)}
                  </div>
                  <h2 className="text-xl font-bold text-slate-900">{selectedProject.title}</h2>
                </div>
                <button
                  onClick={() => setSelectedProject(null)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4 text-sm">
                {selectedProject.description && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Description</h4>
                    <p className="text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">{selectedProject.description}</p>
                  </div>
                )}

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">User Target</h4>
                  <p className="text-slate-700 bg-emerald-50/60 p-3 rounded-lg border border-emerald-100 font-medium">
                    {selectedProject.target_description || '—'}
                  </p>
                </div>

                {/* STEP 17: MEASUREMENTS & VERIFICATION SECTION */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                      <BarChart3 className="w-3.5 h-3.5 text-emerald-600" />
                      Observed Accounting Measurements ({projectMeasurements.length})
                    </h4>
                    <button
                      onClick={() => setMeasurementModal(selectedProject)}
                      className="text-xs text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1"
                    >
                      + New Measurement
                    </button>
                  </div>

                  {loadingMeasurements ? (
                    <div className="text-xs text-slate-400 p-3 bg-slate-50 rounded">Loading measurements...</div>
                  ) : projectMeasurements.length === 0 ? (
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
                      No accounting measurements calculated yet for this project.
                      <button
                        onClick={() => setMeasurementModal(selectedProject)}
                        className="block mx-auto mt-2 text-emerald-700 font-semibold hover:underline"
                      >
                        Measure Results Between Periods
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {projectMeasurements.map((m) => (
                        <div key={m.id} className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-slate-800">
                                {m.reference_period} → {m.measurement_period}
                              </span>
                              <span className="px-2 py-0.5 bg-slate-200/70 rounded text-slate-700 font-mono">
                                {m.measurement_scope_type}
                              </span>
                              {getVerificationBadge(m.verification_status)}
                            </div>
                            <button
                              onClick={() => handleOpenVerificationModal(m)}
                              className="text-purple-700 hover:text-purple-900 font-semibold"
                            >
                              Verification Details
                            </button>
                          </div>

                          <div className="grid grid-cols-3 gap-2 pt-1 text-slate-700">
                            <div>
                              <span className="text-slate-400 block">Reference:</span>
                              <strong>{m.reference_co2e_t !== null ? `${m.reference_co2e_t.toFixed(4)} t` : 'N/A'}</strong>
                            </div>
                            <div>
                              <span className="text-slate-400 block">Measured:</span>
                              <strong>{m.measurement_co2e_t !== null ? `${m.measurement_co2e_t.toFixed(4)} t` : 'N/A'}</strong>
                            </div>
                            <div>
                              <span className="text-slate-400 block">Observed Change:</span>
                              <strong className={m.observed_change_t < 0 ? 'text-emerald-700' : 'text-slate-800'}>
                                {m.observed_change_t !== null ? `${m.observed_change_t > 0 ? '+' : ''}${m.observed_change_t.toFixed(4)} t` : 'N/A'}
                              </strong>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* AUDIT TRAIL TIMELINE */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5" />
                    Status History & Audit Trail
                  </h4>
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                    {selectedProject.events && selectedProject.events.length > 0 ? (
                      selectedProject.events.map((ev) => (
                        <div key={ev.id} className="text-xs flex items-start gap-3 border-b border-slate-200/60 pb-2.5 last:border-0 last:pb-0">
                          <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1 flex-shrink-0" />
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-800">{ev.event_type}</span>
                              <span className="text-slate-400">{new Date(ev.created_at).toLocaleString()}</span>
                            </div>
                            {ev.note && <p className="text-slate-600 mt-0.5">{ev.note}</p>}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-400">No event log entries recorded.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 flex justify-end">
                <button
                  onClick={() => setSelectedProject(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CREATE NEW PROJECT MODAL */}
        {createModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">Create Carbon Reduction Project</h3>
                <button
                  onClick={() => setCreateModal(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateProject} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Project Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. LED Lighting Retrofit & Occupancy Sensors"
                    value={createForm.title}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Category</label>
                    <select
                      value={createForm.category}
                      onChange={(e) => setCreateForm(prev => ({ ...prev, category: e.target.value }))}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="ENERGY">ENERGY</option>
                      <option value="FUEL">FUEL</option>
                      <option value="TRANSPORT">TRANSPORT</option>
                      <option value="DATA_QUALITY">DATA_QUALITY</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Scope</label>
                    <select
                      value={createForm.scope}
                      onChange={(e) => setCreateForm(prev => ({ ...prev, scope: e.target.value }))}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="SCOPE_1">SCOPE 1</option>
                      <option value="SCOPE_2">SCOPE 2</option>
                      <option value="SCOPE_3">SCOPE 3</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Owner / Team</label>
                  <input
                    type="text"
                    placeholder="e.g. Operations Manager"
                    value={createForm.owner}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, owner: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Target Description</label>
                  <textarea
                    rows={2}
                    placeholder="Describe operational objective..."
                    value={createForm.target_description}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, target_description: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setCreateModal(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {creating ? 'Creating...' : 'Create Project'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
