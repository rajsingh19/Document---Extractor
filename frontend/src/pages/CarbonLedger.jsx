import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Filter,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ShieldCheck,
  ChevronRight,
  X,
  Hash,
  Layers,
  FileText,
  Info,
  Calendar,
  Building2,
  Archive,
  ArrowRight,
  Calculator,
  Compass
} from 'lucide-react';
import { getCarbonLedger, getCarbonLedgerSummary } from '../services/api';

export default function CarbonLedger() {
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedActivityType, setSelectedActivityType] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');
  const [selectedYear, setSelectedYear] = useState('');

  // Detail Drawer
  const [selectedEntry, setSelectedEntry] = useState(null);

  const fetchLedgerData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (selectedStatus) params.accounting_status = selectedStatus;
      if (selectedScope) params.scope = selectedScope;
      if (selectedCategory) params.category = selectedCategory;
      if (selectedActivityType) params.activity_type = selectedActivityType;
      if (selectedDocId) params.document_id = parseInt(selectedDocId, 10);
      if (selectedYear) params.reporting_year = parseInt(selectedYear, 10);

      const [listData, summaryData] = await Promise.all([
        getCarbonLedger(params),
        getCarbonLedgerSummary(params).catch(() => null),
      ]);

      setEntries(listData.items || []);
      if (summaryData) {
        setSummary(summaryData);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load carbon ledger records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedgerData();
  }, [selectedStatus, selectedScope, selectedCategory, selectedActivityType, selectedDocId, selectedYear]);

  // Derived Summary Totals
  const postedEntries = entries.filter((e) => e.accounting_status === 'POSTED');
  const totalPostedCo2e = postedEntries.reduce((acc, e) => acc + (e.calculated_co2e || 0), 0);
  const scope1Co2e = postedEntries.filter((e) => e.scope === 'SCOPE_1').reduce((acc, e) => acc + (e.calculated_co2e || 0), 0);
  const scope2Co2e = postedEntries.filter((e) => e.scope === 'SCOPE_2').reduce((acc, e) => acc + (e.calculated_co2e || 0), 0);
  const scope3Co2e = postedEntries.filter((e) => e.scope === 'SCOPE_3').reduce((acc, e) => acc + (e.calculated_co2e || 0), 0);
  const excludedCount = entries.filter((e) => e.accounting_status === 'EXCLUDED').length;
  const supersededCount = entries.filter((e) => e.accounting_status === 'SUPERSEDED').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'POSTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> POSTED
          </span>
        );
      case 'EXCLUDED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" /> EXCLUDED
          </span>
        );
      case 'SUPERSEDED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <Archive className="w-3 h-3 text-slate-500" /> SUPERSEDED
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <Info className="w-3 h-3 text-blue-600" /> PENDING
          </span>
        );
      case 'INVALID':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
            <XCircle className="w-3 h-3 text-red-600" /> INVALID
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
            {status}
          </span>
        );
    }
  };

  const getCategoryBadge = (cat) => {
    const c = (cat || 'OTHER').toUpperCase();
    const colors = {
      ENERGY: 'bg-amber-50 text-amber-700 border-amber-200',
      FUEL: 'bg-orange-50 text-orange-700 border-orange-200',
      TRANSPORT: 'bg-blue-50 text-blue-700 border-blue-200',
      WATER: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      WASTE: 'bg-rose-50 text-rose-700 border-rose-200',
      OTHER: 'bg-slate-50 text-slate-700 border-slate-200',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${colors[c] || colors.OTHER}`}>
        {c}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-6 max-w-7xl mx-auto space-y-6 font-sans">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded-full border border-emerald-200">
              Step 14 Accounting Ledger
            </span>
            <span className="px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 rounded-full">
              v1.0 Immutable &amp; Auditable
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-[#0F6B56]" />
            Carbon Accounting Ledger
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Deterministic accounting layer organized by document, scope, period, and category with full provenance and double-counting protection.
          </p>
        </div>

        <button
          onClick={fetchLedgerData}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
        >
          <RefreshCw className={`w-4 h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          Refresh Ledger
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Posted</p>
          <p className="text-xl font-bold text-slate-900 mt-1 font-mono">
            {totalPostedCo2e.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            kgCO₂e ({(totalPostedCo2e / 1000).toFixed(2)} t)
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">Scope 1 Direct</p>
          <p className="text-xl font-bold text-slate-900 mt-1 font-mono">
            {scope1Co2e.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            kgCO₂e ({(scope1Co2e / 1000).toFixed(2)} t)
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-[11px] font-semibold text-blue-700 uppercase tracking-wider">Scope 2 Indirect</p>
          <p className="text-xl font-bold text-slate-900 mt-1 font-mono">
            {scope2Co2e.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            kgCO₂e ({(scope2Co2e / 1000).toFixed(2)} t)
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-[11px] font-semibold text-purple-700 uppercase tracking-wider">Scope 3 Value Chain</p>
          <p className="text-xl font-bold text-slate-900 mt-1 font-mono">
            {scope3Co2e.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            kgCO₂e ({(scope3Co2e / 1000).toFixed(2)} t)
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">Excluded</p>
          <p className="text-xl font-bold text-slate-900 mt-1 font-mono">{excludedCount}</p>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">Zero/No Factor/Totals</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Superseded</p>
          <p className="text-xl font-bold text-slate-900 mt-1 font-mono">{supersededCount}</p>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">Historical Versions</p>
        </div>
      </div>

      {/* Double-Counting Protection Banner */}
      <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <div className="flex items-center space-x-2 text-emerald-900 font-semibold">
          <ShieldCheck className="w-4 h-4 text-[#0F6B56]" />
          <span>Double-Counting Protected Accounting Layer</span>
        </div>
        <p className="text-slate-600 text-xs">
          Constituent components are posted; aggregate group totals are strictly excluded from sums.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          Filter Accounting Ledger
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-xs">
          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">Accounting Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-[#0F6B56]"
            >
              <option value="">All Statuses</option>
              <option value="POSTED">POSTED</option>
              <option value="EXCLUDED">EXCLUDED</option>
              <option value="SUPERSEDED">SUPERSEDED</option>
              <option value="PENDING">PENDING</option>
              <option value="INVALID">INVALID</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">GHG Scope</label>
            <select
              value={selectedScope}
              onChange={(e) => setSelectedScope(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-[#0F6B56]"
            >
              <option value="">All Scopes</option>
              <option value="SCOPE_1">Scope 1</option>
              <option value="SCOPE_2">Scope 2</option>
              <option value="SCOPE_3">Scope 3</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-[#0F6B56]"
            >
              <option value="">All Categories</option>
              <option value="ENERGY">ENERGY</option>
              <option value="FUEL">FUEL</option>
              <option value="TRANSPORT">TRANSPORT</option>
              <option value="WATER">WATER</option>
              <option value="WASTE">WASTE</option>
              <option value="OTHER">OTHER</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">Activity Type</label>
            <input
              type="text"
              placeholder="e.g. purchased_electricity"
              value={selectedActivityType}
              onChange={(e) => setSelectedActivityType(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-[#0F6B56]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">Document ID</label>
            <input
              type="number"
              placeholder="e.g. 1"
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-[#0F6B56]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">Reporting Year</label>
            <input
              type="number"
              placeholder="e.g. 2024"
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 focus:outline-hidden focus:ring-1 focus:ring-[#0F6B56]"
            />
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Date / ID</th>
                <th className="py-3 px-4">Activity</th>
                <th className="py-3 px-3">Category</th>
                <th className="py-3 px-3">Scope</th>
                <th className="py-3 px-4 text-right">Quantity</th>
                <th className="py-3 px-4 text-right">Calculated CO₂e</th>
                <th className="py-3 px-3">Period</th>
                <th className="py-3 px-3">Doc</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan="10" className="py-8 text-center text-slate-400">
                    Loading accounting ledger entries...
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan="10" className="py-8 text-center text-slate-400">
                    No ledger entries found matching active filters.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr
                    key={entry.id}
                    onClick={() => setSelectedEntry(entry)}
                    className={`hover:bg-slate-50 cursor-pointer transition-colors ${
                      entry.accounting_status === 'SUPERSEDED' ? 'opacity-60 bg-slate-50/40' : ''
                    }`}
                  >
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-600">
                      <div className="font-semibold text-slate-900">#{entry.id}</div>
                      <div className="text-[10px] text-slate-400">
                        {entry.created_at ? new Date(entry.created_at).toLocaleDateString() : '—'}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 capitalize">
                        {entry.activity_type.replace(/_/g, ' ')}
                      </div>
                      {entry.activity_group_id && (
                        <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1 mt-0.5">
                          <Layers className="w-2.5 h-2.5 text-purple-500" />
                          <span>{entry.activity_role}: {entry.activity_group_id}</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {getCategoryBadge(entry.category)}
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-mono font-medium text-slate-700">
                        {entry.scope || '—'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-slate-800">
                      {entry.quantity != null ? entry.quantity.toLocaleString() : '—'} {entry.activity_unit}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold">
                      {entry.accounting_status === 'POSTED' && entry.calculated_co2e != null ? (
                        <span className="text-emerald-800">
                          {entry.calculated_co2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })} kg
                        </span>
                      ) : (
                        <span className="text-slate-400 font-normal italic">
                          {entry.accounting_status === 'EXCLUDED' ? 'Excluded' : '—'}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-slate-600 font-medium">
                      {entry.reporting_period || entry.reporting_year || '—'}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-600">
                      {entry.document_id ? `#${entry.document_id}` : '—'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {getStatusBadge(entry.accounting_status)}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <ChevronRight className="w-4 h-4 text-slate-400 inline" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ledger Detail Drawer */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-2xs flex justify-end">
          <div className="bg-white w-full max-w-xl h-full shadow-2xl border-l border-slate-200 flex flex-col overflow-y-auto">
            
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center space-x-2">
                <BookOpen className="w-5 h-5 text-[#0F6B56]" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Ledger Entry Audit Detail (#{selectedEntry.id})
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    Ledger v{selectedEntry.ledger_version} &bull; Calc v{selectedEntry.calculation_version}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedEntry(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="p-5 space-y-5 text-xs flex-1">
              
              {/* Status Section */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">Accounting Status</span>
                  {getStatusBadge(selectedEntry.accounting_status)}
                </div>
                {selectedEntry.accounting_reason && (
                  <p className="text-xs text-slate-600 bg-white p-2.5 rounded-lg border border-slate-200 font-sans">
                    {selectedEntry.accounting_reason}
                  </p>
                )}
              </div>

              {/* Activity Snapshot */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-[#0F6B56]" />
                  Activity Snapshot
                </h4>
                <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Activity Type</span>
                    <span className="font-semibold text-slate-900">{selectedEntry.activity_type}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Category</span>
                    <span>{getCategoryBadge(selectedEntry.category)}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Activity Role</span>
                    <span className="font-semibold text-slate-900">{selectedEntry.activity_role}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Activity Group ID</span>
                    <span className="font-mono text-slate-800">{selectedEntry.activity_group_id || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Physical Quantity</span>
                    <span className="font-mono font-bold text-slate-900">
                      {selectedEntry.quantity != null ? selectedEntry.quantity.toLocaleString() : '—'} {selectedEntry.activity_unit}
                    </span>
                  </div>
                </div>
              </div>

              {/* Calculation & Emission Factor Snapshot */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Calculator className="w-3.5 h-3.5 text-[#0F6B56]" />
                  Calculation &amp; Factor Snapshot
                </h4>
                <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Calculated CO₂e</span>
                    <span className="font-mono font-bold text-emerald-800">
                      {selectedEntry.calculated_co2e != null ? `${selectedEntry.calculated_co2e.toLocaleString()} kgCO₂e` : '—'}
                    </span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Scope</span>
                    <span className="font-semibold text-slate-900">{selectedEntry.scope || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Emission Factor Code</span>
                    <span className="font-mono text-slate-800">{selectedEntry.factor_code || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Emission Factor Value</span>
                    <span className="font-mono text-slate-800">
                      {selectedEntry.factor_value != null ? `${selectedEntry.factor_value} ${selectedEntry.factor_unit || ''}` : '—'}
                    </span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Factor Source &amp; Version</span>
                    <span className="text-slate-800">
                      {selectedEntry.factor_source || '—'} (v{selectedEntry.factor_version || '1.0'})
                    </span>
                  </div>
                </div>
              </div>

              {/* Accounting Dimensions */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5 text-[#0F6B56]" />
                  Accounting Dimensions
                </h4>
                <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Geography</span>
                    <span className="font-semibold text-slate-900">{selectedEntry.geography || 'Unspecified'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Reporting Period</span>
                    <span className="font-semibold text-slate-900">{selectedEntry.reporting_period || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Reporting Year</span>
                    <span className="font-semibold text-slate-900">{selectedEntry.reporting_year || '—'}</span>
                  </div>
                </div>
              </div>

              {/* Provenance & Audit Lineage */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#0F6B56]" />
                  Audit Lineage &amp; Provenance
                </h4>
                <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Document ID</span>
                    <span className="font-mono text-slate-800">#{selectedEntry.document_id || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Carbon Calculation ID</span>
                    <span className="font-mono text-slate-800">#{selectedEntry.carbon_calculation_id}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Activity Data ID</span>
                    <span className="font-mono text-slate-800">#{selectedEntry.activity_data_id || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Metric ID</span>
                    <span className="font-mono text-slate-800">#{selectedEntry.metric_id || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Source Field</span>
                    <span className="font-mono text-slate-800">{selectedEntry.source_field || '—'}</span>
                  </div>
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Source Page</span>
                    <span className="font-mono text-slate-800">Page {selectedEntry.page || 1}</span>
                  </div>
                  {selectedEntry.source_text && (
                    <div className="p-2.5 space-y-1">
                      <span className="text-slate-500 block">Verbatim Source Evidence:</span>
                      <p className="text-slate-900 font-mono bg-slate-50 p-2 rounded border border-slate-100 text-[11px]">
                        {selectedEntry.source_text}
                      </p>
                    </div>
                  )}
                  <div className="p-2.5 flex justify-between">
                    <span className="text-slate-500">Created / Updated</span>
                    <span className="text-slate-600 font-mono text-[11px]">
                      {selectedEntry.created_at ? new Date(selectedEntry.created_at).toLocaleString() : '—'}
                    </span>
                  </div>
                </div>
              </div>

            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setSelectedEntry(null)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-lg text-xs font-semibold transition-colors"
              >
                Close Drawer
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
