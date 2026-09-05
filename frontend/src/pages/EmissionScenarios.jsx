import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  TrendingDown,
  Layers,
  ArrowRight,
  ShieldCheck,
  Zap,
  Flame,
  Info,
  ChevronRight,
  Archive,
  BarChart2,
  FileText,
  Activity,
  PlusCircle,
  Eye,
  X,
  Target
} from 'lucide-react';
import {
  getEmissionScenarios,
  getEmissionScenario,
  createEmissionScenario,
  recalculateEmissionScenario,
  getScenarioResults,
  archiveEmissionScenario,
  getDocuments,
  getReductionRoadmaps,
  getActivityData
} from '../services/api';

const EmissionScenarios = () => {
  // State
  const [scenarios, setScenarios] = useState([]);
  const [activeScenario, setActiveScenario] = useState(null);
  const [scenarioResults, setScenarioResults] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [roadmaps, setRoadmaps] = useState([]);
  const [activityItems, setActivityItems] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  // Form State
  const [scenarioName, setScenarioName] = useState('');
  const [scenarioDescription, setScenarioDescription] = useState('');
  const [scenarioType, setScenarioType] = useState('REDUCE_ACTIVITY');
  const [targetActivityId, setTargetActivityId] = useState('');
  const [changePercent, setChangePercent] = useState('20');
  const [replacementActivityType, setReplacementActivityType] = useState('solar_electricity');
  const [replacementPercent, setReplacementPercent] = useState('30');
  const [selectedRoadmapId, setSelectedRoadmapId] = useState('');

  // Tab State
  const [viewTab, setViewTab] = useState('sources'); // 'sources' | 'assumptions' | 'target'

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadDocumentActivities(selectedDocId);
    }
  }, [selectedDocId]);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [scenariosRes, docsRes, roadmapsRes] = await Promise.all([
        getEmissionScenarios(),
        getDocuments(),
        getReductionRoadmaps().catch(() => ({ items: [] }))
      ]);

      const scList = scenariosRes.items || [];
      setScenarios(scList);
      setDocuments(docsRes.documents || docsRes || []);
      setRoadmaps(roadmapsRes.items || []);

      if (docsRes.documents && docsRes.documents.length > 0) {
        setSelectedDocId(String(docsRes.documents[0].id));
      }

      if (scList.length > 0) {
        await selectScenario(scList[0].id);
      }
    } catch (err) {
      console.error('Failed to load initial scenario data:', err);
      setError('Failed to load emissions scenarios. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const loadDocumentActivities = async (docId) => {
    try {
      const actRes = await getActivityData({ document_id: docId });
      const items = actRes.activity_data || actRes.items || actRes || [];
      setActivityItems(items);
      if (items.length > 0) {
        setTargetActivityId(String(items[0].id));
      }
    } catch (err) {
      console.error('Failed to load document activity items:', err);
    }
  };

  const selectScenario = async (scenarioId) => {
    setLoading(true);
    try {
      const [detail, results] = await Promise.all([
        getEmissionScenario(scenarioId),
        getScenarioResults(scenarioId).catch(() => ({ items: [] }))
      ]);
      setActiveScenario(detail);
      setScenarioResults(results.items || []);
    } catch (err) {
      console.error('Failed to load scenario details:', err);
      setError('Unable to load scenario details.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateScenario = async (e) => {
    e.preventDefault();
    if (!scenarioName.trim()) {
      setError('Please provide a scenario name.');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const payload = {
        name: scenarioName.trim(),
        description: scenarioDescription.trim() || null,
        document_id: selectedDocId ? parseInt(selectedDocId, 10) : null,
        roadmap_id: selectedRoadmapId ? parseInt(selectedRoadmapId, 10) : null,
        scenario_type: scenarioType,
      };

      if (scenarioType === 'REDUCE_ACTIVITY' || scenarioType === 'INCREASE_ACTIVITY') {
        payload.target_activity_data_id = targetActivityId ? parseInt(targetActivityId, 10) : null;
        payload.change_percent = parseFloat(changePercent);
      } else if (scenarioType === 'REPLACE_SOURCE' || scenarioType === 'SHIFT_SOURCE') {
        payload.source_activity_data_id = targetActivityId ? parseInt(targetActivityId, 10) : null;
        payload.replacement_activity_type = replacementActivityType;
        payload.replacement_percent = parseFloat(replacementPercent);
      } else if (scenarioType === 'ADD_SOURCE') {
        payload.target_activity_data_id = targetActivityId ? parseInt(targetActivityId, 10) : null;
        payload.change_percent = parseFloat(changePercent);
      }

      const created = await createEmissionScenario(payload);
      const updatedList = [created, ...scenarios.filter(s => s.id !== created.id)];
      setScenarios(updatedList);
      await selectScenario(created.id);

      // Reset form
      setScenarioName('');
      setScenarioDescription('');
    } catch (err) {
      console.error('Failed to create scenario:', err);
      const msg = err.response?.data?.detail || err.message || 'Failed to create scenario.';
      setError(msg);
    } finally {
      setCreating(false);
    }
  };

  const handleRecalculate = async () => {
    if (!activeScenario) return;
    setCalculating(true);
    try {
      const updated = await recalculateEmissionScenario(activeScenario.id);
      setActiveScenario(updated);
      const results = await getScenarioResults(activeScenario.id);
      setScenarioResults(results.items || []);
      setScenarios(scenarios.map(s => s.id === updated.id ? updated : s));
    } catch (err) {
      console.error('Failed to recalculate scenario:', err);
      setError('Recalculation failed.');
    } finally {
      setCalculating(false);
    }
  };

  const handleArchive = async (scenarioId) => {
    if (!window.confirm('Archive this scenario? It will be marked as ARCHIVED for audit lineage.')) return;
    try {
      await archiveEmissionScenario(scenarioId);
      setScenarios(scenarios.filter(s => s.id !== scenarioId));
      if (activeScenario && activeScenario.id === scenarioId) {
        const remaining = scenarios.filter(s => s.id !== scenarioId);
        if (remaining.length > 0) {
          await selectScenario(remaining[0].id);
        } else {
          setActiveScenario(null);
          setScenarioResults([]);
        }
      }
    } catch (err) {
      console.error('Failed to archive scenario:', err);
      setError('Failed to archive scenario.');
    }
  };

  // Quick preset loader
  const applyPreset = (presetKey) => {
    if (presetKey === 'DIESEL_20') {
      setScenarioName('Diesel Consumption -20%');
      setScenarioDescription('Evaluate modeled impact of 20% stationary diesel reduction on facility footprint.');
      setScenarioType('REDUCE_ACTIVITY');
      setChangePercent('20');
      const dieselItem = activityItems.find(a => a.activity_type?.toLowerCase().includes('diesel'));
      if (dieselItem) setTargetActivityId(String(dieselItem.id));
    } else if (presetKey === 'SOLAR_30') {
      setScenarioName('Grid Electricity to On-site Solar 30%');
      setScenarioDescription('Simulate replacing 30% of grid power with onsite solar PV.');
      setScenarioType('REPLACE_SOURCE');
      setReplacementActivityType('solar_electricity');
      setReplacementPercent('30');
      const gridItem = activityItems.find(a => a.activity_type?.toLowerCase().includes('electr'));
      if (gridItem) setTargetActivityId(String(gridItem.id));
    } else if (presetKey === 'BIODIESEL_25') {
      setScenarioName('Shift Diesel to Biodiesel Blend 25%');
      setScenarioDescription('Model fuel switching from standard diesel to low-carbon biodiesel.');
      setScenarioType('SHIFT_SOURCE');
      setReplacementActivityType('biodiesel');
      setReplacementPercent('25');
      const dieselItem = activityItems.find(a => a.activity_type?.toLowerCase().includes('diesel'));
      if (dieselItem) setTargetActivityId(String(dieselItem.id));
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner with Strict Disclaimer */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 sm:p-8 text-white border border-indigo-500/20 shadow-xl">
        <div className="absolute right-0 top-0 -mt-8 -mr-8 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold uppercase tracking-wider">
              <AlertTriangle className="w-3.5 h-3.5" />
              SCENARIO — NOT ACTUAL
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Sliders className="w-8 h-8 text-indigo-400" />
              Emissions Scenario & What-If Engine
            </h1>
            <p className="text-slate-300 text-sm max-w-2xl">
              Model hypothetical decarbonization interventions against verified ledger baselines. Scenarios are strictly non-mutating simulation records with auditable factor snapshots.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs text-slate-400">Quick Templates:</span>
            <button
              onClick={() => applyPreset('DIESEL_20')}
              className="px-3 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/30 text-xs text-indigo-200 transition flex items-center gap-1.5"
            >
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              Diesel −20%
            </button>
            <button
              onClick={() => applyPreset('SOLAR_30')}
              className="px-3 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/30 text-xs text-indigo-200 transition flex items-center gap-1.5"
            >
              <Zap className="w-3.5 h-3.5 text-yellow-400" />
              Solar 30%
            </button>
            <button
              onClick={() => applyPreset('BIODIESEL_25')}
              className="px-3 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/30 text-xs text-indigo-200 transition flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              Biodiesel 25%
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Grid: Builder Form & Scenario Visualization */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Scenario Builder (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <PlusCircle className="w-4 h-4 text-indigo-400" />
                Configure Scenario
              </h2>
              <span className="text-xs text-slate-400">Step 22C Engine</span>
            </div>

            <form onSubmit={handleCreateScenario} className="space-y-4">
              {/* Document Selection */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Baseline Document Scope
                </label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Portfolio-wide (All Documents)</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      #{doc.id} — {doc.filename || doc.original_filename || `Document #${doc.id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* Scenario Name */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Scenario Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  placeholder="e.g. FY25 Diesel -20% Optimization"
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              {/* Scenario Type */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Intervention Action Type
                </label>
                <select
                  value={scenarioType}
                  onChange={(e) => setScenarioType(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="REDUCE_ACTIVITY">Reduce Activity (Efficiency / Curtailment)</option>
                  <option value="INCREASE_ACTIVITY">Increase Activity (Capacity Expansion)</option>
                  <option value="REPLACE_SOURCE">Replace Source (e.g. Grid to Solar)</option>
                  <option value="SHIFT_SOURCE">Shift Source (e.g. Diesel to Biodiesel)</option>
                  <option value="ADD_SOURCE">Add Verified Source (New Equipment)</option>
                  <option value="REMOVE_SOURCE">Remove Source (Decommissioning)</option>
                </select>
              </div>

              {/* Target Activity Data */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Verified Activity Line
                </label>
                <select
                  value={targetActivityId}
                  onChange={(e) => setTargetActivityId(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {activityItems.length === 0 && (
                    <option value="">No baseline activity data found</option>
                  )}
                  {activityItems.map((act) => (
                    <option key={act.id} value={act.id}>
                      #{act.id} — {act.activity_type} ({act.normalized_quantity || act.raw_quantity} {act.normalized_unit || act.raw_unit || ''})
                    </option>
                  ))}
                </select>
              </div>

              {/* Change % (for REDUCE / INCREASE / ADD) */}
              {(scenarioType === 'REDUCE_ACTIVITY' || scenarioType === 'INCREASE_ACTIVITY' || scenarioType === 'ADD_SOURCE') && (
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs font-medium text-slate-300">
                      {scenarioType === 'REDUCE_ACTIVITY' ? 'Reduction Percentage (%)' : 'Change Percentage (%)'}
                    </label>
                    <span className="text-xs font-semibold text-indigo-400">{changePercent}%</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max={scenarioType === 'REDUCE_ACTIVITY' ? '100' : '200'}
                    value={changePercent}
                    onChange={(e) => setChangePercent(e.target.value)}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                    <span>1%</span>
                    <span>50%</span>
                    <span>{scenarioType === 'REDUCE_ACTIVITY' ? '100%' : '200%'}</span>
                  </div>
                </div>
              )}

              {/* Replacement parameters (for REPLACE / SHIFT) */}
              {(scenarioType === 'REPLACE_SOURCE' || scenarioType === 'SHIFT_SOURCE') && (
                <div className="space-y-3 pt-2 border-t border-slate-800">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Replacement Source Type
                    </label>
                    <select
                      value={replacementActivityType}
                      onChange={(e) => setReplacementActivityType(e.target.value)}
                      className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="solar_electricity">On-site Solar PV (solar_electricity)</option>
                      <option value="biodiesel">Biodiesel Fuel Blend (biodiesel)</option>
                      <option value="natural_gas">Natural Gas Switching (natural_gas)</option>
                      <option value="wind_electricity">Wind Power (wind_electricity)</option>
                      <option value="biomass">Biomass Fuel (biomass)</option>
                    </select>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-medium text-slate-300">
                        Replacement Share (%)
                      </label>
                      <span className="text-xs font-semibold text-indigo-400">{replacementPercent}%</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="100"
                      value={replacementPercent}
                      onChange={(e) => setReplacementPercent(e.target.value)}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>
                </div>
              )}

              {/* Linked Roadmap for Target Alignment */}
              {roadmaps.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Compare Against Roadmap Target (Optional)
                  </label>
                  <select
                    value={selectedRoadmapId}
                    onChange={(e) => setSelectedRoadmapId(e.target.value)}
                    className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">No Roadmap Selected</option>
                    {roadmaps.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.title || `Roadmap #${r.id}`} ({r.target_reduction_percent}% target by {r.target_year})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={creating}
                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-lg shadow-indigo-600/30"
              >
                {creating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Calculating Scenario...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate What-If Scenario
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Saved Scenarios List */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Saved Scenarios ({scenarios.length})</span>
              <Activity className="w-3.5 h-3.5 text-slate-500" />
            </h3>

            {scenarios.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">No scenarios saved yet. Use the builder above or click a quick template.</p>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {scenarios.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => selectScenario(s.id)}
                    className={`p-3 rounded-xl border transition cursor-pointer flex items-center justify-between gap-2 ${
                      activeScenario?.id === s.id
                        ? 'bg-indigo-950/60 border-indigo-500/50 text-white'
                        : 'bg-slate-800/40 border-slate-800 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium truncate">{s.name}</span>
                        {s.quantification_status === 'QUANTIFIED' ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-medium">
                            {s.reduction_percent ? `−${Number(s.reduction_percent).toFixed(1)}%` : 'Quantified'}
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-400 font-medium">
                            Unresolved Factor
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                        <span>{s.scenario_code}</span>
                        <span>•</span>
                        <span>{s.scenario_type}</span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Active Scenario Results & Analysis (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {activeScenario ? (
            <>
              {/* Scenario Header Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-lg space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                        {activeScenario.scenario_code}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {activeScenario.scenario_type}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        activeScenario.status === 'ARCHIVED'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {activeScenario.status}
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-white">{activeScenario.name}</h2>
                    {activeScenario.description && (
                      <p className="text-xs text-slate-400">{activeScenario.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRecalculate}
                      disabled={calculating}
                      className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition text-xs flex items-center gap-1.5"
                      title="Recalculate against updated emission factors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${calculating ? 'animate-spin' : ''}`} />
                      <span>Recalculate</span>
                    </button>
                    <button
                      onClick={() => handleArchive(activeScenario.id)}
                      className="p-2 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/40 text-rose-300 hover:text-rose-100 transition text-xs flex items-center gap-1.5"
                      title="Archive scenario"
                    >
                      <Archive className="w-3.5 h-3.5" />
                      <span>Archive</span>
                    </button>
                  </div>
                </div>

                {/* KPI Metrics Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {/* Baseline */}
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                      Baseline Footprint
                    </span>
                    <div className="text-xl font-bold text-white">
                      {activeScenario.baseline_emissions_tco2e !== null && activeScenario.baseline_emissions_tco2e !== undefined
                        ? `${Number(activeScenario.baseline_emissions_tco2e).toFixed(4)}`
                        : '—'}
                      <span className="text-xs font-normal text-slate-400 ml-1">tCO₂e</span>
                    </div>
                    <span className="text-[10px] text-slate-500 mt-1 block">
                      Period: {activeScenario.baseline_period || 'Verified Actual'}
                    </span>
                  </div>

                  {/* Modeled Scenario Footprint */}
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                      Modeled Footprint
                    </span>
                    {activeScenario.quantification_status === 'QUANTIFIED' && activeScenario.scenario_emissions_tco2e !== null ? (
                      <div className="text-xl font-bold text-indigo-300">
                        {Number(activeScenario.scenario_emissions_tco2e).toFixed(4)}
                        <span className="text-xs font-normal text-slate-400 ml-1">tCO₂e</span>
                      </div>
                    ) : (
                      <div className="text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-1 rounded inline-block">
                        NOT QUANTIFIABLE
                      </div>
                    )}
                    <span className="text-[10px] text-slate-500 mt-1 block">
                      {activeScenario.quantification_status === 'QUANTIFIED' ? 'Deterministic Result' : 'Factor Unresolved'}
                    </span>
                  </div>

                  {/* Modeled Reduction */}
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                      Modeled Reduction
                    </span>
                    {activeScenario.quantification_status === 'QUANTIFIED' && activeScenario.reduction_tco2e !== null ? (
                      <div className="text-xl font-bold text-emerald-400">
                        {Number(activeScenario.reduction_tco2e).toFixed(4)}
                        <span className="text-xs font-normal text-slate-400 ml-1">tCO₂e</span>
                      </div>
                    ) : (
                      <div className="text-xs font-medium text-slate-400">
                        NULL (Pending Factor)
                      </div>
                    )}
                    <span className="text-[10px] text-emerald-400 mt-1 block">
                      {activeScenario.reduction_percent !== null && activeScenario.reduction_percent !== undefined
                        ? `−${Number(activeScenario.reduction_percent).toFixed(2)}% of Baseline`
                        : 'No zero-substitution'}
                    </span>
                  </div>

                  {/* Target Status */}
                  <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                      Target Alignment
                    </span>
                    <div className="mt-0.5">
                      {activeScenario.target_status === 'TARGET_MET' && (
                        <span className="px-2 py-1 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Target Met
                        </span>
                      )}
                      {activeScenario.target_status === 'TARGET_NOT_MET' && (
                        <span className="px-2 py-1 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" /> Target Gap
                        </span>
                      )}
                      {activeScenario.target_status === 'SCENARIO_NOT_QUANTIFIABLE' && (
                        <span className="px-2 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
                          <HelpCircle className="w-3.5 h-3.5" /> Unquantifiable
                        </span>
                      )}
                      {activeScenario.target_status === 'TARGET_NOT_DEFINED' && (
                        <span className="px-2 py-1 rounded text-xs font-medium text-slate-400">
                          No Target Linked
                        </span>
                      )}
                    </div>
                    {activeScenario.remaining_target_gap_tco2e !== null && activeScenario.remaining_target_gap_tco2e !== undefined && (
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        Gap: {Number(activeScenario.remaining_target_gap_tco2e).toFixed(3)} tCO₂e
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* View Tabs */}
              <div className="flex border-b border-slate-800">
                <button
                  onClick={() => setViewTab('sources')}
                  className={`py-2.5 px-4 font-medium text-xs border-b-2 transition flex items-center gap-2 ${
                    viewTab === 'sources'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <BarChart2 className="w-3.5 h-3.5" />
                  Source Breakdown ({scenarioResults.length})
                </button>
                <button
                  onClick={() => setViewTab('assumptions')}
                  className={`py-2.5 px-4 font-medium text-xs border-b-2 transition flex items-center gap-2 ${
                    viewTab === 'assumptions'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Assumptions & Safeguard Disclosures
                </button>
                {activeScenario.roadmap_id && (
                  <button
                    onClick={() => setViewTab('target')}
                    className={`py-2.5 px-4 font-medium text-xs border-b-2 transition flex items-center gap-2 ${
                      viewTab === 'target'
                        ? 'border-indigo-500 text-indigo-400'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Target className="w-3.5 h-3.5" />
                    Roadmap Target Alignment
                  </button>
                )}
              </div>

              {/* Tab 1: Source-by-Source Breakdown Table */}
              {viewTab === 'sources' && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
                  <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Source-Level Impact & Factor Snapshots</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Full lineage showing baseline quantities vs modeled scenario quantities with locked emission factors.
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800/60 text-slate-300 uppercase tracking-wider font-semibold">
                        <tr>
                          <th className="py-3 px-4">Activity Source</th>
                          <th className="py-3 px-3">Scope</th>
                          <th className="py-3 px-3">Baseline Qty</th>
                          <th className="py-3 px-3">Scenario Qty</th>
                          <th className="py-3 px-3">Factor Snapshot</th>
                          <th className="py-3 px-3">Scenario Emissions</th>
                          <th className="py-3 px-3">Net Reduction</th>
                          <th className="py-3 px-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-200">
                        {scenarioResults.length === 0 ? (
                          <tr>
                            <td colSpan="8" className="py-6 text-center text-slate-500 italic">
                              No source results recorded for this scenario.
                            </td>
                          </tr>
                        ) : (
                          scenarioResults.map((res) => (
                            <tr key={res.id} className="hover:bg-slate-800/30 transition">
                              <td className="py-3.5 px-4">
                                <div className="font-medium text-white">{res.source_name}</div>
                                <div className="text-[11px] text-slate-400 font-mono">{res.activity_type}</div>
                              </td>
                              <td className="py-3.5 px-3">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                  res.scope === 'SCOPE_1'
                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                    : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                                }`}>
                                  {res.scope || 'N/A'}
                                </span>
                              </td>
                              <td className="py-3.5 px-3 font-mono">
                                {Number(res.baseline_quantity).toLocaleString()} {res.unit}
                              </td>
                              <td className="py-3.5 px-3 font-mono text-indigo-300 font-medium">
                                {Number(res.scenario_quantity).toLocaleString()} {res.unit}
                              </td>
                              <td className="py-3.5 px-3">
                                {res.scenario_factor !== null && res.scenario_factor !== undefined ? (
                                  <div>
                                    <span className="font-mono text-slate-200">{Number(res.scenario_factor).toFixed(4)}</span>
                                    <span className="text-[10px] text-slate-500 ml-1">{res.factor_unit || ''}</span>
                                    {res.factor_code && (
                                      <div className="text-[10px] text-slate-500 font-mono">{res.factor_code}</div>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                                    Unresolved
                                  </span>
                                )}
                              </td>
                              <td className="py-3.5 px-3 font-mono">
                                {res.scenario_emissions_kgco2e !== null ? (
                                  <span>{Number(res.scenario_emissions_kgco2e).toFixed(2)} kg</span>
                                ) : (
                                  <span className="text-amber-400">NULL</span>
                                )}
                              </td>
                              <td className="py-3.5 px-3 font-mono font-medium">
                                {res.reduction_kgco2e !== null ? (
                                  <span className={Number(res.reduction_kgco2e) >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                                    {Number(res.reduction_kgco2e) >= 0 ? '+' : ''}{Number(res.reduction_kgco2e).toFixed(2)} kg
                                  </span>
                                ) : (
                                  <span className="text-slate-500">NULL</span>
                                )}
                              </td>
                              <td className="py-3.5 px-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                                  res.status === 'QUANTIFIED'
                                    ? 'bg-emerald-500/10 text-emerald-400'
                                    : 'bg-amber-500/10 text-amber-400'
                                }`}>
                                  {res.status}
                                </span>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Tab 2: Assumptions & Methodological Disclosures */}
              {viewTab === 'assumptions' && (
                <div className="space-y-4">
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-400" />
                      Model Assumptions & Verification Lineage
                    </h3>

                    <div className="space-y-3">
                      <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                        <span className="text-xs font-semibold text-slate-300 block mb-1">Scenario Narrative</span>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {activeScenario.assumption_summary || 'Standard baseline modification modeled with deterministic factor math.'}
                        </p>
                      </div>

                      {activeScenario.limitation_summary && (
                        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200">
                          <span className="text-xs font-semibold flex items-center gap-1.5 mb-1 text-amber-300">
                            <AlertTriangle className="w-4 h-4" />
                            Methodological Limitations & Safeguards (Safeguard 3)
                          </span>
                          <p className="text-xs leading-relaxed text-amber-200">
                            {activeScenario.limitation_summary}
                          </p>
                          <p className="text-[11px] text-amber-300/80 mt-2 font-mono">
                            * Total modeled footprint and reduction percentage are kept NULL to prevent misleading carbon claims.
                          </p>
                        </div>
                      )}

                      <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-400 space-y-1">
                        <div>Calculation Engine Version: <span className="font-mono text-slate-200">{activeScenario.calculation_version || '1.0'}</span></div>
                        <div>Scenario State: <span className="text-slate-200">{activeScenario.status}</span></div>
                        <div>Created Timestamp: <span className="text-slate-200">{new Date(activeScenario.created_at).toLocaleString()}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Roadmap Target Alignment */}
              {viewTab === 'target' && activeScenario.roadmap_id && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Target className="w-4 h-4 text-indigo-400" />
                    Target Alignment vs Reduction Roadmap #{activeScenario.roadmap_id}
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                      <span className="text-[11px] text-slate-400 uppercase font-medium block mb-1">Target Status</span>
                      <span className="text-sm font-bold text-white">{activeScenario.target_status}</span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                      <span className="text-[11px] text-slate-400 uppercase font-medium block mb-1">Modeled Reduction</span>
                      <span className="text-sm font-bold text-emerald-400">
                        {activeScenario.reduction_tco2e !== null ? `${Number(activeScenario.reduction_tco2e).toFixed(4)} tCO₂e` : 'NULL'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800">
                      <span className="text-[11px] text-slate-400 uppercase font-medium block mb-1">Remaining Target Gap</span>
                      <span className="text-sm font-bold text-indigo-300">
                        {activeScenario.remaining_target_gap_tco2e !== null ? `${Number(activeScenario.remaining_target_gap_tco2e).toFixed(4)} tCO₂e` : '—'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-3">
              <Sliders className="w-12 h-12 text-slate-600 mx-auto" />
              <h3 className="text-base font-semibold text-slate-200">No Scenario Selected</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Configure a new scenario on the left or select a template above to simulate decarbonization outcomes.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmissionScenarios;
