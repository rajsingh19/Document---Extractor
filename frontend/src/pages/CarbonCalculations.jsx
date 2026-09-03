import React, { useState, useEffect } from 'react';
import {
  Calculator,
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
  ArrowRight
} from 'lucide-react';
import { getCarbonCalculations, calculateActivityCarbon } from '../services/api';

export default function CarbonCalculationsPage() {
  const [calculations, setCalculations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');

  // Detail Modal
  const [selectedItem, setSelectedItem] = useState(null);

  const fetchCalculations = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (selectedStatus) params.status = selectedStatus;
      if (selectedScope) params.scope = selectedScope;
      if (selectedType) params.activity_type = selectedType;
      if (selectedDocId) params.document_id = parseInt(selectedDocId, 10);

      const data = await getCarbonCalculations(params);
      setCalculations(data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load carbon calculation records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalculations();
  }, [selectedStatus, selectedScope, selectedType, selectedDocId]);

  // Summary Metrics
  const calculatedItems = calculations.filter((c) => c.status === 'CALCULATED');
  const totalCo2e = calculatedItems.reduce((acc, c) => acc + (c.calculated_co2e || 0), 0);
  const scope1Co2e = calculatedItems.filter((c) => c.scope === 'SCOPE_1').reduce((acc, c) => acc + (c.calculated_co2e || 0), 0);
  const scope2Co2e = calculatedItems.filter((c) => c.scope === 'SCOPE_2').reduce((acc, c) => acc + (c.calculated_co2e || 0), 0);
  const scope3Co2e = calculatedItems.filter((c) => c.scope === 'SCOPE_3').reduce((acc, c) => acc + (c.calculated_co2e || 0), 0);
  const reviewCount = calculations.filter((c) => c.status !== 'CALCULATED').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'CALCULATED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> CALCULATED
          </span>
        );
      case 'INELIGIBLE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
            <XCircle className="w-3 h-3 text-slate-400" /> INELIGIBLE
          </span>
        );
      case 'NO_FACTOR':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">
            <AlertTriangle className="w-3 h-3 text-amber-600" /> NO FACTOR
          </span>
        );
      case 'MULTIPLE_FACTORS':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">
            <HelpCircle className="w-3 h-3 text-amber-600" /> MULTIPLE
          </span>
        );
      case 'MISSING_GEOGRAPHY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
            <Info className="w-3 h-3 text-blue-600" /> NO GEOGRAPHY
          </span>
        );
      case 'MISSING_YEAR':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
            <Info className="w-3 h-3 text-blue-600" /> NO YEAR
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800">
            <XCircle className="w-3 h-3 text-red-600" /> {status}
          </span>
        );
    }
  };

  const getRoleBadge = (role) => {
    switch (role) {
      case 'TOTAL':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800">TOTAL</span>;
      case 'COMPONENT':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">COMPONENT</span>;
      case 'SUPPORTING':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">SUPPORTING</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">{role}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded-full border border-emerald-200">
              Step 13 Engine
            </span>
            <span className="px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 rounded-full">
              v1.0 Decimal ROUND_HALF_UP
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Calculator className="w-6 h-6 text-emerald-600" />
            Carbon Calculation Ledger
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Deterministic CO2e calculations computed from canonical activity quantities and resolved emission factors.
          </p>
        </div>

        <button
          onClick={fetchCalculations}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Notice Banner: Extracted vs Calculated */}
      <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-950 flex items-start gap-3 shadow-xs">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-emerald-900 text-sm">Extracted Emissions ≠ Calculated Emissions</p>
          <p>
            This ledger stores newly computed CO2e values separate from extracted sustainability metrics.
            Document #1's original extracted emissions (Scope 1: <strong>1.13 tCO2e</strong>, Scope 2: <strong>31.88 tCO2e</strong>, Total: <strong>33.01 tCO2e</strong>) remain untouched.
            Double-counting protection ensures related electricity components (Grid 44,900 kWh) are calculated without redundantly adding Total Electricity (48,750 kWh) to document aggregation.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-medium text-slate-500 block">Total Calculated CO2e</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-1 block">
            {totalCo2e.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-sans font-normal text-slate-500">kgCO2e</span>
          </span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">
            ≈ {(totalCo2e / 1000).toFixed(2)} tCO2e
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-medium text-slate-500 block">Scope 1 (Direct Fuel)</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-1 block">
            {scope1Co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-sans font-normal text-slate-500">kgCO2e</span>
          </span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">
            ≈ {(scope1Co2e / 1000).toFixed(2)} tCO2e
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-medium text-slate-500 block">Scope 2 (Electricity)</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-1 block">
            {scope2Co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-sans font-normal text-slate-500">kgCO2e</span>
          </span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">
            ≈ {(scope2Co2e / 1000).toFixed(2)} tCO2e
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-medium text-slate-500 block">Scope 3 (Value Chain)</span>
          <span className="text-xl font-bold font-mono text-slate-900 mt-1 block">
            {scope3Co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-sans font-normal text-slate-500">kgCO2e</span>
          </span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">
            ≈ {(scope3Co2e / 1000).toFixed(2)} tCO2e
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-medium text-slate-500 block">Non-Calculated Items</span>
          <span className="text-xl font-bold font-mono text-slate-700 mt-1 block">
            {reviewCount} <span className="text-xs font-sans font-normal text-slate-400">items</span>
          </span>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Ineligible / No factor</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" /> Filters
          </span>
          {(selectedStatus || selectedScope || selectedType || selectedDocId) && (
            <button
              onClick={() => {
                setSelectedStatus('');
                setSelectedScope('');
                setSelectedType('');
                setSelectedDocId('');
              }}
              className="text-xs text-emerald-600 hover:text-emerald-800 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Statuses</option>
              <option value="CALCULATED">CALCULATED</option>
              <option value="INELIGIBLE">INELIGIBLE</option>
              <option value="NO_FACTOR">NO_FACTOR</option>
              <option value="MULTIPLE_FACTORS">MULTIPLE_FACTORS</option>
              <option value="MISSING_GEOGRAPHY">MISSING_GEOGRAPHY</option>
              <option value="MISSING_YEAR">MISSING_YEAR</option>
              <option value="INVALID_ACTIVITY">INVALID_ACTIVITY</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Scope</label>
            <select
              value={selectedScope}
              onChange={(e) => setSelectedScope(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Scopes</option>
              <option value="SCOPE_1">SCOPE_1</option>
              <option value="SCOPE_2">SCOPE_2</option>
              <option value="SCOPE_3">SCOPE_3</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Activity Type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">All Types</option>
              <option value="purchased_electricity">purchased_electricity</option>
              <option value="diesel">diesel</option>
              <option value="petrol">petrol</option>
              <option value="natural_gas">natural_gas</option>
              <option value="other">other</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Document ID</label>
            <input
              type="number"
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>
      </div>

      {/* Main Calculations Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Calculator className="w-4 h-4 text-emerald-600" />
            Calculation Records ({calculations.length})
          </h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-500" />
            Loading calculation records...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-red-600 text-sm">{error}</div>
        ) : calculations.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No carbon calculations found matching filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
                  <th className="px-4 py-3">Activity</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Group</th>
                  <th className="px-4 py-3 text-right">Quantity</th>
                  <th className="px-4 py-3">Factor Code</th>
                  <th className="px-4 py-3 text-right">Factor Value</th>
                  <th className="px-4 py-3 text-right">Calculated CO2e</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal text-slate-800">
                {calculations.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      <div className="flex flex-col">
                        <span>{item.activity_type}</span>
                        {item.scope && (
                          <span className="text-[10px] text-slate-400 font-normal">{item.scope}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">{getRoleBadge(item.activity_role)}</td>
                    <td className="px-4 py-3">
                      {item.activity_group_id ? (
                        <span className="inline-flex items-center gap-1 font-mono text-[11px] text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                          <Hash className="w-2.5 h-2.5 text-indigo-400" />
                          {item.activity_group_id}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">standalone</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      {item.quantity?.toLocaleString(undefined, { maximumFractionDigits: 2 })} {item.activity_unit}
                    </td>
                    <td className="px-4 py-3">
                      {item.factor_code ? (
                        <span className="font-mono text-[11px] text-slate-700">{item.factor_code}</span>
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700">
                      {item.factor_value !== null && item.factor_value !== undefined
                        ? `${item.factor_value} ${item.factor_unit || ''}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                      {item.calculated_co2e !== null && item.calculated_co2e !== undefined
                        ? `${item.calculated_co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })} kgCO2e`
                        : <span className="text-slate-400 font-normal italic">—</span>}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(item.status)}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setSelectedItem(item)}
                        className="text-xs text-emerald-600 hover:text-emerald-800 font-medium inline-flex items-center gap-0.5 px-2 py-1 rounded hover:bg-emerald-50 transition-colors"
                      >
                        Inspect <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail Drawer / Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-900">Calculation Provenance & Audit</h3>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-500 block">Activity</span>
                <span className="font-bold text-slate-900 text-sm">{selectedItem.activity_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Calculation Status</span>
                <div className="mt-1">{getStatusBadge(selectedItem.status)}</div>
              </div>
              <div>
                <span className="text-slate-500 block">Physical Quantity</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {selectedItem.quantity?.toLocaleString()} {selectedItem.activity_unit}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Calculated CO2e</span>
                <span className="font-mono font-bold text-emerald-700 text-sm">
                  {selectedItem.calculated_co2e !== null ? `${selectedItem.calculated_co2e?.toLocaleString()} ${selectedItem.calculated_co2e_unit}` : 'Not calculated'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Role & Group</span>
                <div className="flex items-center gap-1.5 mt-1">
                  {getRoleBadge(selectedItem.activity_role)}
                  <span className="font-mono text-[11px] text-slate-600">{selectedItem.activity_group_id || 'standalone'}</span>
                </div>
              </div>
              <div>
                <span className="text-slate-500 block">Scope</span>
                <span className="font-medium text-slate-800">{selectedItem.scope || 'Unspecified'}</span>
              </div>
            </div>

            {/* Formula block */}
            {selectedItem.formula && (
              <div>
                <span className="text-xs font-semibold text-slate-700 block mb-1">Deterministic Formula</span>
                <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-xs font-mono font-semibold text-emerald-950">
                  {selectedItem.formula}
                </div>
              </div>
            )}

            {/* Factor Snapshot */}
            {selectedItem.factor_code && (
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                <span className="font-semibold text-slate-800 block">Emission Factor Snapshot (Auditable at Calculation Time)</span>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600">
                  <div>Factor Code: <strong>{selectedItem.factor_code}</strong></div>
                  <div>Factor Value: <strong>{selectedItem.factor_value} {selectedItem.factor_unit}</strong></div>
                  <div>Version: <strong>v{selectedItem.factor_version || '1.0'}</strong></div>
                  <div>Source: <strong>{selectedItem.factor_source || 'Registry'}</strong></div>
                </div>
              </div>
            )}

            {/* Verbatim Source Evidence */}
            <div>
              <span className="text-xs font-semibold text-slate-700 block mb-1">Verbatim Source Evidence (Preserved Provenance)</span>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono text-slate-800 break-words whitespace-pre-wrap">
                {selectedItem.source_text || 'No verbatim source text recorded.'}
              </div>
            </div>

            {/* Calculation Reason */}
            {selectedItem.calculation_reason && (
              <div>
                <span className="text-xs font-semibold text-slate-700 block mb-1">Audit Trail & Reason</span>
                <div className="p-3 bg-slate-100 rounded-lg text-xs text-slate-700">
                  {selectedItem.calculation_reason}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-[11px] text-slate-500">
              <span>Engine Version: <strong>v{selectedItem.calculation_version}</strong></span>
              <button
                onClick={() => setSelectedItem(null)}
                className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
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
