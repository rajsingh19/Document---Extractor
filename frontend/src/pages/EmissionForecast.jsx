import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle2, 
  Info, 
  RefreshCw, 
  Filter, 
  BarChart2, 
  Calendar, 
  Layers, 
  Activity, 
  ShieldAlert, 
  Zap, 
  Clock, 
  HelpCircle,
  Sparkles
} from 'lucide-react';
import { 
  getEmissionsForecast, 
  getForecastModels, 
  getForecastDataQuality, 
  getForecastBacktest 
} from '../services/api';

export default function EmissionForecastPage() {
  const [forecastData, setForecastData] = useState(null);
  const [dataQuality, setDataQuality] = useState(null);
  const [modelsList, setModelsList] = useState([]);
  const [backtestResults, setBacktestResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [scopeFilter, setScopeFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [horizonFilter, setHorizonFilter] = useState(1);
  const [modelPreference, setModelPreference] = useState('');

  useEffect(() => {
    loadForecastData();
    loadModels();
  }, [scopeFilter, categoryFilter, horizonFilter, modelPreference]);

  const loadModels = async () => {
    try {
      const data = await getForecastModels();
      setModelsList(data || []);
    } catch (err) {
      console.error("Failed to load forecast models:", err);
    }
  };

  const loadForecastData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        horizon: parseInt(horizonFilter, 10),
      };
      if (scopeFilter) params.scope = scopeFilter;
      if (categoryFilter) params.category = categoryFilter;
      if (modelPreference) params.model_preference = modelPreference;

      const [forecastRes, qualityRes, backtestRes] = await Promise.all([
        getEmissionsForecast(params),
        getForecastDataQuality(params),
        getForecastBacktest(params),
      ]);

      setForecastData(forecastRes);
      setDataQuality(qualityRes);
      setBacktestResults(backtestRes);
    } catch (err) {
      console.error("Failed to load emissions forecast:", err);
      setError("Unable to load predictive emissions forecast data.");
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceBadge = (label) => {
    switch (label) {
      case 'HIGH':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">High Confidence</span>;
      case 'MODERATE':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">Moderate Confidence</span>;
      case 'LOW':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800">Low Confidence</span>;
      case 'INSUFFICIENT_DATA':
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">Insufficient Data</span>;
    }
  };

  const getQualityBadge = (quality) => {
    switch (quality) {
      case 'EXCELLENT':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">Excellent Quality</span>;
      case 'GOOD':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200">Good Quality</span>;
      case 'FAIR':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">Fair Quality</span>;
      case 'POOR':
      case 'INSUFFICIENT':
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">Limited Data</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Predictive Emissions Analytics</h1>
            <span className="bg-[#EAF7F2] text-[#0F6B56] text-xs font-semibold px-2.5 py-0.5 rounded-full border border-[#0F6B56]/20">
              Step 21 Engine
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-1">
            Estimate future emissions from your historical POSTED carbon-accounting data.
          </p>
        </div>

        <button
          onClick={loadForecastData}
          disabled={loading}
          className="inline-flex items-center justify-center px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 mr-2 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          Refresh Forecast
        </button>
      </div>

      {/* Mandatory Product Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-900 shadow-2xs">
        <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-amber-950">Important Product Boundary & Disclaimer:</p>
          <p>
            {forecastData?.disclaimer || "This forecast is a statistical projection based on historical accounting data. It is an estimate, not a guaranteed future value or carbon accounting truth."}
          </p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mr-2">
          <Filter className="w-4 h-4" />
          <span>Filters:</span>
        </div>

        {/* Scope Filter */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-700">Scope:</label>
          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
          >
            <option value="">All Scopes (Total)</option>
            <option value="SCOPE_1">Scope 1 (Direct)</option>
            <option value="SCOPE_2">Scope 2 (Electricity)</option>
            <option value="SCOPE_3">Scope 3 (Supply Chain)</option>
          </select>
        </div>

        {/* Horizon Filter */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-700">Horizon:</label>
          <select
            value={horizonFilter}
            onChange={(e) => setHorizonFilter(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
          >
            <option value={1}>+1 Period Ahead</option>
            <option value={2}>+2 Periods Ahead</option>
            <option value={3}>+3 Periods Ahead</option>
            <option value={4}>+4 Periods Ahead</option>
          </select>
        </div>

        {/* Model Preference */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-700">Model:</label>
          <select
            value={modelPreference}
            onChange={(e) => setModelPreference(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]"
          >
            <option value="">Auto Select (Best MAE)</option>
            <option value="LINEAR_TREND">Linear Trend</option>
            <option value="MOVING_AVERAGE">Moving Average</option>
            <option value="EXPONENTIAL_SMOOTHING">Exponential Smoothing</option>
            <option value="NAIVE">Naive Baseline</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-[#0F6B56]" />
          <p className="text-sm font-medium">Computing deterministic emissions forecast...</p>
        </div>
      ) : error ? (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-center text-rose-800">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-rose-600" />
          <p className="font-semibold">{error}</p>
        </div>
      ) : (
        <>
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* 1. Historical Coverage */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-2">
              <div className="flex items-center justify-between text-xs font-medium text-slate-500">
                <span>Historical Coverage</span>
                <Calendar className="w-4 h-4 text-slate-400" />
              </div>
              <div className="text-2xl font-bold text-slate-900">
                {forecastData?.historical_period_count || 0} <span className="text-sm font-normal text-slate-500">periods</span>
              </div>
              <div className="text-xs text-slate-500 flex items-center justify-between">
                <span>Range: {forecastData?.training_start_period || 'N/A'} – {forecastData?.training_end_period || 'N/A'}</span>
              </div>
            </div>

            {/* 2. Projected Emission */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-2">
              <div className="flex items-center justify-between text-xs font-medium text-slate-500">
                <span>Projected ({forecastData?.forecast_period})</span>
                <TrendingUp className="w-4 h-4 text-[#0F6B56]" />
              </div>
              <div className="text-2xl font-bold text-[#0F6B56]">
                {forecastData?.forecast_status === 'INSUFFICIENT_DATA'
                  ? 'N/A'
                  : `${forecastData?.predicted_value?.toFixed(2)} tCO2e`}
              </div>
              <div className="text-xs text-slate-500 flex items-center justify-between">
                <span>Interval: {forecastData?.lower_bound !== null ? `${forecastData?.lower_bound?.toFixed(1)}–${forecastData?.upper_bound?.toFixed(1)}` : 'N/A'}</span>
              </div>
            </div>

            {/* 3. Model Selected */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-2">
              <div className="flex items-center justify-between text-xs font-medium text-slate-500">
                <span>Model Selected</span>
                <BarChart2 className="w-4 h-4 text-slate-400" />
              </div>
              <div className="text-lg font-bold text-slate-900 truncate">
                {forecastData?.model_name || 'N/A'}
              </div>
              <div className="text-xs text-slate-500 flex items-center justify-between">
                <span>Backtest MAE: {forecastData?.backtest_mae !== null ? `${forecastData?.backtest_mae?.toFixed(2)} tCO2e` : 'N/A'}</span>
              </div>
            </div>

            {/* 4. Confidence */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-2">
              <div className="flex items-center justify-between text-xs font-medium text-slate-500">
                <span>Confidence Rating</span>
                <Zap className="w-4 h-4 text-amber-500" />
              </div>
              <div className="pt-1">
                {getConfidenceBadge(forecastData?.confidence_label)}
              </div>
              <div className="text-xs text-slate-500 flex items-center justify-between pt-1">
                <span>Quality: {getQualityBadge(dataQuality?.quality)}</span>
              </div>
            </div>

          </div>

          {/* Warnings Banner if missing or insufficient data */}
          {dataQuality?.warnings && dataQuality.warnings.length > 0 && (
            <div className="bg-amber-50/80 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-amber-950">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Data Quality Notes ({dataQuality.warnings.length}):</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-amber-800 pl-1">
                {dataQuality.warnings.map((warn, idx) => (
                  <li key={idx}>{warn}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Forecast Time-Series Table / Visualization */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900">Emissions Time-Series: Actual vs Forecast</h2>
                <p className="text-xs text-slate-500">
                  Historical POSTED accounting entries compared against deterministic statistical forecast points.
                </p>
              </div>
              <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-md border border-slate-200">
                {scopeFilter || 'ALL SCOPES'}
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="min-w-full divide-y divide-slate-200 text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold">
                  <tr>
                    <th className="px-4 py-3 text-left">Reporting Period</th>
                    <th className="px-4 py-3 text-left">Data Type</th>
                    <th className="px-4 py-3 text-right">Emissions (tCO2e)</th>
                    <th className="px-4 py-3 text-right">Lower Bound (95%)</th>
                    <th className="px-4 py-3 text-right">Upper Bound (95%)</th>
                    <th className="px-4 py-3 text-center">Confidence / Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {forecastData?.time_series && forecastData.time_series.length > 0 ? (
                    forecastData.time_series.map((item, idx) => {
                      const isForecast = item.type === 'FORECAST';
                      return (
                        <tr 
                          key={idx} 
                          className={isForecast ? 'bg-teal-50/40 font-medium' : 'hover:bg-slate-50'}
                        >
                          <td className="px-4 py-3 font-semibold text-slate-900">
                            {item.period}
                          </td>
                          <td className="px-4 py-3">
                            {isForecast ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-2xs font-bold bg-[#EAF7F2] text-[#0F6B56] border border-[#0F6B56]/30">
                                FORECAST
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-2xs font-semibold bg-slate-100 text-slate-700">
                                ACTUAL (POSTED)
                              </span>
                            )}
                          </td>
                          <td className={`px-4 py-3 text-right font-bold ${isForecast ? 'text-[#0F6B56]' : 'text-slate-900'}`}>
                            {item.value.toFixed(2)} tCO2e
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600">
                            {item.lower_bound !== null && item.lower_bound !== undefined ? `${item.lower_bound.toFixed(2)}` : '—'}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600">
                            {item.upper_bound !== null && item.upper_bound !== undefined ? `${item.upper_bound.toFixed(2)}` : '—'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {isForecast ? getConfidenceBadge(item.confidence_label) : (
                              <span className="text-slate-400 text-2xs font-medium">Accounting Truth</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                        No historical or forecast data available for selected filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Explanation & Model Backtest Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Deterministic Explanation */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <Sparkles className="w-5 h-5 text-[#0F6B56]" />
                <h3 className="text-base font-bold text-slate-900">Why this forecast?</h3>
              </div>

              <div className="text-xs text-slate-700 space-y-3 leading-relaxed">
                <p className="bg-slate-50 p-3 rounded-lg border border-slate-200 font-medium text-slate-800">
                  {forecastData?.explanation}
                </p>

                <div className="space-y-1.5">
                  <div className="font-semibold text-slate-900">Model Selection Methodology:</div>
                  <ul className="list-disc list-inside space-y-1 text-slate-600">
                    <li>Walk-forward backtesting evaluates model performance across historical periods without data leakage.</li>
                    <li>The model producing the lowest Mean Absolute Error (MAE) is automatically selected as optimal.</li>
                    <li>95% confidence bounds scale with forecast horizon uncertainty.</li>
                  </ul>
                </div>

                {forecastData?.growth_rate_pct !== null && forecastData?.growth_rate_pct !== undefined && (
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-600">Projected Period-over-Period Delta:</span>
                    <span className={forecastData.growth_rate_pct >= 0 ? 'text-amber-700' : 'text-emerald-700'}>
                      {forecastData.growth_rate_pct >= 0 ? `+${forecastData.growth_rate_pct.toFixed(2)}%` : `${forecastData.growth_rate_pct.toFixed(2)}%`}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Model Backtest Results Table */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <BarChart2 className="w-5 h-5 text-slate-700" />
                  <h3 className="text-base font-bold text-slate-900">Model Comparison & Backtesting</h3>
                </div>
                <span className="text-2xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">Walk-Forward</span>
              </div>

              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold">
                    <tr>
                      <th className="px-3 py-2 text-left">Model</th>
                      <th className="px-3 py-2 text-center">Periods</th>
                      <th className="px-3 py-2 text-right">MAE</th>
                      <th className="px-3 py-2 text-right">RMSE</th>
                      <th className="px-3 py-2 text-right">MAPE (%)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {backtestResults && backtestResults.length > 0 ? (
                      backtestResults.map((b, idx) => {
                        const isSelected = b.model === forecastData?.model_name;
                        return (
                          <tr key={idx} className={isSelected ? 'bg-teal-50/50 font-bold' : ''}>
                            <td className="px-3 py-2 font-medium text-slate-900 flex items-center gap-1.5">
                              {b.model}
                              {isSelected && <span className="text-2xs bg-[#0F6B56] text-white px-1.5 py-0.2 rounded">Selected</span>}
                            </td>
                            <td className="px-3 py-2 text-center text-slate-600">{b.periods_tested}</td>
                            <td className="px-3 py-2 text-right text-slate-900">{b.mae !== null ? b.mae.toFixed(2) : '—'}</td>
                            <td className="px-3 py-2 text-right text-slate-600">{b.rmse !== null ? b.rmse.toFixed(2) : '—'}</td>
                            <td className="px-3 py-2 text-right text-slate-600">{b.mape !== null ? `${b.mape.toFixed(1)}%` : '—'}</td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan={5} className="px-3 py-4 text-center text-slate-500 text-2xs">
                          Insufficient historical periods (&lt;4) for walk-forward backtesting comparison.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </>
      )}

    </div>
  );
}
