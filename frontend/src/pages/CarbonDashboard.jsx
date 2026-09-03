import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Layers, 
  Building2, 
  PieChart as PieChartIcon, 
  AlertCircle, 
  CheckCircle2, 
  FileText, 
  ArrowUpRight, 
  ArrowDownRight, 
  Filter, 
  RefreshCw, 
  Info, 
  ShieldCheck, 
  Activity, 
  Zap, 
  Flame, 
  Truck, 
  Droplets, 
  Trash2, 
  HelpCircle,
  ChevronRight
} from 'lucide-react';
import { getCarbonDashboard, getDocuments } from '../services/api';

export default function CarbonDashboard({ onNavigate }) {
  const [data, setData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');

  // Trend toggle
  const [trendMetric, setTrendMetric] = useState('total'); // 'total', 'scope_1', 'scope_2', 'scope_3'

  useEffect(() => {
    fetchDocumentsList();
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [selectedYear, selectedPeriod, selectedScope, selectedCategory, selectedDocId]);

  const fetchDocumentsList = async () => {
    try {
      const res = await getDocuments();
      setDocuments(res.items || res || []);
    } catch (err) {
      console.error("Failed to load documents list", err);
    }
  };

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (selectedYear) params.reporting_year = parseInt(selectedYear, 10);
      if (selectedPeriod) params.reporting_period = selectedPeriod;
      if (selectedScope) params.scope = selectedScope;
      if (selectedCategory) params.category = selectedCategory;
      if (selectedDocId) params.document_id = parseInt(selectedDocId, 10);

      const res = await getCarbonDashboard(params);
      setData(res);
    } catch (err) {
      console.error("Failed to fetch carbon dashboard", err);
      setError("Failed to load carbon footprint dashboard analytics. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const resetFilters = () => {
    setSelectedYear('');
    setSelectedPeriod('');
    setSelectedScope('');
    setSelectedCategory('');
    setSelectedDocId('');
  };

  const formatT = (val) => {
    if (val === null || val === undefined) return '—';
    return Number(val).toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 }) + ' tCO2e';
  };

  const formatKg = (val) => {
    if (val === null || val === undefined) return '—';
    return Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kgCO2e';
  };

  const getCategoryIcon = (cat) => {
    switch ((cat || '').toUpperCase()) {
      case 'ENERGY': return <Zap className="w-4 h-4 text-amber-600" />;
      case 'FUEL': return <Flame className="w-4 h-4 text-orange-600" />;
      case 'TRANSPORT': return <Truck className="w-4 h-4 text-blue-600" />;
      case 'WATER': return <Droplets className="w-4 h-4 text-cyan-600" />;
      case 'WASTE': return <Trash2 className="w-4 h-4 text-stone-600" />;
      default: return <Activity className="w-4 h-4 text-emerald-600" />;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Carbon Footprint</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              Deterministic Analytics v1.0
            </span>
          </div>
          <p className="text-slate-600 mt-1">
            Calculated footprint from posted accounting records • Strictly auditable
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate && onNavigate('/carbon-ledger')}
            className="px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm"
          >
            <Layers className="w-4 h-4 text-slate-500" />
            Accounting Ledger
          </button>
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="px-3.5 py-2 text-sm font-medium text-white bg-[#0F6B56] hover:bg-[#0c5645] rounded-lg transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-3 text-sm">
        <div className="flex items-center gap-2 text-slate-700 font-semibold mr-1">
          <Filter className="w-4 h-4 text-[#0F6B56]" />
          <span>Filters:</span>
        </div>

        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]/20 focus:border-[#0F6B56]"
        >
          <option value="">All Years</option>
          {data?.trends?.years?.map(y => (
            <option key={y.year} value={y.year}>{y.year}</option>
          )) || <option value="2024">2024</option>}
        </select>

        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]/20 focus:border-[#0F6B56]"
        >
          <option value="">All Periods</option>
          {data?.trends?.periods?.map(p => (
            <option key={p.reporting_period} value={p.reporting_period}>{p.reporting_period}</option>
          )) || <option value="2024-10">2024-10</option>}
        </select>

        <select
          value={selectedScope}
          onChange={(e) => setSelectedScope(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]/20 focus:border-[#0F6B56]"
        >
          <option value="">All Scopes</option>
          <option value="SCOPE_1">Scope 1 (Direct Fuel)</option>
          <option value="SCOPE_2">Scope 2 (Electricity)</option>
          <option value="SCOPE_3">Scope 3 (Value Chain)</option>
        </select>

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]/20 focus:border-[#0F6B56]"
        >
          <option value="">All Categories</option>
          <option value="ENERGY">Energy</option>
          <option value="FUEL">Fuel</option>
          <option value="TRANSPORT">Transport</option>
          <option value="WATER">Water</option>
          <option value="WASTE">Waste</option>
          <option value="OTHER">Other</option>
        </select>

        <select
          value={selectedDocId}
          onChange={(e) => setSelectedDocId(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F6B56]/20 focus:border-[#0F6B56] max-w-xs"
        >
          <option value="">All Documents</option>
          {documents.map(d => (
            <option key={d.id} value={d.id}>Doc #{d.id} - {d.company_name || d.original_filename || d.filename}</option>
          ))}
        </select>

        {(selectedYear || selectedPeriod || selectedScope || selectedCategory || selectedDocId) && (
          <button
            onClick={resetFilters}
            className="text-xs font-semibold text-rose-600 hover:text-rose-700 ml-auto px-2 py-1 bg-rose-50 hover:bg-rose-100 rounded border border-rose-200"
          >
            Reset Filters
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Total Footprint */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#0F6B56]">Total Carbon Footprint</span>
            <ShieldCheck className="w-5 h-5 text-[#0F6B56]" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900">
            {formatT(data?.summary?.total_calculated_co2e_t)}
          </div>
          <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
            <span>{formatKg(data?.summary?.total_calculated_co2e_kg)}</span>
            <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              {data?.summary?.posted_entry_count || 0} Posted Entries
            </span>
          </div>
        </div>

        {/* Scope 1 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Scope 1 (Fuel)</span>
            <Flame className="w-4 h-4 text-orange-600" />
          </div>
          <div className="text-xl font-bold text-slate-900">
            {formatT(data?.summary?.scope_1_co2e_t)}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {data?.summary?.scope_1_co2e_kg ? formatKg(data.summary.scope_1_co2e_kg) : 'No direct emissions'}
          </p>
        </div>

        {/* Scope 2 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Scope 2 (Electricity)</span>
            <Zap className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-xl font-bold text-slate-900">
            {formatT(data?.summary?.scope_2_co2e_t)}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {data?.summary?.scope_2_co2e_kg ? formatKg(data.summary.scope_2_co2e_kg) : 'No grid emissions'}
          </p>
        </div>

        {/* Scope 3 */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Scope 3 (Supply Chain)</span>
            <Truck className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-xl font-bold text-slate-900">
            {formatT(data?.summary?.scope_3_co2e_t)}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {data?.summary?.scope_3_co2e_t !== null && data?.summary?.scope_3_co2e_t !== undefined ? formatKg(data.summary.scope_3_co2e_kg) : 'No calculated data'}
          </p>
        </div>

        {/* Reporting Periods */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Periods</span>
            <TrendingUp className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-xl font-bold text-slate-900">
            {data?.summary?.reporting_period_count || 0}
          </div>
          <p className="text-xs text-slate-500 mt-1 truncate" title={data?.summary?.latest_reporting_period || 'N/A'}>
            Latest: <span className="font-medium text-slate-700">{data?.summary?.latest_reporting_period || 'None'}</span>
          </p>
        </div>
      </div>

      {/* Main Grid: Scope Breakdown & Historical Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Scope Breakdown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <PieChartIcon className="w-5 h-5 text-[#0F6B56]" />
                <h2 className="text-lg font-bold text-slate-900">Scope Distribution</h2>
              </div>
              <span className="text-xs text-slate-500 font-medium">100% Deterministic</span>
            </div>

            <div className="space-y-4">
              {data?.scopes?.items?.map(sc => (
                <div key={sc.scope} className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-semibold text-slate-800">{sc.scope_label}</span>
                    <span className="text-sm font-bold text-slate-900">{formatT(sc.co2e_t)}</span>
                  </div>
                  <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mb-1.5">
                    <div 
                      className={`h-full rounded-full ${
                        sc.scope === 'SCOPE_1' ? 'bg-orange-500' :
                        sc.scope === 'SCOPE_2' ? 'bg-amber-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${sc.percentage_of_total || 0}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{sc.entry_count} posted entries</span>
                    <span className="font-semibold text-slate-700">
                      {sc.percentage_of_total !== null && sc.percentage_of_total !== undefined ? `${sc.percentage_of_total}% share` : '—'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>Total Posted Emissions:</span>
            <span className="font-bold text-slate-900">{formatT(data?.scopes?.total_co2e_t)}</span>
          </div>
        </div>

        {/* Historical Reporting-Period Trends */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-7 flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-[#0F6B56]" />
                <h2 className="text-lg font-bold text-slate-900">Historical Reporting Periods</h2>
              </div>

              {/* Toggle metric */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold text-slate-600">
                <button
                  onClick={() => setTrendMetric('total')}
                  className={`px-2.5 py-1 rounded ${trendMetric === 'total' ? 'bg-white text-slate-900 shadow-sm' : 'hover:text-slate-900'}`}
                >
                  Total
                </button>
                <button
                  onClick={() => setTrendMetric('scope_1')}
                  className={`px-2.5 py-1 rounded ${trendMetric === 'scope_1' ? 'bg-white text-orange-600 shadow-sm' : 'hover:text-slate-900'}`}
                >
                  Scope 1
                </button>
                <button
                  onClick={() => setTrendMetric('scope_2')}
                  className={`px-2.5 py-1 rounded ${trendMetric === 'scope_2' ? 'bg-white text-amber-600 shadow-sm' : 'hover:text-slate-900'}`}
                >
                  Scope 2
                </button>
                <button
                  onClick={() => setTrendMetric('scope_3')}
                  className={`px-2.5 py-1 rounded ${trendMetric === 'scope_3' ? 'bg-white text-blue-600 shadow-sm' : 'hover:text-slate-900'}`}
                >
                  Scope 3
                </button>
              </div>
            </div>

            {/* Trend Points or Single Period Banner */}
            {data?.trends?.periods?.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-lg border border-slate-100">
                No historical reporting periods posted in ledger.
              </div>
            ) : data?.trends?.periods?.length === 1 ? (
              <div className="space-y-4">
                <div className="p-6 bg-slate-50 rounded-xl border border-slate-200/80 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                      Single Available Period
                    </div>
                    <div className="text-2xl font-bold text-slate-900">
                      {data.trends.periods[0].reporting_period}
                    </div>
                    <div className="text-sm text-slate-600 mt-0.5">
                      Posted footprint: <span className="font-semibold text-[#0F6B56]">{formatT(data.trends.periods[0].total_co2e_t)}</span> ({data.trends.periods[0].entry_count} entries)
                    </div>
                  </div>
                  <div className="px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs font-medium flex items-center gap-2 max-w-sm">
                    <Info className="w-4 h-4 flex-shrink-0 text-amber-600" />
                    <span>{data?.trends?.comparison?.message || "More reporting periods are needed to show a trend."}</span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-xs text-slate-500 block">Scope 1</span>
                    <span className="text-sm font-bold text-slate-800">{formatT(data.trends.periods[0].scope_1_t)}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-xs text-slate-500 block">Scope 2</span>
                    <span className="text-sm font-bold text-slate-800">{formatT(data.trends.periods[0].scope_2_t)}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-xs text-slate-500 block">Scope 3</span>
                    <span className="text-sm font-bold text-slate-800">{formatT(data.trends.periods[0].scope_3_t)}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 text-xs font-semibold">
                        <th className="pb-2">Period</th>
                        <th className="pb-2">Total tCO2e</th>
                        <th className="pb-2">Scope 1</th>
                        <th className="pb-2">Scope 2</th>
                        <th className="pb-2">Scope 3</th>
                        <th className="pb-2 text-right">Entries</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {data.trends.periods.map(p => (
                        <tr key={p.reporting_period} className="hover:bg-slate-50">
                          <td className="py-2.5 font-semibold text-slate-900">{p.reporting_period}</td>
                          <td className="py-2.5 font-bold text-[#0F6B56]">{formatT(p.total_co2e_t)}</td>
                          <td className="py-2.5 text-slate-700">{formatT(p.scope_1_t)}</td>
                          <td className="py-2.5 text-slate-700">{formatT(p.scope_2_t)}</td>
                          <td className="py-2.5 text-slate-700">{formatT(p.scope_3_t)}</td>
                          <td className="py-2.5 text-right text-slate-500">{p.entry_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {data?.trends?.comparison?.comparison_available && (
                  <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-center justify-between">
                    <span className="font-semibold">{data.trends.comparison.message}</span>
                    {data.trends.comparison.percentage_change !== null && (
                      <span className="font-bold">
                        {data.trends.comparison.percentage_change > 0 ? `+${data.trends.comparison.percentage_change}%` : `${data.trends.comparison.percentage_change}%`}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>Historical aggregated points: {data?.trends?.periods?.length || 0}</span>
            <span>No zero-fabrication of missing dates</span>
          </div>
        </div>
      </div>

      {/* Secondary Grid: Top Emission Sources & Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Top Emission Sources */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-[#0F6B56]" />
              <h2 className="text-lg font-bold text-slate-900">Top Emission Sources</h2>
            </div>
            <span className="text-xs text-slate-500">Ranked by posted CO2e</span>
          </div>

          <div className="space-y-3">
            {data?.top_sources?.items?.length === 0 ? (
              <p className="text-sm text-slate-500 py-4 text-center">No posted emission sources found.</p>
            ) : (
              data?.top_sources?.items?.map(src => (
                <div key={src.rank} className="p-3 bg-slate-50 hover:bg-slate-100/80 rounded-lg border border-slate-200/80 flex items-center justify-between transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold flex items-center justify-center">
                      #{src.rank}
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-slate-900 capitalize">
                        {src.activity_type.replace(/_/g, ' ')}
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-2">
                        <span>{src.category}</span>
                        <span>•</span>
                        <span className="font-medium text-slate-700">{src.scope}</span>
                        {src.document_name && (
                          <>
                            <span>•</span>
                            <span className="truncate max-w-[150px]">{src.document_name}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-bold text-slate-900">{formatT(src.co2e_t)}</div>
                    <div className="text-xs font-semibold text-emerald-700">
                      {src.percentage_of_total !== null ? `${src.percentage_of_total}% share` : '—'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-[#0F6B56]" />
              <h2 className="text-lg font-bold text-slate-900">Emissions by Category</h2>
            </div>
            <span className="text-xs text-slate-500">{data?.categories?.items?.length || 0} Categories</span>
          </div>

          <div className="space-y-3">
            {data?.categories?.items?.length === 0 ? (
              <p className="text-sm text-slate-500 py-4 text-center">No category data available.</p>
            ) : (
              data?.categories?.items?.map(cat => (
                <div key={cat.category} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded border border-slate-200">
                      {getCategoryIcon(cat.category)}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{cat.category}</div>
                      <div className="text-xs text-slate-500">{cat.entry_count} posted entries</div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-bold text-slate-900">{formatT(cat.co2e_t)}</div>
                    <div className="text-xs font-semibold text-emerald-700">
                      {cat.percentage_of_total !== null ? `${cat.percentage_of_total}%` : '—'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Document Contribution Table */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#0F6B56]" />
            <h2 className="text-lg font-bold text-slate-900">Document Contribution</h2>
          </div>
          <span className="text-xs text-slate-500 font-medium">{data?.documents?.total_documents || 0} Contributing Documents</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                <th className="pb-3">Document</th>
                <th className="pb-3">Period</th>
                <th className="pb-3">Scope 1 (tCO2e)</th>
                <th className="pb-3">Scope 2 (tCO2e)</th>
                <th className="pb-3">Scope 3 (tCO2e)</th>
                <th className="pb-3">Total Calculated</th>
                <th className="pb-3">Share</th>
                <th className="pb-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.documents?.items?.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-6 text-center text-slate-500">
                    No contributing documents found matching filters.
                  </td>
                </tr>
              ) : (
                data?.documents?.items?.map(doc => (
                  <tr key={doc.document_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-400" />
                        <span>{doc.document_name}</span>
                        <span className="text-xs font-normal text-slate-400">#{doc.document_id}</span>
                      </div>
                    </td>
                    <td className="py-3 text-slate-600">{doc.reporting_period || '—'}</td>
                    <td className="py-3 text-slate-700">{formatT(doc.scope_1_t)}</td>
                    <td className="py-3 text-slate-700">{formatT(doc.scope_2_t)}</td>
                    <td className="py-3 text-slate-700">{formatT(doc.scope_3_t)}</td>
                    <td className="py-3 font-bold text-[#0F6B56]">{formatT(doc.total_co2e_t)}</td>
                    <td className="py-3 font-semibold text-slate-700">
                      {doc.percentage_of_total !== null ? `${doc.percentage_of_total}%` : '—'}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => onNavigate && onNavigate(`/documents/${doc.document_id}`)}
                        className="px-2.5 py-1 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded border border-emerald-200 inline-flex items-center gap-1"
                      >
                        Details
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Row: Data Coverage & Extracted vs Calculated Reconciliation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Data Coverage & Quality */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-[#0F6B56]" />
              <h2 className="text-lg font-bold text-slate-900">Data Coverage & Audit Quality</h2>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">Total Activities</span>
              <span className="text-base font-bold text-slate-900">{data?.coverage?.total_activity_records || 0}</span>
            </div>
            <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
              <span className="text-xs text-emerald-700 block">Posted Ledger</span>
              <span className="text-base font-bold text-emerald-800">{data?.coverage?.posted_ledger_records || 0}</span>
            </div>
            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
              <span className="text-xs text-amber-700 block">Excluded Records</span>
              <span className="text-base font-bold text-amber-800">{data?.coverage?.excluded_records || 0}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">No Factor</span>
              <span className="text-base font-bold text-slate-700">{data?.coverage?.no_factor_records || 0}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">Ineligible</span>
              <span className="text-base font-bold text-slate-700">{data?.coverage?.ineligible_records || 0}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block">Superseded</span>
              <span className="text-base font-bold text-slate-700">{data?.coverage?.superseded_records || 0}</span>
            </div>
          </div>

          <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">{data?.coverage?.notice || "Excluded records are not treated as zero emissions."}</p>
              <p className="text-amber-800 mt-0.5">
                Activities without matched emission factors or operational supporting metrics are transparently tracked but excluded from footprint totals.
              </p>
            </div>
          </div>
        </div>

        {/* Extracted vs Calculated Reconciliation */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm lg:col-span-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#0F6B56]" />
              <h2 className="text-lg font-bold text-slate-900">Extracted vs Calculated Footprint</h2>
            </div>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
              data?.reconciliation?.overall_status === 'MATCH' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
              data?.reconciliation?.overall_status === 'DIFFERENCE' ? 'bg-amber-50 text-amber-700 border-amber-200' :
              'bg-slate-50 text-slate-600 border-slate-200'
            }`}>
              {data?.reconciliation?.overall_status || 'NO_DATA'}
            </span>
          </div>

          <div className="space-y-3 mb-4">
            {data?.reconciliation?.items?.map((item, idx) => (
              <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{item.scope_or_metric}</div>
                  <div className="text-xs text-slate-500">
                    Extracted: <span className="font-medium text-slate-700">{formatT(item.extracted_value_t)}</span> • Calculated: <span className="font-medium text-[#0F6B56]">{formatT(item.calculated_value_t)}</span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs font-bold text-slate-800">
                    Diff: {item.difference_t !== null && item.difference_t !== undefined ? `${item.difference_t > 0 ? '+' : ''}${item.difference_t} tCO2e` : '—'}
                  </div>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                    item.status === 'MATCH' ? 'bg-emerald-100 text-emerald-800' :
                    item.status === 'DIFFERENCE' ? 'bg-amber-100 text-amber-800' :
                    'bg-slate-200 text-slate-700'
                  }`}>
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="text-xs text-slate-500 bg-slate-50 p-2.5 rounded border border-slate-200">
            Reconciliation preserves extracted values verbatim while establishing an independent, auditable accounting footprint.
          </div>
        </div>
      </div>
    </div>
  );
}
