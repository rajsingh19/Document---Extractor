import React, { useState, useEffect, useCallback } from 'react';
import { 
  Sparkles, 
  Play, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  ArrowRight, 
  HelpCircle, 
  Filter, 
  TrendingUp, 
  Layers, 
  Sliders, 
  ShieldAlert, 
  Database, 
  X, 
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Info,
  Check,
  Ban
} from 'lucide-react';
import { 
  getAgentBrief, 
  runAgent, 
  getAgentActions, 
  startAgentAction, 
  completeAgentAction, 
  dismissAgentAction, 
  explainAgentAction 
} from '../services/api';

export default function AgentCenter({ onSelectDocument, onOpenCopilotQuery }) {
  const [brief, setBrief] = useState(null);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [actionInProgressId, setActionInProgressId] = useState(null);
  const [explanationModalAction, setExplanationModalAction] = useState(null);
  const [explanationData, setExplanationData] = useState(null);
  const [explaining, setExplaining] = useState(false);

  // Queue Filter state
  const [selectedQueue, setSelectedQueue] = useState('ALL'); // 'ALL' | 'REDUCTION' | 'DATA_QUALITY'
  const [selectedStatus, setSelectedStatus] = useState('ACTIVE'); // 'ACTIVE' | 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'DISMISSED' | 'ALL'
  const [selectedPriority, setSelectedPriority] = useState('ALL');

  // Load Brief and Actions
  const loadAgentData = useCallback(async () => {
    try {
      setLoading(true);
      const [briefData, actionsData] = await Promise.all([
        getAgentBrief(),
        getAgentActions({ limit: 100 })
      ]);
      setBrief(briefData);
      setActions(actionsData.actions || []);
    } catch (err) {
      console.error('Failed to load agent data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAgentData();
  }, [loadAgentData]);

  // Handle Run Agent
  const handleRunAgent = async () => {
    try {
      setRunning(true);
      await runAgent({ force_recalculate: false });
      await loadAgentData();
    } catch (err) {
      console.error('Error running agent:', err);
    } finally {
      setRunning(false);
    }
  };

  // Action Lifecycle handlers
  const handleStartAction = async (actionId) => {
    try {
      setActionInProgressId(actionId);
      await startAgentAction(actionId, 'Started from Agent Center');
      await loadAgentData();
    } catch (err) {
      console.error('Failed to start action:', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleCompleteAction = async (actionId) => {
    try {
      setActionInProgressId(actionId);
      await completeAgentAction(actionId, 'Completed from Agent Center');
      await loadAgentData();
    } catch (err) {
      console.error('Failed to complete action:', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleDismissAction = async (actionId) => {
    try {
      setActionInProgressId(actionId);
      await dismissAgentAction(actionId, 'Dismissed from Agent Center');
      await loadAgentData();
    } catch (err) {
      console.error('Failed to dismiss action:', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Explanation Modal handler (Patch 5)
  const handleExplainAction = async (action) => {
    setExplanationModalAction(action);
    setExplaining(true);
    try {
      const data = await explainAgentAction(action.id);
      setExplanationData(data);
    } catch (err) {
      console.error('Failed to fetch explanation:', err);
    } finally {
      setExplaining(false);
    }
  };

  // Filter actions for the table
  const filteredActions = actions.filter((act) => {
    if (selectedQueue !== 'ALL' && act.queue_type !== selectedQueue) return false;
    if (selectedStatus === 'ACTIVE' && !['OPEN', 'IN_PROGRESS'].includes(act.status)) return false;
    if (selectedStatus !== 'ACTIVE' && selectedStatus !== 'ALL' && act.status !== selectedStatus) return false;
    if (selectedPriority !== 'ALL' && act.priority !== selectedPriority) return false;
    return true;
  });

  const getPriorityBadgeClass = (priority) => {
    switch (priority) {
      case 'CRITICAL':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'HIGH':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'MEDIUM':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'LOW':
        return 'bg-slate-50 text-slate-700 border-slate-200';
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Not yet evaluated';
    try {
      return new Date(ts).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* ------------------------------------------------------------- */}
      {/* SECTION 1: HEADER & AI SUSTAINABILITY BRIEF (Patch 4 & 9) */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-[#EAF7F2] text-[#0F6B56] flex items-center justify-center font-bold">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">AI Sustainability Agent</h1>
                <p className="text-xs text-slate-500">Grounded actions based on your latest sustainability data.</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-2xs font-semibold uppercase tracking-wider text-slate-400">Last Evaluated</p>
              <p className="text-xs font-medium text-slate-700">
                {formatTimestamp(brief?.last_evaluated)}
              </p>
            </div>
            <button
              onClick={handleRunAgent}
              disabled={running}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#0F6B56] hover:bg-[#0c5746] text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
              <span>{running ? 'Evaluating...' : 'Run Agent'}</span>
            </button>
          </div>
        </div>

        {/* AI Sustainability Brief KPI Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6">
          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500">Latest Actual Period</span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold text-slate-900">{brief?.current_period || 'None'}</span>
              <span className="text-3xs font-semibold px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded">ACTUAL</span>
            </div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500">Posted Footprint</span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold text-slate-900">
                {brief?.current_posted_footprint !== undefined ? `${brief.current_posted_footprint.toFixed(4)}` : '0.0000'}
              </span>
              <span className="text-2xs font-medium text-slate-600">tCO2e</span>
            </div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500">Pending Actions</span>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-base font-bold text-slate-900">{brief?.open_action_count || 0}</span>
              {(brief?.critical_count > 0 || brief?.high_count > 0) && (
                <span className="text-3xs font-semibold px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded">
                  {brief.critical_count + brief.high_count} High Priority
                </span>
              )}
            </div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500">Ready Next Actions</span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold text-emerald-700">{brief?.ready_actions?.length || 0}</span>
              <span className="text-3xs font-semibold px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded">READY</span>
            </div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 2: TODAY'S PRIORITIES (REDUCTION QUEUE A) (Patch 2 & 9) */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#0F6B56]" />
              <span>Today's Priorities — Emissions Reduction</span>
              <span className="text-3xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                Queue A
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Directly inherited from Step 22A Reduction Intelligence. Authoritative ranking based on posted ledger actuals.
            </p>
          </div>
        </div>

        {brief?.top_actions?.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-900">No active reduction priorities pending.</p>
            <p className="text-xs text-slate-500 mt-1">Run the agent or ingest new actual reporting periods to evaluate.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {brief?.top_actions?.slice(0, 3).map((act) => (
              <div 
                key={act.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs hover:shadow-xs transition-shadow flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className={`text-3xs font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${getPriorityBadgeClass(act.priority)}`}>
                      {act.priority}
                    </span>
                    <span className={`text-3xs font-semibold px-1.5 py-0.5 rounded ${
                      act.dependency_status === 'READY' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {act.dependency_status}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-slate-900 line-clamp-2">{act.title}</h3>
                    <p className="text-xs text-slate-600 mt-1 line-clamp-3">{act.why_it_matters}</p>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-xs">
                    <p className="text-3xs font-bold text-slate-400 uppercase tracking-wider">Recommended Next Step</p>
                    <p className="text-xs text-slate-700 font-medium mt-0.5 line-clamp-2">{act.recommended_action}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                  <button
                    onClick={() => handleExplainAction(act)}
                    className="text-xs text-slate-600 hover:text-slate-900 font-medium flex items-center gap-1"
                  >
                    <Info className="w-3.5 h-3.5 text-slate-400" />
                    <span>Explain</span>
                  </button>

                  <div className="flex items-center gap-1.5">
                    {act.status === 'OPEN' && (
                      <button
                        onClick={() => handleStartAction(act.id)}
                        disabled={actionInProgressId === act.id}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-2xs font-semibold rounded"
                      >
                        Start
                      </button>
                    )}
                    {act.status !== 'COMPLETED' && (
                      <button
                        onClick={() => handleCompleteAction(act.id)}
                        disabled={actionInProgressId === act.id}
                        className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-2xs font-semibold rounded flex items-center gap-1"
                      >
                        <Check className="w-3 h-3" />
                        <span>Done</span>
                      </button>
                    )}
                    <button
                      onClick={() => handleDismissAction(act.id)}
                      disabled={actionInProgressId === act.id}
                      className="p-1 text-slate-400 hover:text-slate-600 rounded"
                      title="Dismiss Action"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 3: DATA QUALITY BLOCKERS (QUEUE B) (Patch 2 & 9) */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>Data Quality Blockers</span>
            <span className="text-3xs font-semibold px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full">
              Queue B
            </span>
          </h2>
          <p className="text-xs text-slate-500">
            Unresolved factors, unverified activity, or missing evidence that block carbon accounting and what-if simulation.
          </p>
        </div>

        {brief?.data_quality_blockers?.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-6 text-center text-xs text-slate-500">
            No active data quality blockers. All recorded activity data factors are resolved.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {brief?.data_quality_blockers?.map((dq) => (
              <div 
                key={dq.id}
                className="bg-amber-50/40 border border-amber-200/80 rounded-xl p-5 flex flex-col justify-between space-y-4 shadow-2xs"
              >
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-3xs font-bold px-2 py-0.5 bg-amber-100 text-amber-800 rounded border border-amber-200">
                      DATA QUALITY
                    </span>
                    <span className="text-3xs font-semibold px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded">
                      {dq.dependency_status}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900">{dq.title}</h3>
                  <p className="text-xs text-slate-600">{dq.why_it_matters}</p>

                  <div className="p-2.5 bg-white/80 rounded-lg border border-amber-100 text-xs">
                    <p className="text-3xs font-bold text-amber-800 uppercase tracking-wider">Required Resolution</p>
                    <p className="text-xs text-slate-800 font-medium mt-0.5">{dq.recommended_action}</p>
                  </div>
                </div>

                <div className="pt-3 border-t border-amber-200/60 flex items-center justify-between">
                  <button
                    onClick={() => handleExplainAction(dq)}
                    className="text-xs text-amber-900 hover:text-amber-950 font-medium flex items-center gap-1"
                  >
                    <Info className="w-3.5 h-3.5" />
                    <span>Explain</span>
                  </button>

                  <button
                    onClick={() => handleCompleteAction(dq.id)}
                    disabled={actionInProgressId === dq.id}
                    className="px-3 py-1 bg-amber-700 hover:bg-amber-800 text-white text-2xs font-semibold rounded flex items-center gap-1 shadow-2xs"
                  >
                    <Check className="w-3 h-3" />
                    <span>Mark Resolved</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 4, 5, 6, 7: WHAT CHANGED, FORECAST, ROADMAP, SCENARIO */}
      {/* ------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* What Changed */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-slate-600" />
              <span>What Changed</span>
            </h3>
            <span className="text-3xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded">
              ACTUAL PERIODS ONLY
            </span>
          </div>
          
          {(!brief?.recent_changes || brief.recent_changes.length === 0) ? (
            <p className="text-xs text-slate-500 italic">
              Only 1 actual reporting period ({brief?.current_period || 'October 2024'}) is currently posted. A period-over-period change requires at least 2 consecutive actual periods.
            </p>
          ) : (
            <div className="space-y-2">
              {brief.recent_changes.map((chg, idx) => (
                <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-900">{chg.metric_name}</span>
                    <p className="text-2xs text-slate-500">{chg.previous_period} → {chg.current_period}</p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-bold ${chg.is_increase ? 'text-red-600' : 'text-emerald-600'}`}>
                      {chg.is_increase ? '+' : ''}{chg.delta_tco2e.toFixed(4)} tCO2e ({chg.change_percent.toFixed(1)}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Forecast Signal (Patch 8) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-indigo-600" />
              <span>Forecast Signal</span>
            </h3>
            <span className="text-3xs font-bold px-2 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded">
              FORECAST — NOT ACTUAL
            </span>
          </div>

          <div className="p-3 bg-indigo-50/40 rounded-lg border border-indigo-100 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold text-indigo-900 uppercase">Trend Direction</span>
              <span className="text-xs font-bold text-indigo-950">{brief?.forecast_signal?.trend || 'STABLE'}</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {brief?.forecast_signal?.explanation || 'Predictive emissions analytics model projections.'}
            </p>
          </div>
        </div>

        {/* Roadmap Progress */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-emerald-600" />
              <span>Roadmap Progress</span>
            </h3>
            <span className="text-3xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded">
              STEP 22B
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">Phase: <strong>{brief?.roadmap_status?.phase || 'PHASE_1_FOUNDATION'}</strong></span>
              <span className="font-bold text-slate-900">{brief?.roadmap_status?.progress_percent || 0}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div 
                className="bg-emerald-600 h-2 rounded-full transition-all"
                style={{ width: `${brief?.roadmap_status?.progress_percent || 0}%` }}
              />
            </div>
            <p className="text-2xs text-slate-500">
              {brief?.roadmap_status?.completed_items || 0} of {brief?.roadmap_status?.total_items || 0} milestones completed.
            </p>
          </div>
        </div>

        {/* Scenario Status (Patch 8) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>Scenario Status</span>
            </h3>
            <span className="text-3xs font-bold px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded">
              SCENARIO — NOT ACTUAL
            </span>
          </div>

          <div className="p-3 bg-blue-50/40 rounded-lg border border-blue-100 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-2xs font-semibold text-blue-900 uppercase">Active Scenarios</span>
              <span className="text-xs font-bold text-blue-950">{brief?.scenario_status?.total_scenarios || 0}</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {brief?.scenario_status?.notes || 'No active scenarios modeled.'}
            </p>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 8: FULL ACTION QUEUE (FILTERABLE) */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Comprehensive Action Queue</h3>
            <p className="text-xs text-slate-500">Traceable actions across emissions, data quality, roadmap, and compliance.</p>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <select
              value={selectedQueue}
              onChange={(e) => setSelectedQueue(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-medium focus:ring-1 focus:ring-emerald-600 outline-hidden"
            >
              <option value="ALL">All Queues</option>
              <option value="REDUCTION">Reduction (Queue A)</option>
              <option value="DATA_QUALITY">Data Quality (Queue B)</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-medium focus:ring-1 focus:ring-emerald-600 outline-hidden"
            >
              <option value="ACTIVE">Active (Open + In Progress)</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="DISMISSED">Dismissed</option>
              <option value="ALL">All Statuses</option>
            </select>

            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-medium focus:ring-1 focus:ring-emerald-600 outline-hidden"
            >
              <option value="ALL">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 uppercase tracking-wider font-semibold text-3xs">
              <tr>
                <th className="px-5 py-3">Priority</th>
                <th className="px-5 py-3">Queue</th>
                <th className="px-5 py-3">Action</th>
                <th className="px-5 py-3">Dependency</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredActions.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-5 py-8 text-center text-slate-400">
                    No actions match the selected filter criteria.
                  </td>
                </tr>
              ) : (
                filteredActions.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className={`text-3xs font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${getPriorityBadgeClass(a.priority)}`}>
                        {a.priority}
                      </span>
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className="text-2xs font-medium text-slate-600">
                        {a.queue_type === 'REDUCTION' ? 'Reduction' : 'Data Quality'}
                      </span>
                    </td>
                    <td className="px-5 py-3 max-w-md">
                      <div className="font-semibold text-slate-900 line-clamp-1">{a.title}</div>
                      <div className="text-2xs text-slate-500 line-clamp-1 mt-0.5">{a.summary}</div>
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className={`text-3xs font-semibold px-2 py-0.5 rounded ${
                        a.dependency_status === 'READY' ? 'bg-emerald-50 text-emerald-700' :
                        a.dependency_status === 'BLOCKED' ? 'bg-amber-50 text-amber-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {a.dependency_status}
                      </span>
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className="text-2xs font-medium text-slate-700">
                        {a.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => handleExplainAction(a)}
                          className="text-2xs text-[#0F6B56] hover:underline font-medium"
                        >
                          Explain
                        </button>
                        {a.status === 'OPEN' && (
                          <button
                            onClick={() => handleStartAction(a.id)}
                            className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-3xs font-semibold rounded"
                          >
                            Start
                          </button>
                        )}
                        {a.status !== 'COMPLETED' && (
                          <button
                            onClick={() => handleCompleteAction(a.id)}
                            className="px-2 py-0.5 bg-emerald-600 hover:bg-emerald-700 text-white text-3xs font-semibold rounded"
                          >
                            Complete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* SECTION 9: STRUCTURED EXPLANATION MODAL (Patch 5) */}
      {/* ------------------------------------------------------------- */}
      {explanationModalAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-slate-200 max-w-xl w-full p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="text-3xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Grounded Decision Support
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-1">{explanationModalAction.title}</h3>
              </div>
              <button
                onClick={() => setExplanationModalAction(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {explaining ? (
              <div className="py-8 text-center text-xs text-slate-500">Loading grounded explanation contract...</div>
            ) : (
              <div className="space-y-3.5 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-3xs font-bold uppercase tracking-wider text-slate-400">WHAT</span>
                  <p className="text-slate-900 font-medium mt-0.5">{explanationData?.what || explanationModalAction.what || explanationModalAction.title}</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-3xs font-bold uppercase tracking-wider text-slate-400">WHY</span>
                  <p className="text-slate-700 mt-0.5">{explanationData?.why || explanationModalAction.why || explanationModalAction.why_it_matters}</p>
                </div>

                <div className="p-3 bg-emerald-50/50 rounded-lg border border-emerald-100">
                  <span className="text-3xs font-bold uppercase tracking-wider text-emerald-800">RECOMMENDED NEXT STEP</span>
                  <p className="text-emerald-950 font-medium mt-0.5">{explanationData?.next || explanationModalAction.next || explanationModalAction.recommended_action}</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-3xs font-bold uppercase tracking-wider text-slate-400">EVIDENCE & PROVENANCE</span>
                  <p className="text-slate-600 mt-0.5">{explanationData?.evidence || explanationModalAction.evidence || 'Posted Carbon Ledger and Activity Data snapshots.'}</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-3xs font-bold uppercase tracking-wider text-slate-400">FOLLOW-UP CHECK</span>
                  <p className="text-slate-600 mt-0.5">{explanationData?.follow_up || explanationModalAction.follow_up || 'Compare subsequent reporting period actuals against baseline.'}</p>
                </div>

                <div className="p-3 bg-amber-50/50 rounded-lg border border-amber-100">
                  <span className="text-3xs font-bold uppercase tracking-wider text-amber-800">OPERATIONAL LIMITATION</span>
                  <p className="text-amber-900 text-2xs mt-0.5">{explanationData?.limitation || explanationModalAction.limitation || 'Recommendations do not guarantee savings without completed intervention implementation.'}</p>
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setExplanationModalAction(null)}
                className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
