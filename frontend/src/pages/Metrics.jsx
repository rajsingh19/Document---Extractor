import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  Droplets, 
  Recycle, 
  Calendar, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldCheck, 
  ChevronRight,
  Sparkles,
  Layers,
  FileText
} from 'lucide-react';
import { 
  getMetrics, 
  getMetricsSummary, 
  getMetricsTrends, 
  getMetricsChange, 
  getInsights 
} from '../services/api';

export default function Metrics({ stats, documents = [], onSelectDocument }) {
  const [summary, setSummary] = useState(null);
  const [metricsList, setMetricsList] = useState([]);
  const [insightsList, setInsightsList] = useState([]);
  const [trendMetric, setTrendMetric] = useState('electricity_consumption');
  const [trendCompany, setTrendCompany] = useState('');
  const [trendData, setTrendData] = useState([]);
  const [periodChange, setPeriodChange] = useState(null);
  const [isLoadingTrends, setIsLoadingTrends] = useState(false);
  const [insightFilter, setInsightFilter] = useState('ALL');

  useEffect(() => {
    fetchMetricsData();
  }, []);

  useEffect(() => {
    fetchTrends(trendMetric, trendCompany);
  }, [trendMetric, trendCompany]);

  const fetchMetricsData = async () => {
    try {
      const [sumRes, metRes, insRes] = await Promise.all([
        getMetricsSummary().catch(() => null),
        getMetrics().catch(() => ({ metrics: [] })),
        getInsights().catch(() => ({ insights: [] }))
      ]);

      if (sumRes) setSummary(sumRes);
      if (metRes?.metrics) setMetricsList(metRes.metrics);
      if (insRes?.insights) setInsightsList(insRes.insights);
    } catch (err) {
      console.error('Error fetching metrics overview:', err);
    }
  };

  const fetchTrends = async (metricType, company) => {
    try {
      setIsLoadingTrends(true);
      const params = { metric_type: metricType };
      if (company) params.company = company;

      const [trendRes, changeRes] = await Promise.all([
        getMetricsTrends(params).catch(() => ({ data: [] })),
        getMetricsChange(params).catch(() => null)
      ]);

      setTrendData(trendRes?.data || []);
      setPeriodChange(changeRes || null);
    } catch (err) {
      console.error('Error fetching trends:', err);
    } finally {
      setIsLoadingTrends(false);
    }
  };

  // Find unique companies
  const companies = Array.from(new Set(
    documents.map((d) => d.company_name).filter(Boolean)
  ));

  // Determine latest period from metrics or summary
  const latestPeriod = summary?.latest_period || documents[0]?.reporting_period || '—';
  const totalEnergyKwh = summary?.total_electricity_kwh ?? summary?.energy?.total_kwh ?? null;
  const totalWaterKl = summary?.total_water_kl ?? summary?.water_waste?.water_kl ?? null;
  const totalGhgTco2e = summary?.total_carbon_tco2e ?? summary?.carbon?.total_tco2e ?? null;

  const filteredInsights = insightsList.filter((ins) => {
    if (insightFilter === 'ACTION_REQUIRED') return ins.severity === 'ACTION_REQUIRED';
    if (insightFilter === 'REVIEW') return ins.severity === 'REVIEW' || ins.severity === 'WARNING';
    if (insightFilter === 'POSITIVE') return ins.severity === 'POSITIVE' || ins.severity === 'INFO';
    return true;
  });

  return (
    <div className="space-y-6 pb-16 w-full">
      
      {/* 1. HEADER */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sustainability Metrics</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Normalized sustainability data across your verified business documents.
        </p>
      </div>

      {/* 2. TOP FOUR COMPACT SUMMARY CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Latest Period */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Latest Period</span>
            <Calendar className="w-4 h-4 text-slate-400" />
          </div>
          <p className="text-lg font-bold text-slate-900 truncate">{latestPeriod}</p>
          <p className="text-[11px] text-slate-400 font-normal">Active reporting window</p>
        </div>

        {/* Card 2: Energy */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Energy Consumption</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-lg font-bold text-slate-900">
            {totalEnergyKwh != null ? totalEnergyKwh.toLocaleString() : '—'}{' '}
            <span className="text-xs font-normal text-slate-400">kWh</span>
          </p>
          <p className="text-[11px] text-slate-400 font-normal">Grid & captive energy</p>
        </div>

        {/* Card 3: Water */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Water Withdrawal</span>
            <Droplets className="w-4 h-4 text-sky-500" />
          </div>
          <p className="text-lg font-bold text-slate-900">
            {totalWaterKl != null ? totalWaterKl.toLocaleString() : '—'}{' '}
            <span className="text-xs font-normal text-slate-400">kL</span>
          </p>
          <p className="text-[11px] text-slate-400 font-normal">Freshwater intake</p>
        </div>

        {/* Card 4: GHG */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Carbon Emissions</span>
            <Recycle className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-lg font-bold text-slate-900">
            {totalGhgTco2e != null ? (typeof totalGhgTco2e === 'number' ? totalGhgTco2e.toFixed(1) : totalGhgTco2e) : '—'}{' '}
            <span className="text-xs font-normal text-slate-400">tCO2e</span>
          </p>
          <p className="text-[11px] text-slate-400 font-normal">Scope 1 & 2 total</p>
        </div>

      </div>

      {/* 3. HISTORICAL TRENDS & PERIOD COMPARISON */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-4">
        
        {/* Trend Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Historical Trends</h3>
            <p className="text-xs text-slate-500 mt-0.5">Track period-over-period sustainability metrics over time.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={trendMetric}
              onChange={(e) => setTrendMetric(e.target.value)}
              className="px-2.5 py-1 bg-white border border-slate-200 rounded text-xs text-slate-700 focus:outline-none focus:border-teal-700"
            >
              <option value="electricity_consumption">Electricity (kWh)</option>
              <option value="fuel_consumption">Fuel / Diesel (Liters)</option>
              <option value="water_consumption">Water (kL)</option>
              <option value="hazardous_waste">Hazardous Waste (kg)</option>
              <option value="scope_1_emissions">Scope 1 Emissions (tCO2e)</option>
              <option value="scope_2_emissions">Scope 2 Emissions (tCO2e)</option>
            </select>

            {companies.length > 0 && (
              <select
                value={trendCompany}
                onChange={(e) => setTrendCompany(e.target.value)}
                className="px-2.5 py-1 bg-white border border-slate-200 rounded text-xs text-slate-700 focus:outline-none focus:border-teal-700"
              >
                <option value="">All Companies</option>
                {companies.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Period-Over-Period Change Banner */}
        {periodChange && periodChange.percentage_change != null && (
          <div className="p-3 rounded bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2">
              {periodChange.percentage_change > 0 ? (
                <TrendingUp className="w-4 h-4 text-amber-600" />
              ) : (
                <TrendingDown className="w-4 h-4 text-emerald-600" />
              )}
              <span className="text-slate-700">
                <b>{periodChange.percentage_change > 0 ? '+' : ''}{periodChange.percentage_change.toFixed(1)}%</b> change from{' '}
                <span className="font-medium">{periodChange.previous_period || 'previous period'}</span> ({periodChange.previous_value?.toLocaleString()} {periodChange.unit}) to{' '}
                <span className="font-medium">{periodChange.current_period || 'current period'}</span> ({periodChange.current_value?.toLocaleString()} {periodChange.unit}).
              </span>
            </div>
          </div>
        )}

        {/* Chronological Bars or Clean State */}
        {trendData.length > 0 ? (
          <div className="space-y-2.5 pt-2">
            {trendData.map((t, idx) => {
              const maxVal = Math.max(...trendData.map(d => d.value || 0), 1);
              const barWidth = Math.max(12, Math.round(((t.value || 0) / maxVal) * 100));

              return (
                <div key={idx} className="space-y-1 text-xs">
                  <div className="flex justify-between text-slate-700">
                    <span className="font-medium">{t.period}</span>
                    <span className="font-bold text-slate-900">
                      {t.value != null ? t.value.toLocaleString() : '—'} {t.unit || ''}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded h-3 overflow-hidden">
                    <div 
                      className="bg-[#0f6b56] h-full rounded transition-all"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-400">
            Not enough historical data yet for this metric.
          </div>
        )}

      </div>

      {/* 4. ACTIONABLE INSIGHTS */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-4">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Actionable Insights</h3>
            <p className="text-xs text-slate-500 mt-0.5">Deterministic rule-based sustainability findings.</p>
          </div>

          <div className="flex items-center space-x-1.5 text-xs">
            {['ALL', 'ACTION_REQUIRED', 'REVIEW', 'POSITIVE'].map((f) => (
              <button
                key={f}
                onClick={() => setInsightFilter(f)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  insightFilter === f
                    ? 'bg-slate-900 text-white font-semibold'
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                {f.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {filteredInsights.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No actionable insights generated for this filter.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {filteredInsights.map((ins, idx) => {
              const isAction = ins.severity === 'ACTION_REQUIRED';
              const isPositive = ins.severity === 'POSITIVE' || ins.severity === 'INFO';

              return (
                <div 
                  key={idx}
                  className={`p-4 rounded-lg border text-xs space-y-2.5 ${
                    isAction
                      ? 'bg-rose-50/40 border-rose-200'
                      : isPositive
                      ? 'bg-emerald-50/30 border-emerald-200'
                      : 'bg-slate-50/60 border-slate-200'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      {isAction ? (
                        <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      ) : isPositive ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      ) : (
                        <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                      )}
                      <h4 className="font-semibold text-slate-900 text-xs">
                        {ins.title}
                      </h4>
                    </div>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold border ${
                      isAction 
                        ? 'bg-rose-100 text-rose-800 border-rose-200' 
                        : isPositive 
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
                        : 'bg-slate-100 text-slate-700 border-slate-200'
                    }`}>
                      {ins.severity}
                    </span>
                  </div>

                  <p className="text-slate-600 leading-relaxed text-xs">
                    {ins.description}
                  </p>

                  <div className="pt-2 border-t border-slate-200/60 flex flex-wrap items-center justify-between gap-1 text-[11px] text-slate-500">
                    <span><b>Period:</b> {ins.period || 'Latest'}</span>
                    {ins.source_document && (
                      <span className="text-slate-400">Source: {ins.source_document}</span>
                    )}
                  </div>

                  {ins.action && (
                    <div className="p-2 rounded bg-white border border-slate-200/80 text-[11px] text-slate-700">
                      <span className="font-semibold text-slate-900">Recommended Action:</span> {ins.action}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

      </div>

    </div>
  );
}
