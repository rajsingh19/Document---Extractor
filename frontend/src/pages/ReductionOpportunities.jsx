import React, { useState, useEffect } from 'react';
import { 
  Lightbulb, 
  AlertTriangle, 
  TrendingUp, 
  Zap, 
  Fuel, 
  Truck, 
  CheckCircle2, 
  Clock, 
  ChevronRight, 
  Filter, 
  PlusCircle, 
  RefreshCw, 
  HelpCircle, 
  ShieldCheck, 
  Layers,
  ArrowUpRight,
  Sparkles,
  Info
} from 'lucide-react';
import { 
  getReductionOpportunities, 
  getReductionOpportunitySummary, 
  generateReductionOpportunities, 
  updateReductionOpportunityStatus,
  createProjectFromOpportunity 
} from '../services/api';

export default function ReductionOpportunities() {
  const [opportunities, setOpportunities] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // Modals & Details
  const [selectedOpp, setSelectedOpp] = useState(null);
  const [createProjectModal, setCreateProjectModal] = useState(null);
  const [projectForm, setProjectForm] = useState({ title: '', owner: '', target_description: '', notes: '' });
  const [submittingProject, setSubmittingProject] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedCategory, selectedPriority, selectedScope, selectedStatus]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (selectedCategory) params.category = selectedCategory;
      if (selectedPriority) params.priority = selectedPriority;
      if (selectedScope) params.scope = selectedScope;
      if (selectedStatus) params.status = selectedStatus;

      const [oppsData, sumData] = await Promise.all([
        getReductionOpportunities(params),
        getReductionOpportunitySummary()
      ]);

      setOpportunities(oppsData.items || []);
      setSummary(sumData);
    } catch (err) {
      console.error("Failed to load reduction opportunities:", err);
      setError("Unable to load reduction opportunities. Please ensure backend services are running.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      await generateReductionOpportunities();
      await loadData();
    } catch (err) {
      console.error("Failed to generate opportunities:", err);
      setError("Failed to run opportunity detection engine.");
    } finally {
      setGenerating(false);
    }
  };

  const handleStatusChange = async (oppId, newStatus) => {
    try {
      await updateReductionOpportunityStatus(oppId, newStatus);
      await loadData();
      if (selectedOpp && selectedOpp.id === oppId) {
        setSelectedOpp(prev => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      console.error("Failed to update status:", err);
      alert("Failed to update opportunity status.");
    }
  };

  const handleOpenCreateProject = (opp) => {
    setCreateProjectModal(opp);
    setProjectForm({
      title: `Project: ${opp.title}`,
      owner: '',
      target_description: opp.recommended_action || '',
      notes: `Originating Opportunity: ${opp.opportunity_code}`
    });
  };

  const handleCreateProjectSubmit = async (e) => {
    e.preventDefault();
    if (!createProjectModal) return;
    try {
      setSubmittingProject(true);
      await createProjectFromOpportunity(createProjectModal.id, {
        title: projectForm.title,
        owner: projectForm.owner || null,
        target_description: projectForm.target_description || null,
        notes: projectForm.notes || null,
      });
      setCreateProjectModal(null);
      await loadData();
      alert("Reduction project created successfully!");
    } catch (err) {
      console.error("Failed to create reduction project:", err);
      alert("Failed to create project: " + (err.response?.data?.detail || err.message));
    } finally {
      setSubmittingProject(false);
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'HIGH':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">HIGH PRIORITY</span>;
      case 'MEDIUM':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">MEDIUM PRIORITY</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">LOW PRIORITY</span>;
    }
  };

  const getCategoryBadge = (category) => {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">{category}</span>;
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'OPEN':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">OPEN</span>;
      case 'ACKNOWLEDGED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">ACKNOWLEDGED</span>;
      case 'IN_PROGRESS':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">IN PROGRESS</span>;
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">COMPLETED</span>;
      case 'DISMISSED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200">DISMISSED</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-600">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* HEADER */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-emerald-100 text-emerald-800">
                <Lightbulb className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reduction Opportunities</h1>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Deterministic operational areas identified from your calculated carbon footprint and posted accounting ledger.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
              {generating ? 'Scanning Ledger...' : 'Scan For Opportunities'}
            </button>
          </div>
        </div>

        {/* SUMMARY CARDS */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Open Opportunities</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">{summary.open_count}</span>
                <span className="text-xs text-slate-400">of {summary.total_opportunities} total</span>
              </div>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">High Priority</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-rose-600">{summary.high_priority_count}</span>
                <span className="text-xs text-slate-400">require investigation</span>
              </div>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">In Progress</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-purple-600">{summary.in_progress_count}</span>
                <span className="text-xs text-slate-400">active initiatives</span>
              </div>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Medium / Low</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-amber-600">{summary.medium_priority_count + summary.low_priority_count}</span>
                <span className="text-xs text-slate-400">secondary areas</span>
              </div>
            </div>
          </div>
        )}

        {/* FILTERS */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5 text-slate-600 font-medium">
              <Filter className="w-4 h-4 text-slate-400" />
              <span>Filters:</span>
            </div>

            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Categories</option>
              <option value="ENERGY">Energy</option>
              <option value="FUEL">Fuel</option>
              <option value="TRANSPORT">Transport</option>
              <option value="EMISSIONS">Emissions</option>
              <option value="DATA_QUALITY">Data Quality</option>
            </select>

            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Priorities</option>
              <option value="HIGH">High Priority</option>
              <option value="MEDIUM">Medium Priority</option>
              <option value="LOW">Low Priority</option>
            </select>

            <select
              value={selectedScope}
              onChange={(e) => setSelectedScope(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Scopes</option>
              <option value="SCOPE_1">Scope 1</option>
              <option value="SCOPE_2">Scope 2</option>
              <option value="SCOPE_3">Scope 3</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="DISMISSED">Dismissed</option>
            </select>

            {(selectedCategory || selectedPriority || selectedScope || selectedStatus) && (
              <button
                onClick={() => {
                  setSelectedCategory('');
                  setSelectedPriority('');
                  setSelectedScope('');
                  setSelectedStatus('');
                }}
                className="text-xs text-rose-600 hover:text-rose-700 font-medium ml-auto"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* ERROR NOTICE */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        {/* OPPORTUNITIES LIST */}
        {loading ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
            Loading reduction opportunities...
          </div>
        ) : opportunities.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="font-medium text-slate-800">No reduction opportunities match the selected criteria.</p>
            <p className="text-xs text-slate-400 mt-1">Scan the ledger or adjust filter settings to view opportunities.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {opportunities.map((opp) => (
              <div 
                key={opp.id} 
                className="bg-white rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all p-5"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {getPriorityBadge(opp.priority)}
                      {getCategoryBadge(opp.category)}
                      {opp.scope && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                          {opp.scope}
                        </span>
                      )}
                      {getStatusBadge(opp.status)}
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-slate-900 hover:text-emerald-700 transition-colors cursor-pointer"
                          onClick={() => setSelectedOpp(opp)}>
                        {opp.title}
                      </h3>
                      <p className="text-sm text-slate-600 mt-0.5">{opp.description}</p>
                    </div>

                    {/* EVIDENCE LINEAGE & FOOTPRINT CHIPS */}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                      {opp.calculated_co2e_t !== null && opp.calculated_co2e_t !== undefined && (
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200 font-medium text-slate-700">
                          Footprint: <strong className="text-slate-900">{opp.calculated_co2e_t.toFixed(4)} tCO2e</strong>
                        </span>
                      )}
                      {opp.current_value !== null && opp.current_value !== undefined && (
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
                          Activity: <strong>{Number(opp.current_value).toLocaleString()} {opp.current_unit}</strong>
                        </span>
                      )}
                      {opp.evidence_document_id && (
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
                          Document #{opp.evidence_document_id}
                        </span>
                      )}
                      {opp.evidence_ledger_entry_id && (
                        <span className="bg-slate-50 px-2 py-1 rounded border border-slate-200">
                          Ledger #{opp.evidence_ledger_entry_id}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* ACTION BUTTONS */}
                  <div className="flex flex-wrap items-center gap-2 lg:flex-col lg:items-end">
                    <button
                      onClick={() => handleOpenCreateProject(opp)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors"
                    >
                      <PlusCircle className="w-3.5 h-3.5" />
                      Create Reduction Project
                    </button>
                    
                    <div className="flex items-center gap-2">
                      <select
                        value={opp.status}
                        onChange={(e) => handleStatusChange(opp.id, e.target.value)}
                        className="text-xs bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-600 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      >
                        <option value="OPEN">Mark Open</option>
                        <option value="ACKNOWLEDGED">Acknowledge</option>
                        <option value="IN_PROGRESS">In Progress</option>
                        <option value="COMPLETED">Completed</option>
                        <option value="DISMISSED">Dismiss</option>
                      </select>

                      <button
                        onClick={() => setSelectedOpp(opp)}
                        className="text-xs text-slate-600 hover:text-slate-900 font-medium px-2 py-1 bg-slate-100 hover:bg-slate-200 rounded border border-slate-200"
                      >
                        Details
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* DETAIL MODAL / DRAWER */}
        {selectedOpp && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl border border-slate-200 p-6 space-y-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    {getPriorityBadge(selectedOpp.priority)}
                    {getCategoryBadge(selectedOpp.category)}
                    {getStatusBadge(selectedOpp.status)}
                  </div>
                  <h2 className="text-xl font-bold text-slate-900">{selectedOpp.title}</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Code: {selectedOpp.opportunity_code}</p>
                </div>
                <button
                  onClick={() => setSelectedOpp(null)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Description</h4>
                  <p className="text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">{selectedOpp.description}</p>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Deterministic Detection Rationale</h4>
                  <p className="text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">{selectedOpp.rationale}</p>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Recommended Investigation Action</h4>
                  <p className="text-slate-700 bg-emerald-50/60 p-3 rounded-lg border border-emerald-100 text-emerald-950 font-medium">
                    {selectedOpp.recommended_action}
                  </p>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Safety & Limitations Warning</h4>
                  <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg text-amber-900 text-xs flex items-start gap-2">
                    <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <span>{selectedOpp.limitations}</span>
                  </div>
                </div>

                {/* Quantitative Data */}
                <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
                  <div className="bg-slate-50 p-3 rounded border border-slate-200">
                    <span className="text-slate-400">Calculated Footprint</span>
                    <p className="font-semibold text-slate-800 mt-1">
                      {selectedOpp.calculated_co2e_t ? `${selectedOpp.calculated_co2e_t.toFixed(4)} tCO2e` : '—'}
                    </p>
                  </div>
                  <div className="bg-slate-50 p-3 rounded border border-slate-200">
                    <span className="text-slate-400">Current Measured Activity</span>
                    <p className="font-semibold text-slate-800 mt-1">
                      {selectedOpp.current_value ? `${Number(selectedOpp.current_value).toLocaleString()} ${selectedOpp.current_unit}` : '—'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
                <button
                  onClick={() => {
                    const opp = selectedOpp;
                    setSelectedOpp(null);
                    handleOpenCreateProject(opp);
                  }}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm"
                >
                  Create Reduction Project
                </button>
                <button
                  onClick={() => setSelectedOpp(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CREATE PROJECT MODAL */}
        {createProjectModal && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full shadow-xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-slate-900">Create Carbon Reduction Project</h3>
                <button
                  onClick={() => setCreateProjectModal(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateProjectSubmit} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Project Title</label>
                  <input
                    type="text"
                    required
                    value={projectForm.title}
                    onChange={(e) => setProjectForm(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Project Owner</label>
                  <input
                    type="text"
                    placeholder="e.g., Sustainability Lead / Facilities Ops"
                    value={projectForm.owner}
                    onChange={(e) => setProjectForm(prev => ({ ...prev, owner: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Target Description</label>
                  <textarea
                    rows={3}
                    value={projectForm.target_description}
                    onChange={(e) => setProjectForm(prev => ({ ...prev, target_description: e.target.value }))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-600">
                  <p className="font-semibold text-slate-800">Accounting Baseline Reference</p>
                  <p className="mt-0.5">
                    Linked to: <strong>{createProjectModal.title}</strong> ({createProjectModal.calculated_co2e_t ? `${createProjectModal.calculated_co2e_t.toFixed(4)} tCO2e` : '—'})
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setCreateProjectModal(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingProject}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {submittingProject ? 'Creating...' : 'Save & Track Project'}
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
