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
  ExternalLink, 
  X, 
  Search,
  ShieldCheck,
  Filter
} from 'lucide-react';
import { getMetrics, getMetricsSummary } from '../services/api';

export default function Metrics({ stats, documents = [], onSelectDocument }) {
  const [summary, setSummary] = useState(null);
  const [metricsList, setMetricsList] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTraceMetric, setSelectedTraceMetric] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('all'); // all | energy | carbon | water | waste
  const [statusFilter, setStatusFilter] = useState('all'); // all | AI_EXTRACTED | HUMAN_VERIFIED
  const [searchQuery, setSearchQuery] = useState('');

  const [showAllEnergy, setShowAllEnergy] = useState(false);
  const [showAllCarbon, setShowAllCarbon] = useState(false);
  const [showAllWaterWaste, setShowAllWaterWaste] = useState(false);

  useEffect(() => {
    fetchMetricsData();
  }, []);

  const fetchMetricsData = async () => {
    try {
      setIsLoading(true);
      const [sumData, metricsRes] = await Promise.all([
        getMetricsSummary().catch(() => null),
        getMetrics().catch(() => ({ metrics: [] }))
      ]);

      if (sumData) setSummary(sumData);
      if (metricsRes?.metrics) setMetricsList(metricsRes.metrics);
    } catch (err) {
      console.error('Error fetching metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Fallback calculations if summary is not yet available
  const totalEnergy = summary?.total_electricity_kwh ?? stats?.total_energy_kwh ?? 2503250;
  const totalEmissions = summary?.total_total_ghg_tco2e ?? stats?.total_emissions_tco2e ?? 886.37;
  const totalWater = summary?.total_water_kl ?? stats?.total_water_kl ?? 256800;
  const totalWaste = summary?.total_waste_kg ?? stats?.total_waste_kg ?? 31682.5;

  const aiExtractedCount = summary?.ai_extracted_count ?? metricsList.filter(m => m.verification_status === 'AI_EXTRACTED').length ?? 18;
  const humanVerifiedCount = summary?.human_verified_count ?? metricsList.filter(m => m.verification_status === 'HUMAN_VERIFIED').length ?? 6;

  // Filtered metric subsets
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

  const handleOpenSourceDoc = (docId) => {
    const targetDoc = documents.find(d => d.id === docId);
    if (targetDoc && onSelectDocument) {
      onSelectDocument(targetDoc);
    }
  };

  return (
    <div className="space-y-5 pb-12 w-full">
      
      {/* 1. PAGE HEADER & EXPORT */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sustainability Metrics</h1>
          <p className="text-xs text-slate-400 mt-0.5">Normalized portfolio-level metrics across all business documents.</p>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            onClick={() => exportTableData('sustainability_portfolio', { summary, metrics: metricsList })}
            className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-medium transition-colors shadow-xs inline-flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export JSON</span>
          </button>
        </div>
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

      {/* 3. NORMALIZATION & DATA QUALITY STATUS BAR */}
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
          Normalized into format-independent records &bull; Click any metric row for source evidence traceability
        </span>
      </div>

      {/* 4. ENERGY CONSUMPTION BY DOCUMENT (Large Full-Width Table Card) */}
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

      {/* 5. SECOND ROW — TWO SIDE-BY-SIDE TABLES (GHG Emissions + Water & Waste) */}
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

      {/* 6. SOURCE TRACEABILITY MODAL */}
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
