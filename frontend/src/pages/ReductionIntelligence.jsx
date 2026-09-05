import React, { useState, useEffect } from 'react';
import { 
  Target, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Filter, 
  ChevronRight, 
  FileText, 
  Info, 
  Zap, 
  Flame, 
  Layers, 
  ShieldAlert, 
  X,
  ExternalLink,
  Award,
  BarChart3,
  Lightbulb
} from 'lucide-react';
import { 
  getReductionIntelligencePriorities, 
  getReductionIntelligenceSummary, 
  recalculateReductionIntelligence 
} from '../services/api';

export default function ReductionIntelligence({ onSelectDocument, onSelectOpportunity }) {
  const [priorities, setPriorities] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [selectedPriority, setSelectedPriority] = useState(null);
  const [error, setError] = useState(null);

  // Filters
  const [scopeFilter, setScopeFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (scopeFilter) params.scope = scopeFilter;
      if (levelFilter) params.priority_level = levelFilter;
      if (categoryFilter) params.category = categoryFilter;

      const [prioritiesData, summaryData] = await Promise.all([
        getReductionIntelligencePriorities(params),
        getReductionIntelligenceSummary()
      ]);

      setPriorities(prioritiesData.items || []);
      setSummary(summaryData);
    } catch (err) {
      console.error('Failed to load reduction intelligence data:', err);
      setError('Failed to load reduction intelligence data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [scopeFilter, levelFilter, categoryFilter]);

  const handleRecalculate = async () => {
    try {
      setRecalculating(true);
      await recalculateReductionIntelligence();
      await loadData();
    } catch (err) {
      console.error('Recalculation failed:', err);
      alert('Recalculation failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setRecalculating(false);
    }
  };

  const getLevelBadgeClass = (level) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'HIGH':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'MEDIUM':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'LOW':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-purple-50 text-purple-700 border-purple-200';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-[#0F6B56] text-white flex items-center justify-center font-bold shadow-xs">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Reduction Intelligence</h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Where should you focus first to reduce emissions? (Deterministic Decision Support v1.0)
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-[#0F6B56] text-white text-xs font-semibold hover:bg-[#0d5947] disabled:opacity-50 transition-colors shadow-2xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${recalculating ? 'animate-spin' : ''}`} />
            <span>{recalculating ? 'Recalculating...' : 'Recalculate Priorities'}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Top Priority */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Top Priority</span>
            <Target className="w-4 h-4 text-[#0F6B56]" />
          </div>
          <div className="mt-2">
            <div className="text-sm font-bold text-slate-900 truncate" title={summary?.top_priority || 'None'}>
              {summary?.top_priority || 'No Priorities Yet'}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs font-semibold text-[#0F6B56]">
                Score: {summary?.top_priority_score ? Math.round(summary.top_priority_score) : 0}/100
              </span>
              <span className="text-[11px] text-slate-400">Rank #1</span>
            </div>
          </div>
        </div>

        {/* High Priority Areas */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">High Priority Areas</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-slate-900">
              {(summary?.critical || 0) + (summary?.high || 0)}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              {summary?.critical || 0} Critical, {summary?.high || 0} High focus areas
            </div>
          </div>
        </div>

        {/* Total Opportunities */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Opportunities</span>
            <Lightbulb className="w-4 h-4 text-blue-600" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-slate-900">
              {summary?.total_priorities || 0}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              Across all recorded scopes & activities
            </div>
          </div>
        </div>

        {/* Data Quality Blockers */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Data Quality Blockers</span>
            <ShieldAlert className="w-4 h-4 text-purple-600" />
          </div>
          <div className="mt-2">
            <div className="text-xs font-medium text-slate-800 line-clamp-2" title={summary?.data_quality_blockers || 'None'}>
              {summary?.data_quality_blockers || 'No critical blockers identified'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Resolution required for verified reporting
            </div>
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span>Filters:</span>
        </div>

        <select
          value={scopeFilter}
          onChange={(e) => setScopeFilter(e.target.value)}
          className="text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white text-slate-700 focus:outline-hidden focus:border-[#0F6B56]"
        >
          <option value="">All Scopes</option>
          <option value="SCOPE_1">Scope 1</option>
          <option value="SCOPE_2">Scope 2</option>
          <option value="SCOPE_3">Scope 3</option>
        </select>

        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white text-slate-700 focus:outline-hidden focus:border-[#0F6B56]"
        >
          <option value="">All Priority Levels</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
          <option value="INFORMATIONAL">Informational</option>
        </select>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white text-slate-700 focus:outline-hidden focus:border-[#0F6B56]"
        >
          <option value="">All Categories</option>
          <option value="ENERGY">Energy</option>
          <option value="FUEL">Fuel</option>
          <option value="TRANSPORT">Transport</option>
          <option value="WATER">Water</option>
          <option value="WASTE">Waste</option>
          <option value="DATA_QUALITY">Data Quality</option>
        </select>

        {(scopeFilter || levelFilter || categoryFilter) && (
          <button
            onClick={() => {
              setScopeFilter('');
              setLevelFilter('');
              setCategoryFilter('');
            }}
            className="text-xs text-slate-500 hover:text-slate-800 underline ml-auto cursor-pointer"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Priorities List */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-white p-8 rounded-lg border border-slate-200 text-center">
            <RefreshCw className="w-6 h-6 text-[#0F6B56] animate-spin mx-auto" />
            <p className="text-xs text-slate-500 mt-2">Evaluating reduction priorities from carbon ledger...</p>
          </div>
        ) : priorities.length === 0 ? (
          <div className="bg-white p-8 rounded-lg border border-slate-200 text-center">
            <Target className="w-8 h-8 text-slate-300 mx-auto" />
            <h3 className="text-sm font-semibold text-slate-900 mt-2">No Reduction Priorities Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              No reduction priorities currently match your filter criteria. Ensure POSTED carbon ledger records exist.
            </p>
          </div>
        ) : (
          priorities.map((p) => {
            const isDq = p.data_quality_score > 0 || p.blocker_score > 0;
            return (
              <div
                key={p.id || p.priority_code}
                className="bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-all p-4 shadow-2xs hover:shadow-xs"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  
                  {/* Left Column: Rank, Title, Level, Reason */}
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-slate-900 text-white">
                        Rank #{p.priority_rank || 1}
                      </span>

                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${getLevelBadgeClass(p.priority_level)}`}>
                        {p.priority_level}
                      </span>

                      {p.scope && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                          {p.scope}
                        </span>
                      )}

                      {p.category && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                          {p.category}
                        </span>
                      )}

                      {isDq && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                          DATA QUALITY
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 truncate">
                      {p.title}
                    </h3>

                    <p className="text-xs text-slate-600 line-clamp-2">
                      {p.reason}
                    </p>
                  </div>

                  {/* Middle Column: Emissions & Signals */}
                  <div className="flex flex-wrap lg:flex-nowrap items-center gap-6 text-xs text-slate-600 border-t lg:border-t-0 pt-3 lg:pt-0 border-slate-100">
                    
                    {/* Score Bar */}
                    <div className="w-24">
                      <div className="flex justify-between items-center text-[11px] mb-1">
                        <span className="font-semibold text-slate-700">Score</span>
                        <span className="font-bold text-[#0F6B56]">{Math.round(p.priority_score)}/100</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className="bg-[#0F6B56] h-1.5 rounded-full transition-all"
                          style={{ width: `${Math.min(100, Math.max(0, p.priority_score))}%` }}
                        />
                      </div>
                    </div>

                    {/* Emissions */}
                    <div className="min-w-[100px]">
                      <span className="text-[10px] text-slate-400 block uppercase font-medium">Emissions</span>
                      <span className="font-bold text-slate-900 text-xs">
                        {p.current_emissions_tco2e ? `${p.current_emissions_tco2e.toFixed(4)} t` : '0.0000 t'}
                      </span>
                      <span className="text-[11px] text-slate-400 block">
                        {p.current_emissions_kgco2e ? `${(p.current_emissions_kgco2e).toLocaleString()} kg` : '0 kg'}
                      </span>
                    </div>

                    {/* Trend */}
                    <div className="min-w-[80px]">
                      <span className="text-[10px] text-slate-400 block uppercase font-medium">Trend</span>
                      {p.change_percent !== null && p.change_percent !== undefined ? (
                        <span className={`font-semibold text-xs ${p.change_percent > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                          {p.change_percent > 0 ? `+${p.change_percent.toFixed(1)}%` : `${p.change_percent.toFixed(1)}%`}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">Single Period</span>
                      )}
                    </div>

                    {/* Forecast */}
                    <div className="min-w-[90px]">
                      <span className="text-[10px] text-slate-400 block uppercase font-medium">Step 21 Forecast</span>
                      <span className="text-xs font-medium text-slate-700">
                        {p.forecast_emissions_kgco2e ? `${(p.forecast_emissions_kgco2e / 1000).toFixed(2)} t` : 'Unavailable'}
                      </span>
                    </div>

                    {/* Action Button */}
                    <div>
                      <button
                        onClick={() => setSelectedPriority(p)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold text-[#0F6B56] hover:bg-[#EAF7F2] border border-[#0F6B56]/20 transition-colors cursor-pointer"
                      >
                        <span>View Evidence</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>

                  </div>

                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Detail Modal */}
      {selectedPriority && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full p-6 shadow-xl border border-slate-200 relative animate-in fade-in duration-150">
            
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-3 border-b border-slate-200">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-900 text-white">
                    Rank #{selectedPriority.priority_rank}
                  </span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${getLevelBadgeClass(selectedPriority.priority_level)}`}>
                    {selectedPriority.priority_level}
                  </span>
                  <span className="text-xs font-bold text-[#0F6B56]">
                    Overall Score: {Math.round(selectedPriority.priority_score)}/100
                  </span>
                </div>
                <h2 className="text-base font-bold text-slate-900 mt-1">
                  {selectedPriority.title}
                </h2>
              </div>

              <button
                onClick={() => setSelectedPriority(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="py-4 space-y-4 text-xs text-slate-700 max-h-[70vh] overflow-y-auto pr-1">
              
              {/* Grounded Narrative */}
              <div className="bg-slate-50 p-3 rounded border border-slate-200">
                <span className="font-semibold text-slate-900 block mb-1">Grounded Intelligence Reason:</span>
                <p className="text-slate-700 leading-relaxed">
                  {selectedPriority.reason}
                </p>
              </div>

              {/* Transparent Score Breakdown */}
              <div>
                <h4 className="font-bold text-slate-900 text-xs mb-2 uppercase tracking-wide">
                  Transparent Score Breakdown (Sum: {Math.round(selectedPriority.priority_score)}/100)
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  
                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Impact</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.impact_score} / 30</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Share of posted CO2e</span>
                  </div>

                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Trend</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.trend_score} / 20</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Period-over-period rise</span>
                  </div>

                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Forecast</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.forecast_score} / 15</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Step 21 projection</span>
                  </div>

                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Persistence</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.persistence_score} / 15</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Reporting periods</span>
                  </div>

                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Actionability</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.actionability_score} / 10</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Concrete action</span>
                  </div>

                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Data Quality</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.data_quality_score} / 5</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Factor/evidence quality</span>
                  </div>

                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">Blocker</span>
                    <span className="text-sm font-bold text-slate-900">{selectedPriority.blocker_score} / 5</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Critical obstacle</span>
                  </div>

                </div>
              </div>

              {/* Lineage & Provenance */}
              <div className="border-t border-slate-200 pt-3 space-y-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wide">
                  Lineage & Evidence Lineage
                </h4>
                <div className="bg-slate-50 p-3 rounded border border-slate-200 space-y-1.5 font-mono text-[11px]">
                  <div>
                    <span className="text-slate-500">Priority Code: </span>
                    <span className="font-semibold text-slate-800">{selectedPriority.priority_code}</span>
                  </div>
                  {selectedPriority.document_id && (
                    <div>
                      <span className="text-slate-500">Source Document: </span>
                      <span className="font-semibold text-slate-800">Document #{selectedPriority.document_id}</span>
                    </div>
                  )}
                  {selectedPriority.opportunity_id && (
                    <div>
                      <span className="text-slate-500">Linked Opportunity: </span>
                      <span className="font-semibold text-slate-800">ReductionOpportunity #{selectedPriority.opportunity_id}</span>
                    </div>
                  )}
                  {selectedPriority.source_reference && (
                    <div>
                      <span className="text-slate-500">Source Reference: </span>
                      <span className="text-slate-800">{selectedPriority.source_reference}</span>
                    </div>
                  )}
                  {selectedPriority.evidence_reference && (
                    <div>
                      <span className="text-slate-500">Evidence Lineage: </span>
                      <span className="text-slate-800">{selectedPriority.evidence_reference}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Product Boundary Notice */}
              <div className="text-[11px] text-slate-500 bg-amber-50/60 p-2.5 rounded border border-amber-200/60">
                <strong>Decision Support Boundary:</strong> Priority scores reflect deterministic materiality and trends across POSTED accounting ledger entries. Does not predict hypothetical cost savings, ROI, or emission reductions without verified engineering scenarios.
              </div>

            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedPriority(null)}
                className="px-4 py-2 rounded bg-slate-100 text-slate-700 text-xs font-semibold hover:bg-slate-200 transition-colors cursor-pointer"
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
