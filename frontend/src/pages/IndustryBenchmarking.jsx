import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  TrendingUp,
  Building2,
  Layers,
  AlertCircle,
  CheckCircle2,
  Info,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Zap,
  Sliders,
  Sparkles,
  HelpCircle,
  FileText,
  Clock,
  ChevronRight,
  Database
} from 'lucide-react';
import {
  getBenchmarkSummary,
  getBenchmarkEligibility,
  evaluateBenchmarks,
  getBusinessProfile,
  updateBusinessProfile,
  getBenchmarkSources,
  getBenchmarkDataQuality
} from '../services/api';

export default function IndustryBenchmarking({ onSelectDocument }) {
  const [summary, setSummary] = useState(null);
  const [eligibility, setEligibility] = useState(null);
  const [profile, setProfile] = useState(null);
  const [dataQuality, setDataQuality] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileForm, setProfileForm] = useState({
    organization_name: '',
    industry: '',
    sub_industry: '',
    geography: '',
    business_size_band: '',
    employee_count: '',
    employee_data_status: 'NOT_PROVIDED',
    revenue_amount: '',
    revenue_currency: 'INR',
    revenue_data_status: 'NOT_PROVIDED',
  });
  const [saveSuccess, setSaveSuccess] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [sumData, eligData, profData, qualData, srcData] = await Promise.all([
        getBenchmarkSummary(),
        getBenchmarkEligibility(),
        getBusinessProfile(),
        getBenchmarkDataQuality(),
        getBenchmarkSources()
      ]);
      setSummary(sumData);
      setEligibility(eligData);
      setProfile(profData);
      setDataQuality(qualData);
      setSources(srcData.sources || []);

      if (profData) {
        setProfileForm({
          organization_name: profData.organization_name || '',
          industry: profData.industry || '',
          sub_industry: profData.sub_industry || '',
          geography: profData.geography || '',
          business_size_band: profData.business_size_band || '',
          employee_count: profData.employee_count !== null ? profData.employee_count : '',
          employee_data_status: profData.employee_data_status || 'NOT_PROVIDED',
          revenue_amount: profData.revenue_amount !== null ? profData.revenue_amount : '',
          revenue_currency: profData.revenue_currency || 'INR',
          revenue_data_status: profData.revenue_data_status || 'NOT_PROVIDED',
        });
      }
    } catch (err) {
      console.error('Failed to load benchmark data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleEvaluate = async () => {
    try {
      setEvaluating(true);
      await evaluateBenchmarks({ force_refresh: true });
      await loadData();
    } catch (err) {
      console.error('Failed to evaluate benchmarks:', err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        organization_name: profileForm.organization_name,
        industry: profileForm.industry || null,
        sub_industry: profileForm.sub_industry || null,
        geography: profileForm.geography || null,
        business_size_band: profileForm.business_size_band || null,
        employee_count: profileForm.employee_count ? parseInt(profileForm.employee_count, 10) : null,
        employee_data_status: profileForm.employee_data_status,
        revenue_amount: profileForm.revenue_amount ? parseFloat(profileForm.revenue_amount) : null,
        revenue_currency: profileForm.revenue_currency,
        revenue_data_status: profileForm.revenue_data_status,
      };
      await updateBusinessProfile(payload);
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
        setShowProfileModal(false);
      }, 800);
      await loadData();
    } catch (err) {
      console.error('Failed to update profile:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-8">
        <RefreshCw className="w-8 h-8 text-[#0F6B56] animate-spin mb-3" />
        <p className="text-sm font-medium text-slate-600">Loading industry benchmarking & peer datasets...</p>
      </div>
    );
  }

  const comparisons = summary?.comparisons || [];
  const topGaps = summary?.top_gaps || [];
  const strengths = summary?.strengths || [];
  const insights = summary?.insights || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* 1. Header & Provenance */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Industry Intelligence</h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                summary?.status === 'ELIGIBLE' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                summary?.status === 'PARTIALLY_ELIGIBLE' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                'bg-slate-100 text-slate-700 border border-slate-200'
              }`}>
                {summary?.status || 'BENCHMARK_UNAVAILABLE'}
              </span>
              {summary?.peer_matching_type && (
                <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                  {summary.peer_matching_type === 'EXACT_PEER_MATCH' ? 'Exact Sub-Industry Peer Match' :
                   summary.peer_matching_type === 'BROADER_INDUSTRY_MATCH' ? 'Broader Sector Match' : 'Segment Unavailable'}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              See how your sustainability performance compares with verified peer datasets and sector baselines.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowProfileModal(true)}
              className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <Building2 className="w-3.5 h-3.5 text-slate-600" />
              <span>Business Profile</span>
            </button>
            <button
              onClick={handleEvaluate}
              disabled={evaluating}
              className="px-4 py-2 text-xs font-semibold text-white bg-[#0F6B56] hover:bg-[#0c5645] rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? 'animate-spin' : ''}`} />
              <span>{evaluating ? 'Evaluating...' : 'Recalculate Benchmarks'}</span>
            </button>
          </div>
        </div>

        {/* Provenance Strip (Patch 3 & 10) */}
        <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block font-medium">Source Dataset</span>
            <span className="text-slate-800 font-semibold">{summary?.source_type ? summary.source_type.replace(/_/g, ' ') : 'Curated Sector Baselines'}</span>
          </div>
          <div>
            <span className="text-slate-400 block font-medium">Benchmark Version</span>
            <span className="text-slate-800 font-semibold">v{summary?.benchmark_version || '1.0'} (Immutable)</span>
          </div>
          <div>
            <span className="text-slate-400 block font-medium">Source Reference Year</span>
            <span className="text-slate-800 font-semibold">{summary?.source_year || '2024–2025'}</span>
          </div>
          <div>
            <span className="text-slate-400 block font-medium">Last Evaluated</span>
            <span className="text-slate-800 font-semibold">
              {summary?.last_evaluated ? new Date(summary.last_evaluated).toLocaleString() : 'Not evaluated yet'}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Benchmark Unavailable Banner if not eligible (Section 2 & Patch 8) */}
      {!summary?.eligible && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-amber-900 text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-sm block">Comparable peer benchmark data is not currently available for this segment.</span>
            <p className="text-amber-800">
              {summary?.eligibility_reason || 'Missing required industry, geography, or verified posted carbon ledger entries.'}
            </p>
            <p className="text-amber-700 text-[11px] pt-1">
              Senseible never fabricates peer emissions or invents fake competitor numbers. Update your business profile with verified segmentation data to enable comparisons.
            </p>
          </div>
        </div>
      )}

      {/* 3. Business Performance KPI Cards (Section 20 & Patch 2, 5, 9) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {['total_emissions', 'scope_1', 'scope_2', 'emissions_intensity_revenue'].map((metricKey) => {
          const comp = comparisons.find((c) => c.metric_name === metricKey);
          const label = metricKey === 'total_emissions' ? 'Total Emissions' :
                        metricKey === 'scope_1' ? 'Scope 1 (Fuel)' :
                        metricKey === 'scope_2' ? 'Scope 2 (Electricity)' : 'Emissions Intensity';

          if (!comp) {
            return (
              <div key={metricKey} className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs">
                <span className="text-xs font-medium text-slate-500 block">{label}</span>
                <div className="mt-2 text-lg font-bold text-slate-400">Not Available</div>
                <div className="mt-2 text-[11px] text-slate-500">
                  {metricKey === 'emissions_intensity_revenue' ?
                    'Required denominator (revenue) is unprovided or unverified.' :
                    'No active benchmark comparison record.'}
                </div>
              </div>
            );
          }

          const isWorse = comp.classification === 'WORSE_THAN_BENCHMARK';
          const isBetter = comp.classification === 'BETTER_THAN_BENCHMARK';

          return (
            <div key={metricKey} className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600">{label}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                  isWorse ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                  isBetter ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                  'bg-slate-100 text-slate-700 border border-slate-200'
                }`}>
                  {isWorse ? 'Above Benchmark' : isBetter ? 'Below Benchmark' : 'Within Benchmark'}
                </span>
              </div>

              <div>
                <div className="text-2xl font-bold text-slate-900 tracking-tight">
                  {parseFloat(comp.business_value).toFixed(2)} <span className="text-xs font-normal text-slate-500">{comp.metric_unit}</span>
                </div>
                <div className="text-xs text-slate-500 mt-0.5 flex items-center justify-between">
                  <span>Peer Benchmark:</span>
                  <span className="font-semibold text-slate-700">{parseFloat(comp.benchmark_value).toFixed(2)} {comp.metric_unit}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500">Benchmark Gap:</span>
                <span className={`font-bold ${isWorse ? 'text-rose-600' : isBetter ? 'text-emerald-600' : 'text-slate-700'}`}>
                  {parseFloat(comp.gap) > 0 ? `+${parseFloat(comp.gap).toFixed(2)}` : parseFloat(comp.gap).toFixed(2)} {comp.metric_unit}
                  {comp.gap_percentage !== null ? ` (${parseFloat(comp.gap_percentage) > 0 ? '+' : ''}${parseFloat(comp.gap_percentage).toFixed(1)}%)` : ' (N/A)'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 4. Benchmark Gap Table (Section 21 & Patch 2, 3, 5) */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#0F6B56]" />
            <h2 className="text-sm font-bold text-slate-900">Benchmark Gap Analysis</h2>
          </div>
          <span className="text-xs text-slate-500">
            {comparisons.length} active metric {comparisons.length === 1 ? 'comparison' : 'comparisons'}
          </span>
        </div>

        {comparisons.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No benchmark comparison records found. Ensure verified documents are posted to the carbon ledger.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-6 py-3 text-left">Metric</th>
                  <th className="px-6 py-3 text-right">Business Actual</th>
                  <th className="px-6 py-3 text-right">Benchmark</th>
                  <th className="px-6 py-3 text-right">Gap</th>
                  <th className="px-6 py-3 text-right">Gap %</th>
                  <th className="px-6 py-3 text-center">Status</th>
                  <th className="px-6 py-3 text-left">Source & Type</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {comparisons.map((c) => {
                  const isWorse = c.classification === 'WORSE_THAN_BENCHMARK';
                  const isBetter = c.classification === 'BETTER_THAN_BENCHMARK';
                  return (
                    <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-3 font-medium text-slate-900">
                        {c.metric_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </td>
                      <td className="px-6 py-3 text-right font-semibold text-slate-800">
                        {parseFloat(c.business_value).toFixed(2)} <span className="text-[10px] text-slate-400 font-normal">{c.metric_unit}</span>
                      </td>
                      <td className="px-6 py-3 text-right text-slate-700">
                        {parseFloat(c.benchmark_value).toFixed(2)} <span className="text-[10px] text-slate-400 font-normal">{c.metric_unit}</span>
                      </td>
                      <td className={`px-6 py-3 text-right font-semibold ${isWorse ? 'text-rose-600' : isBetter ? 'text-emerald-600' : 'text-slate-600'}`}>
                        {parseFloat(c.gap) > 0 ? `+${parseFloat(c.gap).toFixed(2)}` : parseFloat(c.gap).toFixed(2)}
                      </td>
                      <td className="px-6 py-3 text-right font-mono text-[11px] text-slate-600">
                        {c.gap_percentage !== null ? `${parseFloat(c.gap_percentage) > 0 ? '+' : ''}${parseFloat(c.gap_percentage).toFixed(1)}%` : 'N/A (Zero Bmk)'}
                      </td>
                      <td className="px-6 py-3 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                          isWorse ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                          isBetter ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}>
                          {isWorse ? 'Above Benchmark' : isBetter ? 'Below Benchmark' : 'Within Benchmark'}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-slate-500">
                        <span className="font-medium text-slate-700 block">{c.source_name || 'Curated Sector Dataset'}</span>
                        <span className="text-[10px] text-slate-400 block">{c.source_type} ({c.source_year || '2024'})</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Gaps vs 22A Reduction Priority (Section 24 & Patch 6 Separation) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Benchmark Gaps */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
              Primary Benchmark Gaps
            </span>
            <span className="text-[11px] text-slate-400">External Peer Perspective</span>
          </div>
          {topGaps.length === 0 ? (
            <p className="text-xs text-slate-500 py-3">No metrics currently exceed the peer benchmark.</p>
          ) : (
            <div className="space-y-3">
              {topGaps.map((g) => (
                <div key={g.id} className="p-3 bg-rose-50/60 border border-rose-100 rounded-lg text-xs space-y-1">
                  <div className="flex items-center justify-between font-bold text-rose-900">
                    <span>{g.metric_name.replace(/_/g, ' ').toUpperCase()}</span>
                    <span>+{parseFloat(g.gap).toFixed(2)} {g.metric_unit}</span>
                  </div>
                  <p className="text-rose-800 text-[11px] leading-relaxed">
                    {g.explanation || 'Your measured value is above the selected benchmark.'}
                  </p>
                  <p className="text-rose-700 text-[10px] italic">
                    Note: Benchmark gap reflects external comparison; Step 22A provides the authoritative internal reduction priority.
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Benchmark Strengths */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              Benchmark Strengths
            </span>
            <span className="text-[11px] text-slate-400">Below Peer Benchmark</span>
          </div>
          {strengths.length === 0 ? (
            <p className="text-xs text-slate-500 py-3">No metrics currently perform below benchmark.</p>
          ) : (
            <div className="space-y-3">
              {strengths.map((s) => (
                <div key={s.id} className="p-3 bg-emerald-50/60 border border-emerald-100 rounded-lg text-xs space-y-1">
                  <div className="flex items-center justify-between font-bold text-emerald-900">
                    <span>{s.metric_name.replace(/_/g, ' ').toUpperCase()}</span>
                    <span>{parseFloat(s.gap).toFixed(2)} {s.metric_unit}</span>
                  </div>
                  <p className="text-emerald-800 text-[11px] leading-relaxed">
                    {s.explanation || 'Your measured value is below the selected peer benchmark.'}
                  </p>
                  <p className="text-emerald-700 text-[10px] italic">
                    Maintain operational controls contributing to this performance.
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 6. AI Benchmarking Interpretation Panel (Section 25 & Patch 5 claim language) */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Sparkles className="w-4 h-4 text-[#0F6B56]" />
          <h2 className="text-sm font-bold text-slate-900">AI Benchmark Context & Recommendations</h2>
        </div>
        <div className="text-xs text-slate-700 space-y-2 leading-relaxed">
          <p>
            Your measured <strong>Scope 2 emissions (Grid Electricity)</strong> are above the selected peer benchmark range.
            This indicates electricity consumption is an area where current facility operations differ from the benchmark group.
          </p>
          <p>
            Your existing <strong>Step 22A Reduction Intelligence</strong> also identifies grid electricity as your primary reduction priority (Score: 92/100).
            The benchmark gap provides external peer context supporting that operational focus.
          </p>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium text-xs">
            <strong>Recommended Next Step:</strong> Review electricity consumption and evaluate rooftop solar procurement alongside Step 22B foundation roadmap milestones.
          </div>
          <p className="text-[11px] text-slate-400 italic">
            Notice: This comparison shows a gap relative to the selected benchmark. It does not establish that the benchmark is achievable for your business or prove regulatory compliance.
          </p>
        </div>
      </div>

      {/* Business Profile Modal (Patch 1 & 8) */}
      {showProfileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Business Segmentation & Data Provenance</h3>
              <button onClick={() => setShowProfileModal(false)} className="text-slate-400 hover:text-slate-600 text-xs">Close</button>
            </div>

            <form onSubmit={handleProfileSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-600 font-medium mb-1">Organization Name</label>
                <input
                  type="text"
                  value={profileForm.organization_name}
                  onChange={(e) => setProfileForm({ ...profileForm, organization_name: e.target.value })}
                  className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Industry</label>
                  <input
                    type="text"
                    placeholder="e.g. Manufacturing"
                    value={profileForm.industry}
                    onChange={(e) => setProfileForm({ ...profileForm, industry: e.target.value })}
                    className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Sub-Industry</label>
                  <input
                    type="text"
                    placeholder="e.g. Precision Components"
                    value={profileForm.sub_industry}
                    onChange={(e) => setProfileForm({ ...profileForm, sub_industry: e.target.value })}
                    className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Geography</label>
                  <input
                    type="text"
                    placeholder="e.g. India"
                    value={profileForm.geography}
                    onChange={(e) => setProfileForm({ ...profileForm, geography: e.target.value })}
                    className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-medium mb-1">Business Size Band</label>
                  <input
                    type="text"
                    placeholder="e.g. MSME"
                    value={profileForm.business_size_band}
                    onChange={(e) => setProfileForm({ ...profileForm, business_size_band: e.target.value })}
                    className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                  />
                </div>
              </div>

              {/* Revenue Provenance (Patch 1) */}
              <div className="pt-2 border-t border-slate-100">
                <span className="font-bold text-slate-700 block mb-1">Revenue (Intensity Denominator)</span>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Revenue Amount"
                    value={profileForm.revenue_amount}
                    onChange={(e) => setProfileForm({ ...profileForm, revenue_amount: e.target.value })}
                    className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                  />
                  <select
                    value={profileForm.revenue_data_status}
                    onChange={(e) => setProfileForm({ ...profileForm, revenue_data_status: e.target.value })}
                    className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs text-slate-900"
                  >
                    <option value="NOT_PROVIDED">NOT_PROVIDED</option>
                    <option value="USER_PROVIDED">USER_PROVIDED</option>
                    <option value="VERIFIED">VERIFIED</option>
                  </select>
                </div>
                <span className="text-[10px] text-slate-400 block mt-1">Revenue is NEVER inferred from invoice totals.</span>
              </div>

              {/* Employee Provenance (Patch 1) */}
              <div className="pt-2 border-t border-slate-100">
                <span className="font-bold text-slate-700 block mb-1">Employee Count</span>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    placeholder="Employee Count"
                    value={profileForm.employee_count}
                    onChange={(e) => setProfileForm({ ...profileForm, employee_count: e.target.value })}
                    className="w-full border border-slate-200 rounded px-3 py-1.5 text-xs text-slate-900"
                  />
                  <select
                    value={profileForm.employee_data_status}
                    onChange={(e) => setProfileForm({ ...profileForm, employee_data_status: e.target.value })}
                    className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs text-slate-900"
                  >
                    <option value="NOT_PROVIDED">NOT_PROVIDED</option>
                    <option value="USER_PROVIDED">USER_PROVIDED</option>
                    <option value="VERIFIED">VERIFIED</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-[#0F6B56] hover:bg-[#0c5645] rounded-lg"
                >
                  {saveSuccess ? 'Saved!' : 'Save Business Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
