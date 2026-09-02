import React, { useState, useEffect, useCallback } from 'react';
import { 
  Database, 
  Search, 
  Filter, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  Calendar, 
  Globe, 
  Info,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { getEmissionFactors, resolveEmissionFactor } from '../services/api';

export default function EmissionFactors() {
  const [factors, setFactors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [activityFilter, setActivityFilter] = useState('');
  const [scopeFilter, setScopeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');

  // Interactive Match Tester (Step 12B Resolver)
  const [testActivity, setTestActivity] = useState('purchased_electricity');
  const [testUnit, setTestUnit] = useState('kWh');
  const [testGeography, setTestGeography] = useState('India');
  const [testYear, setTestYear] = useState('2024');
  const [testScope, setTestScope] = useState('SCOPE_2');
  const [testPreferredCode, setTestPreferredCode] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testingMatch, setTestingMatch] = useState(false);
  const [showRejected, setShowRejected] = useState(false);

  const fetchFactors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (activityFilter) params.activity_type = activityFilter;
      if (scopeFilter) params.scope = scopeFilter;
      if (statusFilter) params.status = statusFilter;
      if (yearFilter) params.year = parseInt(yearFilter, 10);

      const res = await getEmissionFactors(params);
      setFactors(res.factors || []);
    } catch (err) {
      console.error('Failed to fetch emission factors:', err);
      setError('Unable to load emission factors from the registry.');
    } finally {
      setLoading(false);
    }
  }, [activityFilter, scopeFilter, statusFilter, yearFilter]);

  useEffect(() => {
    fetchFactors();
  }, [fetchFactors]);

  const handleTestMatch = async (e) => {
    e.preventDefault();
    setTestingMatch(true);
    setTestResult(null);
    setShowRejected(false);
    try {
      const payload = {
        activity_type: testActivity,
        activity_unit: testUnit,
        geography: testGeography.trim() || undefined,
        year: testYear ? parseInt(testYear, 10) : undefined,
        scope: testScope.trim() || undefined,
        preferred_factor_code: testPreferredCode.trim() || undefined,
      };
      const result = await resolveEmissionFactor(payload);
      setTestResult(result);
    } catch (err) {
      setTestResult({
        status: 'INVALID_REQUEST',
        message: err.response?.data?.detail || 'Factor resolution request failed.',
        resolution_version: '1.0',
      });
    } finally {
      setTestingMatch(false);
    }
  };

  const filteredFactors = factors.filter((f) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (f.factor_code && f.factor_code.toLowerCase().includes(q)) ||
      (f.factor_name && f.factor_name.toLowerCase().includes(q)) ||
      (f.activity_type && f.activity_type.toLowerCase().includes(q)) ||
      (f.source_name && f.source_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="w-full max-w-7xl mx-auto py-6 px-4 sm:px-6 space-y-6">
      
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 mb-2">
              <Database className="w-3 h-3" />
              <span>Deterministic Factor Registry &bull; Step 12B</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              Emission Factor Registry &amp; Resolver
            </h1>
            <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
              Deterministic, auditable emission factor database and resolution engine for activity data carbon calculations 
              (Activity &times; Factor = CO<sub>2</sub>e). Factors are strictly non-AI reference data with immutable provenance.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-right">
              <span className="text-[10px] uppercase font-bold text-amber-800 block">Registry Status</span>
              <span className="text-xs font-semibold text-amber-900">Demo Foundation Mode</span>
            </div>
            <button
              onClick={fetchFactors}
              disabled={loading}
              className="p-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-slate-600 transition-colors shadow-2xs"
              title="Refresh Registry"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Resolver Test Bench */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 shadow-2xs">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-emerald-700" />
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Emission Factor Resolver (Step 12B Engine)
            </h2>
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-200 text-slate-700">
            Algorithm v1.0
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Test the deterministic resolution policy and unit compatibility without executing carbon calculations.
        </p>

        <form onSubmit={handleTestMatch} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Activity Type</label>
            <select
              value={testActivity}
              onChange={(e) => setTestActivity(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-medium focus:outline-emerald-600"
            >
              <option value="purchased_electricity">purchased_electricity</option>
              <option value="diesel">diesel</option>
              <option value="petrol">petrol</option>
              <option value="natural_gas">natural_gas</option>
              <option value="freight">freight</option>
              <option value="water">water</option>
              <option value="waste">waste</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Activity Unit</label>
            <input
              type="text"
              value={testUnit}
              onChange={(e) => setTestUnit(e.target.value)}
              placeholder="e.g. kWh, L, scm"
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-medium focus:outline-emerald-600"
              required
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Geography</label>
            <input
              type="text"
              value={testGeography}
              onChange={(e) => setTestGeography(e.target.value)}
              placeholder="e.g. India, Global"
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-medium focus:outline-emerald-600"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Applicable Year</label>
            <input
              type="number"
              value={testYear}
              onChange={(e) => setTestYear(e.target.value)}
              placeholder="e.g. 2024, 2025"
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-medium focus:outline-emerald-600"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-600 mb-1">Scope</label>
            <select
              value={testScope}
              onChange={(e) => setTestScope(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-medium focus:outline-emerald-600"
            >
              <option value="">Any Scope</option>
              <option value="SCOPE_1">SCOPE_1</option>
              <option value="SCOPE_2">SCOPE_2</option>
              <option value="SCOPE_3">SCOPE_3</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={testingMatch}
              className="w-full py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center space-x-1 shadow-2xs"
            >
              <span>{testingMatch ? 'Resolving...' : 'Resolve Factor'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>

        {testResult && (
          <div className={`mt-4 p-4 rounded-lg border text-xs ${
            testResult.status === 'MATCHED'
              ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
              : testResult.status === 'MULTIPLE_MATCHES'
              ? 'bg-blue-50/80 border-blue-200 text-blue-900'
              : testResult.status === 'INVALID_REQUEST'
              ? 'bg-red-50/80 border-red-200 text-red-900'
              : 'bg-amber-50/80 border-amber-200 text-amber-900'
          }`}>
            <div className="flex items-center justify-between font-bold mb-2">
              <span className="flex items-center gap-1.5 text-sm">
                {testResult.status === 'MATCHED' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                )}
                Resolution Status: {testResult.status}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono bg-white/70 px-2 py-0.5 rounded border border-current">
                  Resolver v{testResult.resolution_version || '1.0'}
                </span>
                <span className="text-[11px] font-mono">
                  {testResult.candidates?.length || (testResult.selected_factor ? 1 : 0)} valid candidate(s)
                </span>
              </div>
            </div>

            <p className="mt-1 font-medium">{testResult.message}</p>

            {/* MATCHED Details */}
            {testResult.selected_factor && (
              <div className="mt-3 p-3 bg-white border border-emerald-200 rounded-lg space-y-2">
                <div className="font-mono text-xs font-bold text-slate-900 flex items-center justify-between">
                  <span>Selected: {testResult.selected_factor.factor_code}</span>
                  <span className="text-emerald-700 text-sm">
                    {testResult.selected_factor.factor_value} {testResult.selected_factor.factor_unit}
                  </span>
                </div>
                <div className="text-[11px] text-slate-600 grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-slate-100">
                  <div>Scope: <strong className="text-slate-800">{testResult.selected_factor.scope}</strong></div>
                  <div>Geography: <strong className="text-slate-800">{testResult.selected_factor.geography}</strong></div>
                  <div>Year: <strong className="text-slate-800">{testResult.selected_factor.applicable_year || 'N/A'}</strong></div>
                  <div>Source: <strong className="text-slate-800">{testResult.selected_factor.source_name}</strong></div>
                </div>

                {testResult.resolution_reasons?.length > 0 && (
                  <div className="pt-2 border-t border-slate-100">
                    <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Resolution Reasons:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-700">
                      {testResult.resolution_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* MULTIPLE_MATCHES Candidates List */}
            {testResult.status === 'MULTIPLE_MATCHES' && testResult.candidates?.length > 0 && (
              <div className="mt-3 space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider block">Valid Candidate Factors (Manual Disambiguation Required):</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {testResult.candidates.map((c) => (
                    <div key={c.factor_id} className="p-2.5 bg-white border border-blue-200 rounded-lg text-[11px] space-y-1">
                      <div className="font-mono font-bold text-slate-900">{c.factor_code}</div>
                      <div className="text-slate-600">{c.factor_value} {c.factor_unit} &bull; Year: {c.applicable_year || 'N/A'} &bull; {c.scope}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Rejected Candidates Toggle (Explainability) */}
            {testResult.rejected_candidates?.length > 0 && (
              <div className="mt-3 pt-2 border-t border-current/20">
                <button
                  type="button"
                  onClick={() => setShowRejected(!showRejected)}
                  className="flex items-center gap-1 text-[11px] font-semibold underline hover:opacity-80 transition-opacity"
                >
                  <span>{showRejected ? 'Hide' : 'View'} Evaluated Non-Selected Factors ({testResult.rejected_candidates.length})</span>
                  {showRejected ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showRejected && (
                  <div className="mt-2 space-y-2">
                    {testResult.rejected_candidates.map((rc) => (
                      <div key={rc.factor_id} className="p-2 bg-white/90 border border-slate-200 rounded text-[11px] text-slate-700">
                        <div className="font-mono font-semibold text-slate-900">{rc.factor_code}</div>
                        <ul className="list-disc list-inside text-red-700 text-[10px] mt-0.5">
                          {rc.rejection_reasons.map((rj, idx) => (
                            <li key={idx}>{rj}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search code, name, source..."
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-emerald-600"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={activityFilter}
              onChange={(e) => setActivityFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-medium focus:outline-emerald-600"
            >
              <option value="">All Activities</option>
              <option value="purchased_electricity">Purchased Electricity</option>
              <option value="diesel">Diesel</option>
              <option value="petrol">Petrol</option>
              <option value="natural_gas">Natural Gas</option>
              <option value="freight">Freight</option>
            </select>

            <select
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-medium focus:outline-emerald-600"
            >
              <option value="">All Scopes</option>
              <option value="SCOPE_1">Scope 1</option>
              <option value="SCOPE_2">Scope 2</option>
              <option value="SCOPE_3">Scope 3</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-medium focus:outline-emerald-600"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="DRAFT">Draft</option>
            </select>

            <select
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-medium focus:outline-emerald-600"
            >
              <option value="">All Years</option>
              <option value="2024">2024</option>
              <option value="2025">2025</option>
              <option value="2020">2020</option>
            </select>
          </div>
        </div>
      </div>

      {/* Factor Registry Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-600" />
            Loading emission factors...
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600 text-xs">
            {error}
          </div>
        ) : filteredFactors.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs italic">
            No emission factors found matching the selected criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Factor Code &amp; Name</th>
                  <th className="py-2.5 px-3">Activity</th>
                  <th className="py-2.5 px-3">Scope</th>
                  <th className="py-2.5 px-3 text-right">Factor Value</th>
                  <th className="py-2.5 px-3">Factor Unit</th>
                  <th className="py-2.5 px-3">Geography</th>
                  <th className="py-2.5 px-3">Year</th>
                  <th className="py-2.5 px-3">Ver</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Provenance Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredFactors.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-bold font-mono text-[11px] text-slate-900">{f.factor_code}</div>
                      <div className="text-[11px] text-slate-500 truncate max-w-xs">{f.factor_name}</div>
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-700 capitalize">
                      {f.activity_type.replace('_', ' ')}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        f.scope === 'SCOPE_1'
                          ? 'bg-amber-100 text-amber-800'
                          : f.scope === 'SCOPE_2'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {f.scope.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                      {f.factor_value}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-500 font-mono text-[11px]">
                      {f.factor_unit}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">
                      {f.geography}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">
                      {f.applicable_year || '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      v{f.version}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                        f.status === 'ACTIVE'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : f.status === 'DRAFT'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-500 border border-slate-200'
                      }`}>
                        {f.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-slate-500 max-w-xs">
                      <div className="font-semibold text-slate-700 truncate">{f.source_name}</div>
                      {f.source_reference && (
                        <div className="text-slate-400 truncate">{f.source_reference}</div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Informational Footer */}
      <div className="text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200">
        <span>Senseible Carbon Intelligence &bull; Emission Factor Registry Engine (Step 12A)</span>
        <span>All demo factors strictly marked: DEMO DATA — NOT FOR PRODUCTION</span>
      </div>

    </div>
  );
}
