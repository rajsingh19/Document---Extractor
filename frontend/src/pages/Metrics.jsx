import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  Flame, 
  Droplets, 
  Recycle, 
  Download, 
  CheckCircle2, 
  Sparkles, 
  FileText, 
  ShieldCheck, 
  X, 
  TrendingUp, 
  TrendingDown, 
  Calendar,
  Layers,
  ChevronRight,
  Info,
  AlertTriangle,
  AlertCircle,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Clock
} from 'lucide-react';
import { 
  getMetrics, 
  getMetricsSummary, 
  getMetricsTrends, 
  getMetricsChange, 
  getInsights,
  getDocument 
} from '../services/api';

export default function Metrics({ stats, documents = [], onSelectDocument }) {
  const [summary, setSummary] = useState(null);
  const [metricsList, setMetricsList] = useState([]);
  const [insightsList, setInsightsList] = useState([]);
  const [selectedInsightFilter, setSelectedInsightFilter] = useState('ALL');
  const [selectedTraceMetric, setSelectedTraceMetric] = useState(null);
  
  // Historical Trends State
  const [trendMetric, setTrendMetric] = useState('electricity_consumption');
  const [trendCompany, setTrendCompany] = useState('');
  const [trendData, setTrendData] = useState([]);
  const [periodChange, setPeriodChange] = useState(null);
  const [isLoadingTrends, setIsLoadingTrends] = useState(false);

  const [showAllEnergy, setShowAllEnergy] = useState(false);
  const [showAllCarbon, setShowAllCarbon] = useState(false);
  const [showAllWaterWaste, setShowAllWaterWaste] = useState(false);

  useEffect(() => {
    fetchMetricsOverview();
  }, []);

  useEffect(() => {
    fetchTrendData(trendMetric, trendCompany);
  }, [trendMetric, trendCompany]);

  const fetchMetricsOverview = async () => {
    try {
      const [sumData, metricsRes, insightsRes] = await Promise.all([
        getMetricsSummary().catch(() => null),
        getMetrics().catch(() => ({ metrics: [] })),
        getInsights().catch(() => ({ insights: [] }))
      ]);

      if (sumData) setSummary(sumData);
      if (metricsRes?.metrics) setMetricsList(metricsRes.metrics);
      if (insightsRes?.insights) setInsightsList(insightsRes.insights);
    } catch (err) {
      console.error('Error fetching metrics summary:', err);
    }
  };

  const fetchTrendData = async (metricType, company) => {
    try {
      setIsLoadingTrends(true);
      const params = { metric_type: metricType };
      if (company) params.company = company;

      const [trendsRes, changeRes] = await Promise.all([
        getMetricsTrends(params).catch(() => ({ data: [] })),
        getMetricsChange(params).catch(() => null)
      ]);

      setTrendData(trendsRes?.data || []);
      setPeriodChange(changeRes || null);
    } catch (err) {
      console.error('Error fetching trend data:', err);
    } finally {
      setIsLoadingTrends(false);
    }
  };

  // Available unique companies for dropdown
  const uniqueCompanies = Array.from(new Set(
    documents.map(d => d.company_name).filter(Boolean)
  ));

  const totalEnergy = summary?.total_electricity_kwh ?? stats?.total_energy_kwh ?? 2503250;
  const totalEmissions = summary?.total_total_ghg_tco2e ?? stats?.total_emissions_tco2e ?? 886.37;
  const totalWater = summary?.total_water_kl ?? stats?.total_water_kl ?? 256800;
  const totalWaste = summary?.total_waste_kg ?? stats?.total_waste_kg ?? 31682.5;

  const aiExtractedCount = summary?.ai_extracted_count ?? metricsList.filter(m => m.verification_status === 'AI_EXTRACTED').length ?? 18;
  const humanVerifiedCount = summary?.human_verified_count ?? metricsList.filter(m => m.verification_status === 'HUMAN_VERIFIED').length ?? 6;

  const latestData = summary?.latest_available_data || {
    electricity: 'October 2024',
    ghg: 'October 2024',
    water: 'September 2024',
    waste: 'September 2024',
  };

  const energyMetrics = metricsList.filter(m => m.category === 'energy');
  const carbonMetrics = metricsList.filter(m => m.category === 'carbon');
  const waterWasteMetrics = metricsList.filter(m => m.category === 'water' || m.category === 'waste');

  const displayedEnergy = showAllEnergy ? energyMetrics : energyMetrics.slice(0, 5);
  const displayedCarbon = showAllCarbon ? carbonMetrics : carbonMetrics.slice(0, 5);
  const displayedWaterWaste = showAllWaterWaste ? waterWasteMetrics : waterWasteMetrics.slice(0, 5);

  const exportTableData = (type, dataList) => {
    const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dataList, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", jsonStr);
    downloadAnchor.setAttribute("download", `${type}_metrics_export.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const getDocIcon = (metricType) => {
    switch (metricType) {
      case 'electricity_consumption':
      case 'renewable_energy':
      case 'fuel_consumption':
        return <span className="w-4 h-4 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center text-[9px] font-bold shrink-0">⚡</span>;
      case 'scope_1_emissions':
      case 'scope_2_emissions':
      case 'total_ghg_emissions':
        return <span className="w-4 h-4 rounded bg-purple-100 text-purple-700 flex items-center justify-center text-[9px] font-bold shrink-0">🌱</span>;
      case 'water_consumption':
      case 'recycled_water':
        return <span className="w-4 h-4 rounded bg-blue-100 text-blue-700 flex items-center justify-center text-[9px] font-bold shrink-0">💧</span>;
      case 'hazardous_waste':
      case 'non_hazardous_waste':
      case 'recycled_waste':
        return <span className="w-4 h-4 rounded bg-amber-100 text-amber-700 flex items-center justify-center text-[9px] font-bold shrink-0">♻️</span>;
      default:
        return <span className="w-4 h-4 rounded bg-slate-100 text-slate-700 flex items-center justify-center text-[9px] font-bold shrink-0">📊</span>;
    }
  };

  const formatMetricLabel = (key) => {
    if (!key) return '—';
    return key
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  const handleOpenSourceDoc = async (docId) => {
    if (!docId) return;
    let targetDoc = documents.find(d => d.id === docId);
    if (!targetDoc) {
      try {
        targetDoc = await getDocument(docId);
      } catch (e) {
        console.error('Error fetching source document:', e);
      }
    }
    if (targetDoc && onSelectDocument) {
      onSelectDocument(targetDoc);
    }
  };

  const attentionCount = insightsList.filter(i => i.severity === 'ATTENTION').length;
  const reviewCount = insightsList.filter(i => i.severity === 'REVIEW').length;
  const infoCount = insightsList.filter(i => i.severity === 'INFO').length;

  const filteredInsights = insightsList.filter(i => {
    if (selectedInsightFilter === 'ALL') return true;
    return i.severity === selectedInsightFilter;
  });

  // Trend graph scaling calculation
  const maxTrendVal = trendData.length > 0 ? Math.max(...trendData.map(d => d.value)) : 100;
  const minTrendVal = trendData.length > 0 ? Math.min(...trendData.map(d => d.value)) : 0;

  return (
    <div className="space-y-5 pb-12 w-full">
      
      {/* 1. PAGE HEADER & EXPORT */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sustainability Metrics</h1>
          <p className="text-xs text-slate-400 mt-0.5">Normalized portfolio records and historical recurring trend intelligence.</p>
        </div>

        <button
          onClick={() => exportTableData('sustainability_portfolio', { summary, metrics: metricsList, trends: trendData })}
          className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium transition-colors shadow-xs inline-flex items-center gap-1.5 self-start sm:self-auto"
        >
          <Download className="w-3.5 h-3.5 text-slate-500" />
          <span>Export JSON</span>
        </button>
      </div>

      {/* 2. SUMMARY KPI CARDS (4 Horizontal Cards in 1 Row) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: ELECTRICITY */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">ELECTRICITY</span>
            <p className="text-sm font-bold text-slate-900 leading-tight">
              {Number(totalEnergy).toLocaleString()} kWh
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {summary?.total_renewable_energy_kwh ? `${Number(summary.total_renewable_energy_kwh).toLocaleString()} kWh renewable` : 'Across documents'}
            </p>
          </div>
        </div>

        {/* Card 2: GHG EMISSIONS */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-700 flex items-center justify-center shrink-0">
            <Flame className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">GHG EMISSIONS</span>
            <p className="text-sm font-bold text-slate-900 leading-tight">
              {typeof totalEmissions === 'number' ? totalEmissions.toFixed(2) : totalEmissions} tCO₂e
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Scope 1 & Scope 2 footprint
            </p>
          </div>
        </div>

        {/* Card 3: WATER */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center shrink-0">
            <Droplets className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">WATER</span>
            <p className="text-sm font-bold text-slate-900 leading-tight">
              {Number(totalWater).toLocaleString()} kL
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {summary?.total_recycled_water_kl ? `${Number(summary.total_recycled_water_kl).toLocaleString()} kL recycled` : 'Freshwater consumption'}
            </p>
          </div>
        </div>

        {/* Card 4: WASTE */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center shrink-0">
            <Recycle className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">WASTE</span>
            <p className="text-sm font-bold text-slate-900 leading-tight">
              {typeof totalWaste === 'number' ? totalWaste.toLocaleString() : totalWaste} kg
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Hazardous & non-hazardous
            </p>
          </div>
        </div>

      </div>

      {/* 3. LATEST AVAILABLE DATA ROW */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3 mb-3">
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-teal-700" />
            <h3 className="text-xs font-bold text-slate-900">Latest Available Reporting Period</h3>
          </div>
          <span className="text-[11px] text-slate-400">
            Derived from actual business document reporting periods, not file upload timestamps.
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase block">Electricity</span>
            <span className="font-bold text-slate-900 mt-0.5 block">{latestData.electricity || 'October 2024'}</span>
          </div>
          <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase block">GHG Emissions</span>
            <span className="font-bold text-slate-900 mt-0.5 block">{latestData.ghg || 'October 2024'}</span>
          </div>
          <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase block">Freshwater</span>
            <span className="font-bold text-slate-900 mt-0.5 block">{latestData.water || 'September 2024'}</span>
          </div>
          <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-2.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase block">Solid Waste</span>
            <span className="font-bold text-slate-900 mt-0.5 block">{latestData.waste || 'September 2024'}</span>
          </div>
        </div>
      </div>

      {/* 4. SUSTAINABILITY INSIGHTS & ACTION FLAGS SECTION */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white">
          <div>
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-teal-700" />
              <h3 className="text-xs font-bold text-slate-900">Sustainability Insights & Action Flags</h3>
              {attentionCount > 0 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                  {attentionCount} need attention
                </span>
              )}
              {reviewCount > 0 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                  {reviewCount} require review
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Deterministic, fact-based period comparisons, threshold alerts, and source-traceable action flags.
            </p>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center space-x-1.5 text-xs bg-slate-50 p-1 rounded-lg border border-slate-200/80">
            <button
              onClick={() => setSelectedInsightFilter('ALL')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                selectedInsightFilter === 'ALL'
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              All ({insightsList.length})
            </button>
            <button
              onClick={() => setSelectedInsightFilter('ATTENTION')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                selectedInsightFilter === 'ATTENTION'
                  ? 'bg-amber-50 text-amber-900 border border-amber-200 shadow-2xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Attention ({attentionCount})
            </button>
            <button
              onClick={() => setSelectedInsightFilter('REVIEW')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                selectedInsightFilter === 'REVIEW'
                  ? 'bg-rose-50 text-rose-900 border border-rose-200 shadow-2xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Review ({reviewCount})
            </button>
            <button
              onClick={() => setSelectedInsightFilter('INFO')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                selectedInsightFilter === 'INFO'
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Info ({infoCount})
            </button>
          </div>
        </div>

        <div className="p-5">
          {filteredInsights.length === 0 ? (
            <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-8 text-center text-xs space-y-2">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto" />
              <p className="font-semibold text-slate-800">No active insight flags</p>
              <p className="text-slate-400 max-w-sm mx-auto">
                All metrics are within standard operating thresholds and no documents require immediate human review.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {filteredInsights.map((ins, idx) => {
                const isAttention = ins.severity === 'ATTENTION';
                const isReview = ins.severity === 'REVIEW';

                // Subtle border & header styling
                const cardBorder = isAttention
                  ? 'border-amber-200/90 bg-amber-50/20'
                  : isReview
                  ? 'border-rose-200/90 bg-rose-50/20'
                  : 'border-slate-200 bg-white';

                const badgeStyle = isAttention
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : isReview
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200';

                return (
                  <div
                    key={idx}
                    className={`border rounded-xl p-4 flex flex-col justify-between space-y-3 transition-shadow hover:shadow-2xs ${cardBorder}`}
                  >
                    <div>
                      {/* Top Header */}
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center space-x-1.5">
                          {getDocIcon(ins.metric_type)}
                          <div>
                            <span className="font-bold text-slate-900 text-xs block leading-tight">
                              {ins.metric_type ? formatMetricLabel(ins.metric_type) : (ins.category === 'NEEDS_REVIEW' ? 'Document Review' : 'Operational Flag')}
                            </span>
                            {ins.company_name && (
                              <span className="text-[10px] text-slate-400 block truncate max-w-[140px]">
                                {ins.company_name}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center space-x-1 shrink-0">
                          {ins.percentage_change !== null && ins.percentage_change !== undefined && (
                            <span className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              ins.percentage_change > 0 
                                ? (isAttention ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-800')
                                : 'bg-slate-100 text-slate-700'
                            }`}>
                              {ins.percentage_change > 0 ? `↑ ${ins.percentage_change}%` : `↓ ${Math.abs(ins.percentage_change)}%`}
                            </span>
                          )}
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${badgeStyle}`}>
                            {ins.severity}
                          </span>
                        </div>
                      </div>

                      {/* Message */}
                      <p className="text-xs text-slate-700 leading-relaxed font-medium">
                        {ins.message}
                      </p>

                      {/* Threshold Note */}
                      {ins.threshold_note && (
                        <div className="mt-2 text-[10px] text-slate-500 bg-slate-50 border border-slate-200/80 rounded px-2 py-1 font-mono">
                          {ins.threshold_note}
                        </div>
                      )}

                      {/* Numeric Data Breakdown */}
                      {(ins.current_value !== null && ins.current_value !== undefined) && (
                        <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Current</span>
                            <span className="font-semibold text-slate-800">
                              {Number(ins.current_value).toLocaleString()} {ins.unit}
                            </span>
                          </div>
                          {ins.previous_value !== null && ins.previous_value !== undefined && (
                            <div className="text-right">
                              <span className="text-[10px] text-slate-400 block">Previous</span>
                              <span className="font-semibold text-slate-600">
                                {Number(ins.previous_value).toLocaleString()} {ins.unit}
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {ins.quality_score !== null && ins.quality_score !== undefined && (
                        <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                          <span>Quality Score:</span>
                          <span className="font-bold text-slate-800">{ins.quality_score}/100</span>
                        </div>
                      )}
                    </div>

                    {/* Footer Actions: Source Traceability */}
                    <div className="pt-2 border-t border-slate-100/80 flex items-center justify-between gap-2 text-xs">
                      <div className="flex items-center space-x-2">
                        {ins.source_document_id && (
                          <button
                            onClick={() => handleOpenSourceDoc(ins.source_document_id)}
                            className="inline-flex items-center space-x-1 text-[11px] text-teal-700 hover:text-teal-900 font-semibold transition-colors cursor-pointer"
                          >
                            <FileText className="w-3 h-3" />
                            <span>{ins.category === 'NEEDS_REVIEW' ? 'Review Document' : `Doc #${ins.source_document_id}`}</span>
                          </button>
                        )}
                        {ins.previous_source_document_id && (
                          <button
                            onClick={() => handleOpenSourceDoc(ins.previous_source_document_id)}
                            className="inline-flex items-center space-x-1 text-[10px] text-slate-400 hover:text-slate-700 font-medium transition-colors cursor-pointer"
                          >
                            <span>Prev #{ins.previous_source_document_id}</span>
                          </button>
                        )}
                        {ins.category === 'MISSING_DATA' && (
                          <span className="text-[10px] text-slate-400">
                            Period: {ins.period || 'Latest'}
                          </span>
                        )}
                      </div>

                      {ins.period && (
                        <span className="text-[10px] text-slate-400 font-mono">
                          {ins.period}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 5. HISTORICAL SUSTAINABILITY TRENDS SECTION */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white">
          <div>
            <h3 className="text-xs font-bold text-slate-900 flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-teal-700" />
              <span>Historical Sustainability Trends</span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Chronological recurring period analysis & period-over-period comparisons.</p>
          </div>

          {/* Metric & Company Dropdown Selectors */}
          <div className="flex items-center space-x-2 text-xs">
            <select
              value={trendMetric}
              onChange={(e) => setTrendMetric(e.target.value)}
              className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 font-medium focus:outline-none focus:border-teal-700 cursor-pointer shadow-2xs"
            >
              <option value="electricity_consumption">Electricity (kWh)</option>
              <option value="renewable_energy">Renewable Energy (kWh)</option>
              <option value="fuel_consumption">Fuel (Liters)</option>
              <option value="scope_1_emissions">Scope 1 GHG (tCO₂e)</option>
              <option value="scope_2_emissions">Scope 2 GHG (tCO₂e)</option>
              <option value="total_ghg_emissions">Total GHG (tCO₂e)</option>
              <option value="water_consumption">Water Consumption (kL)</option>
              <option value="hazardous_waste">Hazardous Waste (kg)</option>
            </select>

            <select
              value={trendCompany}
              onChange={(e) => setTrendCompany(e.target.value)}
              className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 font-medium focus:outline-none focus:border-teal-700 cursor-pointer shadow-2xs"
            >
              <option value="">All Companies</option>
              {uniqueCompanies.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="p-5">
          {trendData.length < 2 ? (
            /* Single Period or Empty Data Informational View */
            <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-8 text-center text-xs space-y-2">
              <Info className="w-6 h-6 text-slate-400 mx-auto" />
              <p className="font-semibold text-slate-800">
                {trendData.length === 1 
                  ? 'Not enough historical data for a trend.' 
                  : 'No recurring historical records found for this metric.'}
              </p>
              <p className="text-slate-400 max-w-sm mx-auto">
                {trendData.length === 1 
                  ? '1 reporting period available. Upload additional monthly or quarterly documents to view historical trends and comparisons.'
                  : 'Upload monthly utility bills or sustainability reports to generate chronological trends.'}
              </p>
              {trendData.length === 1 && (
                <div className="inline-block mt-3 bg-white border border-slate-200 rounded-lg px-4 py-2 text-left">
                  <span className="text-[10px] text-slate-400 block font-semibold uppercase">Single Available Period</span>
                  <span className="font-bold text-slate-900 text-xs">
                    {trendData[0].period_label || trendData[0].period}: {Number(trendData[0].value).toLocaleString()} {trendData[0].unit}
                  </span>
                </div>
              )}
            </div>
          ) : (
            /* Chronological Trend Visualization & Points */
            <div className="space-y-6">
              
              {/* Minimal Line Chart Visual */}
              <div className="bg-slate-50/50 border border-slate-200/80 rounded-xl p-4">
                <div className="flex items-center justify-between text-[11px] text-slate-500 font-semibold mb-3">
                  <span>{formatMetricLabel(trendMetric)} ({trendData[0]?.unit})</span>
                  <span>{trendData.length} Reporting Periods</span>
                </div>

                {/* SVG Trend Line / Visual Points */}
                <div className="h-44 w-full flex items-end justify-between gap-4 pt-6 pb-2 px-6">
                  {trendData.map((d, idx) => {
                    const range = (maxTrendVal - minTrendVal) || 1;
                    const heightPct = Math.max(20, Math.min(95, ((d.value - minTrendVal) / range) * 80 + 15));
                    return (
                      <div 
                        key={d.id || idx}
                        onClick={() => setSelectedTraceMetric(d)}
                        className="flex-1 flex flex-col items-center group cursor-pointer"
                      >
                        <div className="text-[10px] font-bold text-slate-700 opacity-0 group-hover:opacity-100 transition-opacity mb-1 whitespace-nowrap">
                          {Number(d.value).toLocaleString()} {d.unit}
                        </div>
                        <div 
                          style={{ height: `${heightPct}%` }}
                          className="w-8 sm:w-12 bg-teal-600/80 group-hover:bg-teal-700 rounded-t-md transition-all relative flex items-start justify-center pt-1"
                        >
                          <div className="w-2 h-2 rounded-full bg-white shadow-xs" />
                        </div>
                        <div className="text-[11px] font-medium text-slate-600 mt-2 text-center truncate max-w-[80px]" title={d.period_label || d.period}>
                          {d.period_label || d.period}
                        </div>
                        <span className="text-[9px] text-slate-400 truncate max-w-[80px]">
                          {d.company_name}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Period Comparison Card (Neutral & Transparent) */}
              {periodChange && periodChange.previous_period && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Period-Over-Period Comparison
                    </span>
                    <p className="font-bold text-slate-900 mt-0.5">
                      {periodChange.current_period} vs {periodChange.previous_period}
                    </p>
                    <p className="text-slate-500 mt-0.5">
                      {formatMetricLabel(trendMetric)}: <strong>{Number(periodChange.current_value).toLocaleString()} {periodChange.unit}</strong> (was {Number(periodChange.previous_value).toLocaleString()} {periodChange.unit})
                    </p>
                  </div>

                  <div className="flex items-center space-x-3 bg-white border border-slate-200 rounded-lg p-2.5 px-4 shadow-2xs self-start sm:self-auto">
                    {periodChange.percentage_change < 0 ? (
                      <TrendingDown className="w-5 h-5 text-slate-600" />
                    ) : (
                      <TrendingUp className="w-5 h-5 text-slate-600" />
                    )}
                    <div>
                      <span className="font-bold text-slate-900 text-sm block leading-none">
                        {periodChange.percentage_change > 0 ? `+${periodChange.percentage_change}%` : `${periodChange.percentage_change}%`}
                      </span>
                      <span className="text-[10px] text-slate-400 mt-0.5 block">
                        ({periodChange.absolute_change > 0 ? `+${periodChange.absolute_change}` : periodChange.absolute_change} {periodChange.unit})
                      </span>
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </div>

      {/* 5. DATA NORMALIZATION & QUALITY STATUS BAR */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 px-5 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-4">
          <span className="font-semibold text-slate-700">Data Normalization Quality:</span>
          <span className="inline-flex items-center space-x-1 text-slate-600">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            <span>AI Extracted: <strong>{aiExtractedCount}</strong></span>
          </span>
          <span className="inline-flex items-center space-x-1 text-purple-700">
            <CheckCircle2 className="w-3.5 h-3.5 text-purple-600" />
            <span>Human Verified: <strong>{humanVerifiedCount}</strong></span>
          </span>
        </div>
        <span className="text-[11px] text-slate-400">
          Normalized format-independent records &bull; Click any metric row for source evidence traceability
        </span>
      </div>

      {/* 6. ENERGY CONSUMPTION BY DOCUMENT (Large Full-Width Table Card) */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 bg-white border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-xs font-semibold text-slate-900">Energy Consumption by Document</h3>
            <p className="text-[11px] text-slate-400">Electricity, captive solar renewable generation, and fuel records</p>
          </div>
          <button
            onClick={() => exportTableData('energy', energyMetrics)}
            className="px-2.5 py-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-md text-xs font-medium transition-colors shadow-xs inline-flex items-center gap-1"
          >
            <Download className="w-3 h-3 text-slate-500" />
            <span>Export</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/70 border-b border-slate-100 text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-2.5">Document / Company</th>
                <th className="px-4 py-2.5">Metric</th>
                <th className="px-4 py-2.5">Reporting Period</th>
                <th className="px-4 py-2.5">Verification</th>
                <th className="px-5 py-2.5 text-right">Normalized Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {displayedEnergy.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-6 text-center text-slate-400">
                    No normalized energy metrics found. Upload documents to populate.
                  </td>
                </tr>
              ) : (
                displayedEnergy.map((m, idx) => (
                  <tr
                    key={m.id || idx}
                    onClick={() => setSelectedTraceMetric(m)}
                    className="hover:bg-slate-50/70 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3 font-semibold text-slate-900">
                      <div className="flex items-center space-x-2">
                        {getDocIcon(m.metric_type)}
                        <span className="hover:text-teal-700">{m.company_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-700 font-medium">
                      {formatMetricLabel(m.metric_type)}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{m.period_start || m.period_end || '—'}</td>
                    <td className="px-4 py-3">
                      {m.verification_status === 'HUMAN_VERIFIED' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                          Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-teal-50 text-teal-700 border border-teal-200">
                          AI Extracted
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right font-semibold text-slate-900">
                      {Number(m.value).toLocaleString()} {m.unit}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="px-5 py-3 bg-white border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-slate-400">
            Showing 1 to {displayedEnergy.length} of {energyMetrics.length} records
          </span>
          {energyMetrics.length > 5 && (
            <button
              onClick={() => setShowAllEnergy(!showAllEnergy)}
              className="text-xs text-teal-700 hover:text-teal-900 font-medium transition-colors"
            >
              {showAllEnergy ? 'Show top 5 ↑' : 'View all energy data →'}
            </button>
          )}
        </div>
      </div>

      {/* 7. SECOND ROW — TWO SIDE-BY-SIDE TABLES (GHG Emissions + Water & Waste) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Left Card: GHG Carbon Footprint */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden flex flex-col justify-between">
          <div>
            <div className="px-5 py-3.5 bg-white border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-900">GHG Carbon Footprint by Document</h3>
              <button
                onClick={() => exportTableData('emissions', carbonMetrics)}
                className="px-2 py-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-md text-xs font-medium transition-colors shadow-xs inline-flex items-center gap-1"
              >
                <Download className="w-3 h-3 text-slate-500" />
                <span>Export</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/70 border-b border-slate-100 text-slate-500 font-semibold">
                  <tr>
                    <th className="px-5 py-2.5">Document</th>
                    <th className="px-3 py-2.5">Metric</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-5 py-2.5 text-right">Emissions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {displayedCarbon.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-5 py-6 text-center text-slate-400">
                        No carbon emission records found.
                      </td>
                    </tr>
                  ) : (
                    displayedCarbon.map((m, idx) => (
                      <tr
                        key={m.id || idx}
                        onClick={() => setSelectedTraceMetric(m)}
                        className="hover:bg-slate-50/70 cursor-pointer transition-colors"
                      >
                        <td className="px-5 py-3 font-semibold text-slate-900">
                          <span className="hover:text-teal-700 truncate block max-w-[140px]" title={m.company_name}>
                            {m.company_name}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-slate-600 truncate max-w-[110px]">
                          {formatMetricLabel(m.metric_type)}
                        </td>
                        <td className="px-3 py-3">
                          {m.verification_status === 'HUMAN_VERIFIED' ? (
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                              Verified
                            </span>
                          ) : (
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-medium bg-teal-50 text-teal-700 border border-teal-200">
                              AI
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-right font-semibold text-slate-900">
                          {Number(m.value).toFixed(2)} {m.unit}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="px-5 py-3 bg-white border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Showing 1 to {displayedCarbon.length} of {carbonMetrics.length} records
            </span>
            {carbonMetrics.length > 5 && (
              <button
                onClick={() => setShowAllCarbon(!showAllCarbon)}
                className="text-xs text-teal-700 hover:text-teal-900 font-medium transition-colors"
              >
                {showAllCarbon ? 'Show top 5 ↑' : 'View all GHG data →'}
              </button>
            )}
          </div>
        </div>

        {/* Right Card: Water Usage & Solid Waste */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden flex flex-col justify-between">
          <div>
            <div className="px-5 py-3.5 bg-white border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-900">Water Usage & Solid Waste by Document</h3>
              <button
                onClick={() => exportTableData('water_waste', waterWasteMetrics)}
                className="px-2 py-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-md text-xs font-medium transition-colors shadow-xs inline-flex items-center gap-1"
              >
                <Download className="w-3 h-3 text-slate-500" />
                <span>Export</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/70 border-b border-slate-100 text-slate-500 font-semibold">
                  <tr>
                    <th className="px-5 py-2.5">Document</th>
                    <th className="px-3 py-2.5">Metric</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-5 py-2.5 text-right">Normalized Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {displayedWaterWaste.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-5 py-6 text-center text-slate-400">
                        No water/waste records found.
                      </td>
                    </tr>
                  ) : (
                    displayedWaterWaste.map((m, idx) => (
                      <tr
                        key={m.id || idx}
                        onClick={() => setSelectedTraceMetric(m)}
                        className="hover:bg-slate-50/70 cursor-pointer transition-colors"
                      >
                        <td className="px-5 py-3 font-semibold text-slate-900">
                          <span className="hover:text-teal-700 truncate block max-w-[140px]" title={m.company_name}>
                            {m.company_name}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-slate-600 truncate max-w-[110px]">
                          {formatMetricLabel(m.metric_type)}
                        </td>
                        <td className="px-3 py-3">
                          {m.verification_status === 'HUMAN_VERIFIED' ? (
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                              Verified
                            </span>
                          ) : (
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-medium bg-teal-50 text-teal-700 border border-teal-200">
                              AI
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-right font-semibold text-slate-900">
                          {Number(m.value).toLocaleString()} {m.unit}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="px-5 py-3 bg-white border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Showing 1 to {displayedWaterWaste.length} of {waterWasteMetrics.length} records
            </span>
            {waterWasteMetrics.length > 5 && (
              <button
                onClick={() => setShowAllWaterWaste(!showAllWaterWaste)}
                className="text-xs text-teal-700 hover:text-teal-900 font-medium transition-colors"
              >
                {showAllWaterWaste ? 'Show top 5 ↑' : 'View all water & waste data →'}
              </button>
            )}
          </div>
        </div>

      </div>

      {/* 8. SOURCE TRACEABILITY MODAL */}
      {selectedTraceMetric && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-teal-700" />
                <h3 className="text-xs font-bold text-slate-900">Source Evidence Traceability</h3>
              </div>
              <button
                onClick={() => setSelectedTraceMetric(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Metric:</span>
                  <span className="font-bold text-slate-900">{formatMetricLabel(selectedTraceMetric.metric_type)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Normalized Value:</span>
                  <span className="font-bold text-teal-700 text-sm">{Number(selectedTraceMetric.value).toLocaleString()} {selectedTraceMetric.unit}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Reporting Period:</span>
                  <span className="font-semibold text-slate-800">{selectedTraceMetric.period_label || selectedTraceMetric.period_start || selectedTraceMetric.period || '—'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Source Field:</span>
                  <code className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[11px] text-slate-700 font-mono">
                    {selectedTraceMetric.source_field}
                  </code>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Status:</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                    selectedTraceMetric.verification_status === 'HUMAN_VERIFIED'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-teal-100 text-teal-800'
                  }`}>
                    {selectedTraceMetric.verification_status}
                  </span>
                </div>
              </div>

              <div>
                <span className="font-semibold text-slate-700 block mb-1">Source Text Evidence:</span>
                <div className="bg-amber-50/60 border border-amber-200/80 rounded-lg p-3 font-mono text-[11px] text-slate-800 leading-relaxed">
                  "{selectedTraceMetric.source_text || 'Exact line item extracted from source business document.'}"
                </div>
              </div>

              <div className="flex justify-between items-center pt-2">
                <span className="text-slate-400 text-[11px]">
                  Document ID: #{selectedTraceMetric.document_id} &bull; Company: {selectedTraceMetric.company_name}
                </span>
                <button
                  onClick={() => {
                    handleOpenSourceDoc(selectedTraceMetric.document_id);
                    setSelectedTraceMetric(null);
                  }}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg font-medium transition-colors shadow-xs"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Open Document</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
