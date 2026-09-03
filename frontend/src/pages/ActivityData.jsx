import React, { useState, useEffect } from 'react';
import {
  Activity,
  Filter,
  Layers,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  FileText,
  Sparkles,
  ArrowRight,
  Info,
  ShieldCheck,
  ChevronRight,
  X,
  RefreshCw,
  Hash,
  Database
} from 'lucide-react';
import { getActivityData, previewNormalizeActivity, calculateActivityCarbon } from '../services/api';

export default function ActivityDataPage() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [selectedType, setSelectedType] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedEligible, setSelectedEligible] = useState('');

  // Detail Modal / Drawer
  const [selectedItem, setSelectedItem] = useState(null);

  // Interactive Normalization Preview Test Bench
  const [testForm, setTestForm] = useState({
    activity_type: 'Electricity Consumption',
    quantity: '48,750 KWH',
    unit: 'kWh',
    geography: 'India',
    reporting_period: 'October 2024',
    activity_role: 'TOTAL',
  });
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState(null);

  const fetchActivities = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (selectedType) params.activity_type = selectedType;
      if (selectedCategory) params.category = selectedCategory;
      if (selectedRole) params.activity_role = selectedRole;
      if (selectedStatus) params.status = selectedStatus;
      if (selectedEligible !== '') params.calculation_eligible = selectedEligible === 'true';

      const data = await getActivityData(params);
      setActivities(data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load activity data records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, [selectedType, selectedCategory, selectedRole, selectedStatus, selectedEligible]);

  const handleTestPreview = async (e) => {
    if (e) e.preventDefault();
    setPreviewLoading(true);
    try {
      const res = await previewNormalizeActivity(testForm);
      setPreviewResult(res);
    } catch (err) {
      setPreviewResult({
        status: 'INVALID',
        reasons: [err.response?.data?.detail || 'Normalization preview request failed.'],
      });
    } finally {
      setPreviewLoading(false);
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

  const getEligibilityBadge = (eligible) => {
    if (eligible) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Eligible
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-50 text-slate-600 border border-slate-200">
        <XCircle className="w-3 h-3 text-slate-400" /> Not eligible
      </span>
    );
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'VALID':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800"><CheckCircle2 className="w-3 h-3" /> VALID</span>;
      case 'NEEDS_REVIEW':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800"><AlertTriangle className="w-3 h-3" /> REVIEW</span>;
      case 'INVALID':
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800"><XCircle className="w-3 h-3" /> INVALID</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-indigo-100 text-indigo-800 rounded-full border border-indigo-200">
              Step 12C Canonical Layer
            </span>
            <span className="px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 rounded-full">
              v1.0 Normalizer
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Layers className="w-6 h-6 text-indigo-600" />
            Canonical Activity Data
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Standardized physical activity quantities (kWh, L, scm, tonne_km) prepared for emission factor matching and Step 13 calculations.
          </p>
        </div>

        <button
          onClick={fetchActivities}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Notice Banner */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 text-xs text-indigo-950 flex items-start gap-3 shadow-xs">
        <Info className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-indigo-900 text-sm">Strict Deterministic Boundaries</p>
          <p>
            This layer stores <strong>physical activity quantities only</strong>. It never generates CO2e or alters existing Scope 1/2 calculations.
            Related records (e.g. Total Electricity 48,750 kWh, Grid 44,900 kWh, Solar 3,850 kWh) share an <strong>activity_group_id</strong> with explicit roles (TOTAL vs COMPONENT) to prevent double counting in Step 13.
            Operational metrics (peak demand, power factor) are labeled <strong>SUPPORTING</strong> and strictly marked non-eligible for carbon calculations.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" /> Filters
          </span>
          {(selectedType || selectedCategory || selectedRole || selectedStatus || selectedEligible !== '') && (
            <button
              onClick={() => {
                setSelectedType('');
                setSelectedCategory('');
                setSelectedRole('');
                setSelectedStatus('');
                setSelectedEligible('');
              }}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Activity Type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Activities</option>
              <option value="purchased_electricity">purchased_electricity</option>
              <option value="diesel">diesel</option>
              <option value="petrol">petrol</option>
              <option value="natural_gas">natural_gas</option>
              <option value="freight">freight</option>
              <option value="water">water</option>
              <option value="waste">waste</option>
              <option value="other">other</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Category</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
            <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Roles</option>
              <option value="TOTAL">TOTAL</option>
              <option value="COMPONENT">COMPONENT</option>
              <option value="SUPPORTING">SUPPORTING</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Calculation Eligible</label>
            <select
              value={selectedEligible}
              onChange={(e) => setSelectedEligible(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All</option>
              <option value="true">Eligible Only</option>
              <option value="false">Not Eligible (Supporting)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Statuses</option>
              <option value="VALID">VALID</option>
              <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
              <option value="INVALID">INVALID</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-600" />
            Canonical Activity Records ({activities.length})
          </h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
            Loading canonical activity records...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-red-600 text-sm">{error}</div>
        ) : activities.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No canonical activity data matching selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
                  <th className="px-4 py-3">Activity</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Eligible</th>
                  <th className="px-4 py-3">Activity Group</th>
                  <th className="px-4 py-3 text-right">Physical Quantity</th>
                  <th className="px-4 py-3">Unit</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Geography</th>
                  <th className="px-4 py-3">Period</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal text-slate-800">
                {activities.map((item) => (
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
                    <td className="px-4 py-3">{getEligibilityBadge(item.calculation_eligible)}</td>
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
                    <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                      {item.quantity?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{item.unit}</td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                        {item.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.geography || <span className="text-slate-400 italic">Not specified</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.reporting_period || (item.reporting_year ? `Year ${item.reporting_year}` : <span className="text-slate-400 italic">Unspecified</span>)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        {item.calculation_eligible ? (
                          <button
                            onClick={async () => {
                              try {
                                await calculateActivityCarbon(item.id, true);
                                alert(`Emissions calculated successfully for Activity #${item.id}! View in Carbon Calculations.`);
                              } catch (e) {
                                alert(e.response?.data?.detail || 'Failed to calculate emissions.');
                              }
                            }}
                            className="text-[11px] text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded font-medium transition-colors"
                            title="Calculate emissions with EmissionFactorResolver"
                          >
                            Calculate emissions
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-medium">
                            Not eligible for calculation
                          </span>
                        )}
                        <button
                          onClick={() => setSelectedItem(item)}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center gap-0.5 px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
                        >
                          Inspect <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Normalization Preview Test Bench */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-900">Interactive Normalization Preview Tester</h2>
          </div>
          <span className="text-xs text-slate-500 font-medium">Safe validation • Never persists to database</span>
        </div>

        <form onSubmit={handleTestPreview} className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-600 mb-1">Raw Activity / Name</label>
            <input
              type="text"
              value={testForm.activity_type}
              onChange={(e) => setTestForm({ ...testForm, activity_type: e.target.value })}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Diesel Fuel, Electricity"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Quantity String</label>
            <input
              type="text"
              value={testForm.quantity}
              onChange={(e) => setTestForm({ ...testForm, quantity: e.target.value })}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. 48,750"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Unit</label>
            <input
              type="text"
              value={testForm.unit}
              onChange={(e) => setTestForm({ ...testForm, unit: e.target.value })}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. kWh, L"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Geography</label>
            <input
              type="text"
              value={testForm.geography}
              onChange={(e) => setTestForm({ ...testForm, geography: e.target.value })}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. India (leave empty for None)"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={previewLoading}
              className="w-full text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded-lg transition-colors shadow-xs flex items-center justify-center gap-1"
            >
              {previewLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
              Preview Normalization
            </button>
          </div>
        </form>

        {previewResult && (
          <div className={`p-4 rounded-lg border text-xs space-y-2.5 ${
            previewResult.status === 'VALID'
              ? 'bg-emerald-50/50 border-emerald-200'
              : previewResult.status === 'NEEDS_REVIEW'
              ? 'bg-amber-50/50 border-amber-200'
              : 'bg-red-50/50 border-red-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-800">Preview Result:</span>
                {getStatusBadge(previewResult.status)}
                <span className="font-mono text-[11px] text-slate-500">v{previewResult.normalization_version}</span>
              </div>
              <div className="flex items-center gap-2">
                {getRoleBadge(previewResult.activity_role)}
                {getEligibilityBadge(previewResult.calculation_eligible)}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
              <div><span className="text-slate-500 font-sans">Activity:</span> <strong>{previewResult.activity_type || 'None'}</strong></div>
              <div><span className="text-slate-500 font-sans">Quantity:</span> <strong>{previewResult.quantity ?? 'None'} {previewResult.unit}</strong></div>
              <div><span className="text-slate-500 font-sans">Geography:</span> <strong>{previewResult.geography || 'None'}</strong></div>
              <div><span className="text-slate-500 font-sans">Group:</span> <strong>{previewResult.activity_group_id || 'None'}</strong></div>
            </div>

            {previewResult.reasons?.length > 0 && (
              <div className="pt-2 border-t border-slate-200/60">
                <span className="font-semibold text-slate-700">Audit & Decision Trail:</span>
                <ul className="list-disc list-inside mt-1 space-y-0.5 text-slate-600">
                  {previewResult.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Detail Drawer / Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Activity Provenance & Audit</h3>
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
                <span className="text-slate-500 block">Activity Type</span>
                <span className="font-bold text-slate-900 text-sm">{selectedItem.activity_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Physical Quantity</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {selectedItem.quantity?.toLocaleString()} {selectedItem.unit}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Activity Role</span>
                <div className="mt-1">{getRoleBadge(selectedItem.activity_role)}</div>
              </div>
              <div>
                <span className="text-slate-500 block">Calculation Eligible</span>
                <div className="mt-1">{getEligibilityBadge(selectedItem.calculation_eligible)}</div>
              </div>
              <div>
                <span className="text-slate-500 block">Activity Group ID</span>
                <span className="font-mono text-indigo-800 bg-indigo-50 px-2 py-0.5 rounded inline-block mt-0.5">
                  {selectedItem.activity_group_id || 'standalone'}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Geography</span>
                <span className="font-semibold text-slate-800">
                  {selectedItem.geography || <span className="text-slate-400 italic">Not specified (None)</span>}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Source Document</span>
                <span className="font-medium text-slate-800">Document #{selectedItem.document_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Source Field</span>
                <span className="font-mono text-slate-800">{selectedItem.source_field || 'N/A'}</span>
              </div>
            </div>

            {/* Verbatim Source Evidence */}
            <div>
              <span className="text-xs font-semibold text-slate-700 block mb-1">Verbatim Source Evidence (Preserved Lineage)</span>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono text-slate-800 break-words whitespace-pre-wrap">
                {selectedItem.source_text || 'No verbatim source text recorded.'}
              </div>
            </div>

            {/* Normalization Reasons */}
            {selectedItem.normalization_reasons && (
              <div>
                <span className="text-xs font-semibold text-slate-700 block mb-1">Normalization Decision</span>
                <div className="p-3 bg-indigo-50/60 rounded-lg border border-indigo-100 text-xs text-indigo-950">
                  {selectedItem.normalization_reasons}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-[11px] text-slate-500">
              <span>Normalization Version: <strong>v{selectedItem.normalization_version}</strong></span>
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
