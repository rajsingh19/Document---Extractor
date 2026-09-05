import React, { useState, useEffect } from 'react';
import {
  Compass,
  Target,
  ArrowRight,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Layers,
  BarChart3,
  RefreshCw,
  FileText,
  ShieldCheck,
  HelpCircle,
  TrendingDown,
  Info,
  Calendar,
  Sparkles,
  ChevronRight,
  ExternalLink,
  History,
  X,
} from 'lucide-react';
import {
  getReductionRoadmaps,
  getReductionRoadmapById,
  createReductionRoadmap,
  regenerateReductionRoadmap,
  getReductionRoadmapProgress,
  updateReductionRoadmap,
  updateReductionRoadmapItemStatus,
  getReductionRoadmapEvents,
  getDocuments,
} from '../services/api';

const ReductionRoadmap = () => {
  // State
  const [roadmaps, setRoadmaps] = useState([]);
  const [activeRoadmap, setActiveRoadmap] = useState(null);
  const [progress, setProgress] = useState(null);
  const [events, setEvents] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState(null);

  // Form State
  const [targetPercent, setTargetPercent] = useState(20);
  const [targetYear, setTargetYear] = useState(2025);
  const [customName, setCustomName] = useState('');

  // Selected Item Drawer
  const [selectedItem, setSelectedItem] = useState(null);
  const [showEventsModal, setShowEventsModal] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [roadmapsRes, docsRes] = await Promise.all([
        getReductionRoadmaps(),
        getDocuments(),
      ]);
      setRoadmaps(roadmapsRes.items || []);
      setDocuments(docsRes.documents || docsRes || []);

      if (roadmapsRes.items && roadmapsRes.items.length > 0) {
        await loadRoadmapDetail(roadmapsRes.items[0].id);
      }
    } catch (err) {
      console.error('Failed to load reduction roadmap data:', err);
      setError('Unable to load reduction roadmaps. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadRoadmapDetail = async (roadmapId) => {
    try {
      const [detailRes, progRes, evtRes] = await Promise.all([
        getReductionRoadmapById(roadmapId),
        getReductionRoadmapProgress(roadmapId),
        getReductionRoadmapEvents(roadmapId),
      ]);
      setActiveRoadmap(detailRes);
      setProgress(progRes);
      setEvents(evtRes || []);
    } catch (err) {
      console.error('Failed to load roadmap details:', err);
    }
  };

  const handleCreateRoadmap = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const payload = {
        target_reduction_percent: parseFloat(targetPercent),
        target_year: targetYear ? parseInt(targetYear) : null,
        document_id: selectedDocId ? parseInt(selectedDocId) : null,
        name: customName || `Reduction Roadmap (${targetPercent}% Target)`,
      };
      const created = await createReductionRoadmap(payload);
      await loadInitialData();
      await loadRoadmapDetail(created.id);
    } catch (err) {
      console.error('Failed to create reduction roadmap:', err);
      setError('Failed to create reduction roadmap. Ensure valid target percentage.');
    } finally {
      setCreating(false);
    }
  };

  const handleRegenerate = async () => {
    if (!activeRoadmap) return;
    setRegenerating(true);
    try {
      await regenerateReductionRoadmap(activeRoadmap.id);
      await loadRoadmapDetail(activeRoadmap.id);
    } catch (err) {
      console.error('Failed to regenerate roadmap:', err);
    } finally {
      setRegenerating(false);
    }
  };

  const handleItemStatusChange = async (itemId, newStatus) => {
    if (!activeRoadmap) return;
    try {
      await updateReductionRoadmapItemStatus(activeRoadmap.id, itemId, { status: newStatus });
      await loadRoadmapDetail(activeRoadmap.id);
      if (selectedItem && selectedItem.id === itemId) {
        setSelectedItem((prev) => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      console.error('Failed to update item status:', err);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800"><CheckCircle2 className="w-3 h-3 mr-1" /> Completed</span>;
      case 'IN_PROGRESS':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800"><Clock className="w-3 h-3 mr-1" /> In Progress</span>;
      case 'BLOCKED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800"><AlertTriangle className="w-3 h-3 mr-1" /> Blocked</span>;
      case 'CANCELLED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-800">Cancelled</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">Not Started</span>;
    }
  };

  const getPhaseColor = (phase) => {
    switch (phase) {
      case 'PHASE_1_FOUNDATION':
        return { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', badge: 'bg-amber-100 text-amber-900' };
      case 'PHASE_2_ACTION':
        return { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', badge: 'bg-blue-100 text-blue-900' };
      case 'PHASE_3_MEASUREMENT':
        return { bg: 'bg-indigo-50', border: 'border-indigo-200', text: 'text-indigo-800', badge: 'bg-indigo-100 text-indigo-900' };
      case 'PHASE_4_VERIFICATION':
        return { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', badge: 'bg-emerald-100 text-emerald-900' };
      default:
        return { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-800', badge: 'bg-gray-100 text-gray-900' };
    }
  };

  // Group items by phase
  const groupedItems = {
    PHASE_1_FOUNDATION: activeRoadmap?.items?.filter((i) => i.phase === 'PHASE_1_FOUNDATION') || [],
    PHASE_2_ACTION: activeRoadmap?.items?.filter((i) => i.phase === 'PHASE_2_ACTION') || [],
    PHASE_3_MEASUREMENT: activeRoadmap?.items?.filter((i) => i.phase === 'PHASE_3_MEASUREMENT') || [],
    PHASE_4_VERIFICATION: activeRoadmap?.items?.filter((i) => i.phase === 'PHASE_4_VERIFICATION') || [],
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-gray-200 pb-6 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-600 rounded-lg text-white shadow-sm">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Reduction Roadmap</h1>
              <p className="text-sm text-gray-600 mt-0.5">
                Turn verified reduction priorities into a measurable, phased action plan.
              </p>
            </div>
          </div>
        </div>

        {activeRoadmap && (
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowEventsModal(true)}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
            >
              <History className="w-4 h-4 mr-1.5 text-gray-500" />
              Audit Trail ({events.length})
            </button>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${regenerating ? 'animate-spin' : ''}`} />
              Regenerate Plan
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-50 border border-rose-200 text-sm text-rose-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 font-semibold">Dismiss</button>
        </div>
      )}

      {/* Target Builder Strip */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center">
          <Target className="w-5 h-5 text-emerald-600 mr-2" />
          Set Your Reduction Target
        </h2>

        <form onSubmit={handleCreateRoadmap} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Target Reduction %</label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={targetPercent}
                onChange={(e) => setTargetPercent(e.target.value)}
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-emerald-500 focus:border-emerald-500 pr-8"
              />
              <span className="absolute right-3 top-2 text-sm text-gray-400 font-medium">%</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Target Year</label>
            <input
              type="number"
              min="2024"
              max="2050"
              value={targetYear}
              onChange={(e) => setTargetYear(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Scope to Document (Optional)</label>
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-emerald-500 focus:border-emerald-500 bg-white"
            >
              <option value="">All Portfolio Documents</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  Doc #{d.id} ({d.original_filename || d.filename})
                </option>
              ))}
            </select>
          </div>

          <div>
            <button
              type="submit"
              disabled={creating}
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-gray-900 hover:bg-gray-800 focus:outline-none disabled:opacity-50"
            >
              {creating ? 'Building...' : 'Build Roadmap'}
              <ArrowRight className="w-4 h-4 ml-2" />
            </button>
          </div>
        </form>
      </div>

      {/* Target & KPI Summary */}
      {activeRoadmap && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {/* Baseline */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Current Baseline</div>
            <div className="mt-2 text-2xl font-bold text-gray-900">
              {Number(activeRoadmap.baseline_emissions_tco2e).toFixed(4)}{' '}
              <span className="text-sm font-normal text-gray-500">tCO2e</span>
            </div>
            <div className="mt-1 flex items-center text-xs text-gray-600">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1.5" />
              Period: {activeRoadmap.baseline_period} (ACTUAL)
            </div>
          </div>

          {/* Target */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Target Emissions ({activeRoadmap.target_reduction_percent}%)
            </div>
            <div className="mt-2 text-2xl font-bold text-blue-700">
              {Number(activeRoadmap.target_emissions_tco2e).toFixed(4)}{' '}
              <span className="text-sm font-normal text-gray-500">tCO2e</span>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              Target Year: {activeRoadmap.target_year || 'Not specified'}
            </div>
          </div>

          {/* Required Gap */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">Required Reduction Gap</div>
            <div className="mt-2 text-2xl font-bold text-amber-700">
              {Number(activeRoadmap.reduction_gap_tco2e).toFixed(4)}{' '}
              <span className="text-sm font-normal text-gray-500">tCO2e</span>
            </div>
            <div className="mt-1 text-xs text-amber-600 font-medium">
              Mathematical target gap (non-projected)
            </div>
          </div>

          {/* Feasibility Indicator */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center justify-between">
              <span>Target Feasibility</span>
              <span className="group relative cursor-pointer">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400" />
                <span className="absolute bottom-full right-0 mb-1 w-56 p-2 bg-gray-900 text-white text-xs rounded shadow-lg hidden group-hover:block z-10 font-normal">
                  {activeRoadmap.feasibility_explanation}
                </span>
              </span>
            </div>
            <div className="mt-2">
              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                <AlertTriangle className="w-3 h-3 mr-1 text-amber-600" />
                Not Yet Quantified
              </span>
            </div>
            <div className="mt-1 text-xs text-gray-500 truncate" title={activeRoadmap.feasibility_explanation}>
              Verified M&V data required
            </div>
          </div>
        </div>
      )}

      {/* Progress Separation Section */}
      {progress && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 1. Roadmap Progress */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-gray-900">Roadmap Action Progress</h3>
                <p className="text-xs text-gray-500">Operational tasks and milestones completed</p>
              </div>
              <span className="text-lg font-bold text-gray-900">{progress.roadmap_progress_percent}%</span>
            </div>

            <div className="w-full bg-gray-100 rounded-full h-2.5 mb-4">
              <div
                className="bg-emerald-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress.roadmap_progress_percent}%` }}
              />
            </div>

            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              <div className="p-2 bg-gray-50 rounded">
                <span className="text-gray-500 block">Total</span>
                <span className="font-bold text-gray-900">{progress.total_items}</span>
              </div>
              <div className="p-2 bg-emerald-50 rounded">
                <span className="text-emerald-700 block">Done</span>
                <span className="font-bold text-emerald-800">{progress.completed_items}</span>
              </div>
              <div className="p-2 bg-blue-50 rounded">
                <span className="text-blue-700 block">Active</span>
                <span className="font-bold text-blue-800">{progress.in_progress_items}</span>
              </div>
              <div className="p-2 bg-amber-50 rounded">
                <span className="text-amber-700 block">Blocked</span>
                <span className="font-bold text-amber-800">{progress.blocked_items}</span>
              </div>
            </div>
          </div>

          {/* 2. Emissions Reduction Progress */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-gray-900">Emissions Reduction Progress</h3>
                <p className="text-xs text-gray-500">Actual POSTED accounting ledger changes</p>
              </div>
              <span className="text-xs px-2 py-0.5 rounded font-semibold bg-gray-100 text-gray-700">
                {progress.emissions_progress_status === 'OBSERVED_ACTUAL_CHANGE' ? 'Observed Change' : 'Pending M&V'}
              </span>
            </div>

            {progress.emissions_progress_status === 'OBSERVED_ACTUAL_CHANGE' ? (
              <div className="space-y-2">
                <div className="flex items-baseline space-x-2">
                  <span className={`text-2xl font-bold ${progress.actual_change_percent < 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {progress.actual_change_percent > 0 ? '+' : ''}{progress.actual_change_percent}%
                  </span>
                  <span className="text-xs text-gray-500">
                    ({progress.actual_change_tco2e > 0 ? '+' : ''}{progress.actual_change_tco2e} tCO2e vs baseline)
                  </span>
                </div>
                <p className="text-xs text-gray-600">
                  Latest period: <strong>{progress.latest_actual_period}</strong> ({progress.latest_actual_emissions_tco2e} tCO2e).
                  Observed accounting change does not prove project causality.
                </p>
              </div>
            ) : (
              <div className="py-3 text-center">
                <p className="text-sm text-gray-600 font-medium">Insufficient post-project measurement data</p>
                <p className="text-xs text-gray-400 mt-1">
                  Upload subsequent monthly energy/fuel documents to record post-implementation ledger actuals.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4-Phase Roadmap Timeline */}
      {activeRoadmap && (
        <div className="space-y-6">
          <div className="border-b border-gray-200 pb-3 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center">
              <Layers className="w-5 h-5 text-gray-700 mr-2" />
              Structured 4-Phase Implementation Plan
            </h2>
            <span className="text-xs text-gray-500">
              {activeRoadmap.items?.length || 0} Total Actions
            </span>
          </div>

          {/* Phases */}
          {[
            { key: 'PHASE_1_FOUNDATION', label: 'Phase 1: Foundation', window: '0–30 days', icon: FileText },
            { key: 'PHASE_2_ACTION', label: 'Phase 2: Action & Implementation', window: '31–90 days', icon: Target },
            { key: 'PHASE_3_MEASUREMENT', label: 'Phase 3: Measurement & Accounting', window: '91–180 days', icon: BarChart3 },
            { key: 'PHASE_4_VERIFICATION', label: 'Phase 4: Verification & Target Review', window: '181+ days', icon: ShieldCheck },
          ].map((phaseMeta) => {
            const items = groupedItems[phaseMeta.key] || [];
            const colors = getPhaseColor(phaseMeta.key);
            const IconComponent = phaseMeta.icon;

            return (
              <div key={phaseMeta.key} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                {/* Phase Header */}
                <div className={`px-6 py-4 border-b ${colors.bg} ${colors.border} flex items-center justify-between`}>
                  <div className="flex items-center space-x-3">
                    <div className={`p-1.5 rounded-md bg-white shadow-xs ${colors.text}`}>
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-gray-900">{phaseMeta.label}</h3>
                      <span className="text-xs text-gray-500">Suggested Planning Window: {phaseMeta.window}</span>
                    </div>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${colors.badge}`}>
                    {items.length} {items.length === 1 ? 'Action' : 'Actions'}
                  </span>
                </div>

                {/* Items List */}
                <div className="divide-y divide-gray-100">
                  {items.length === 0 ? (
                    <div className="p-6 text-center text-xs text-gray-400 italic">
                      No actions assigned to this planning phase.
                    </div>
                  ) : (
                    items.map((item) => (
                      <div
                        key={item.id}
                        className="p-5 hover:bg-gray-50/80 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                      >
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center space-x-2.5">
                            <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-700 font-bold text-xs flex items-center justify-center">
                              #{item.sequence}
                            </span>
                            <h4
                              onClick={() => setSelectedItem(item)}
                              className="text-sm font-semibold text-gray-900 hover:text-emerald-600 cursor-pointer"
                            >
                              {item.title}
                            </h4>
                            <span className="text-xs px-2 py-0.5 rounded font-medium bg-gray-100 text-gray-600">
                              {item.action_type}
                            </span>
                            {item.scope && (
                              <span className="text-xs px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-700">
                                {item.scope}
                              </span>
                            )}
                          </div>

                          <p className="text-xs text-gray-600 line-clamp-1">{item.reason}</p>

                          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                            {item.current_emissions_tco2e && (
                              <span>Footprint: <strong>{Number(item.current_emissions_tco2e).toFixed(4)} tCO2e</strong></span>
                            )}
                            {item.dependency && (
                              <span className="text-amber-700 font-medium">Dep: {item.dependency}</span>
                            )}
                            <span>Contribution: <strong className="text-gray-700">Not Quantified</strong></span>
                          </div>
                        </div>

                        {/* Status dropdown & detail button */}
                        <div className="flex items-center space-x-3 self-end md:self-center">
                          <select
                            value={item.status}
                            onChange={(e) => handleItemStatusChange(item.id, e.target.value)}
                            className="text-xs font-semibold rounded-md border border-gray-300 py-1.5 pl-2.5 pr-8 bg-white focus:ring-emerald-500 focus:border-emerald-500 cursor-pointer"
                          >
                            <option value="NOT_STARTED">Not Started</option>
                            <option value="IN_PROGRESS">In Progress</option>
                            <option value="BLOCKED">Blocked</option>
                            <option value="COMPLETED">Completed</option>
                            <option value="CANCELLED">Cancelled</option>
                          </select>

                          <button
                            onClick={() => setSelectedItem(item)}
                            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                            title="View Action Details"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Item Detail Modal / Drawer */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-start justify-between border-b border-gray-100 pb-4">
              <div>
                <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                  Action #{selectedItem.sequence} • {selectedItem.phase}
                </span>
                <h3 className="text-lg font-bold text-gray-900 mt-1">{selectedItem.title}</h3>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="p-1.5 text-gray-400 hover:text-gray-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Action Type</span>
                <span className="font-semibold text-gray-900">{selectedItem.action_type}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Status</span>
                <div className="mt-0.5">{getStatusBadge(selectedItem.status)}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Source Emissions</span>
                <span className="font-semibold text-gray-900">
                  {selectedItem.current_emissions_tco2e ? `${Number(selectedItem.current_emissions_tco2e).toFixed(4)} tCO2e` : 'Data Quality / N/A'}
                </span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Target Contribution</span>
                <span className="font-semibold text-amber-800">Not Quantified (NULL)</span>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <h4 className="font-bold text-gray-900">Operational Reason & Lineage</h4>
                <p className="text-gray-600 mt-1 leading-relaxed">{selectedItem.reason}</p>
              </div>

              {selectedItem.prerequisite && (
                <div>
                  <h4 className="font-bold text-gray-900">Prerequisites</h4>
                  <p className="text-gray-600 mt-1 leading-relaxed">{selectedItem.prerequisite}</p>
                </div>
              )}

              {selectedItem.required_data && (
                <div>
                  <h4 className="font-bold text-gray-900">Required Data</h4>
                  <p className="text-gray-600 mt-1 leading-relaxed">{selectedItem.required_data}</p>
                </div>
              )}

              {selectedItem.measurement_method && (
                <div>
                  <h4 className="font-bold text-gray-900">Measurement Method (M&V)</h4>
                  <p className="text-gray-600 mt-1 leading-relaxed">{selectedItem.measurement_method}</p>
                </div>
              )}

              {selectedItem.verification_method && (
                <div>
                  <h4 className="font-bold text-gray-900">Verification Protocol</h4>
                  <p className="text-gray-600 mt-1 leading-relaxed">{selectedItem.verification_method}</p>
                </div>
              )}

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900">
                <span className="font-bold block">Methodology Limitation</span>
                <span>{selectedItem.limitation || 'Reduction claims require verified post-implementation ledger records.'}</span>
              </div>
            </div>

            <div className="border-t border-gray-100 pt-4 flex justify-end">
              <button
                onClick={() => setSelectedItem(null)}
                className="px-4 py-2 bg-gray-900 text-white rounded-md text-xs font-semibold hover:bg-gray-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Audit Trail Modal */}
      {showEventsModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-xl w-full max-h-[80vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-900 flex items-center">
                <History className="w-4 h-4 mr-2 text-gray-500" />
                Roadmap Audit Trail
              </h3>
              <button
                onClick={() => setShowEventsModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="divide-y divide-gray-100">
              {events.map((evt) => (
                <div key={evt.id} className="py-3 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gray-900">{evt.event_type}</span>
                    <span className="text-gray-400">{new Date(evt.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-gray-600">{evt.notes}</p>
                  <span className="text-gray-400 block">Actor: {evt.actor}</span>
                </div>
              ))}
            </div>

            <div className="border-t border-gray-100 pt-3 flex justify-end">
              <button
                onClick={() => setShowEventsModal(false)}
                className="px-4 py-2 bg-gray-900 text-white rounded-md text-xs font-semibold hover:bg-gray-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReductionRoadmap;
