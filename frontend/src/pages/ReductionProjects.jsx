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
  Info
} from 'lucide-react';
import { 
  getReductionProjects, 
  createReductionProject, 
  updateReductionProjectStatus, 
  updateReductionProject 
} from '../services/api';

export default function ReductionProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  // Modals
  const [selectedProject, setSelectedProject] = useState(null);
  const [statusModal, setStatusModal] = useState(null);
  const [newStatus, setNewStatus] = useState('IN_PROGRESS');
  const [statusNote, setStatusNote] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

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

  const handleStatusUpdate = async (e) => {
    e.preventDefault();
    if (!statusModal) return;
    try {
      setUpdatingStatus(true);
      await updateReductionProjectStatus(statusModal.id, newStatus, statusNote || null);
      setStatusModal(null);
      setStatusNote('');
      await loadProjects();
    } catch (err) {
      console.error("Failed to update project status:", err);
      alert("Failed to update status: " + (err.response?.data?.detail || err.message));
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
      await loadProjects();
    } catch (err) {
      console.error("Failed to create project:", err);
      alert("Failed to create project: " + (err.response?.data?.detail || err.message));
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PLANNED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">PLANNED</span>;
      case 'IN_PROGRESS':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">IN PROGRESS</span>;
      case 'ON_HOLD':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">ON HOLD</span>;
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">COMPLETED</span>;
      case 'CANCELLED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">CANCELLED</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-600">{status}</span>;
    }
  };

  const plannedCount = projects.filter(p => p.status === 'PLANNED').length;
  const inProgressCount = projects.filter(p => p.status === 'IN_PROGRESS').length;
  const completedCount = projects.filter(p => p.status === 'COMPLETED').length;

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* HEADER */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-purple-100 text-purple-800">
                <FolderKanban className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reduction Projects</h1>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Track operational decarbonization initiatives, baseline references, and status history from identified opportunities.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              New Project
            </button>
          </div>
        </div>

        {/* SUMMARY STATS */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Projects</span>
            <div className="mt-2 text-2xl font-bold text-slate-900">{projects.length}</div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Planned</span>
            <div className="mt-2 text-2xl font-bold text-slate-600">{plannedCount}</div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">In Progress</span>
            <div className="mt-2 text-2xl font-bold text-purple-600">{inProgressCount}</div>
          </div>
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed</span>
            <div className="mt-2 text-2xl font-bold text-emerald-600">{completedCount}</div>
          </div>
        </div>

        {/* FILTERS */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="text-slate-600 font-medium">Filter Projects:</span>

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
            Loading projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <FolderKanban className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-medium text-slate-800">No reduction projects found.</p>
            <p className="text-xs text-slate-400 mt-1">Create a project from the Reduction Opportunities page or click "New Project" above.</p>
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
                        onClick={() => setSelectedProject(prj)}
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
                          Baseline Reference: <strong>{prj.baseline_co2e_t.toFixed(4)} tCO2e</strong>
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
                  <div className="flex items-center gap-2">
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
                      onClick={() => setSelectedProject(prj)}
                      className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium rounded-lg transition-colors"
                    >
                      View Details & Audit
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

        {/* PROJECT DETAIL & AUDIT MODAL */}
        {selectedProject && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl border border-slate-200 p-6 space-y-5">
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

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 p-3 rounded border border-slate-200">
                    <span className="text-slate-400">Baseline Reference</span>
                    <p className="font-semibold text-slate-800 mt-1">
                      {selectedProject.baseline_co2e_t ? `${selectedProject.baseline_co2e_t.toFixed(4)} tCO2e` : '—'}
                    </p>
                  </div>
                  <div className="bg-slate-50 p-3 rounded border border-slate-200">
                    <span className="text-slate-400">Observed Post-Project Footprint</span>
                    <p className="font-semibold text-slate-800 mt-1">
                      {selectedProject.actual_post_project_t ? `${selectedProject.actual_post_project_t.toFixed(4)} tCO2e` : 'Awaiting Post-Period Accounting'}
                    </p>
                  </div>
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
