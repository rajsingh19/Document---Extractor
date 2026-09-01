import React, { useState } from 'react';
import { 
  X, 
  Download, 
  Copy, 
  Check, 
  FileText, 
  Building, 
  Calendar, 
  Zap, 
  Flame, 
  Droplets, 
  Recycle, 
  ShieldCheck, 
  ListTree, 
  Code2, 
  AlignLeft, 
  Info,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export default function DocumentDetailModal({ document, onClose }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [copied, setCopied] = useState(false);

  if (!document) return null;

  const data = document.structured_data || {};
  const company = data.company || {};
  const period = data.period || {};
  const energy = data.energy || {};
  const emissions = data.carbon_emissions || {};
  const waterWaste = data.water_and_waste || {};
  const compliance = data.compliance || {};
  const lineItems = data.line_items || [];

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-5xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        
        {/* Modal Top Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white tracking-tight">
                  {document.original_filename}
                </h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {data.document_type || document.document_type || 'Sustainability Record'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {company.name || document.company_name || 'MSME Enterprise'} • Extracted via{' '}
                <span className="text-slate-300 font-medium">
                  {document.extraction_method === 'ocr_fallback' ? 'Tesseract OCR Fallback' : 'PyMuPDF Text Engine'}
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {document.structured_data && (
              <a
                href={`/api/documents/${document.id}/download-json`}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-400 hover:text-white border border-slate-700 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="px-6 border-b border-slate-800 bg-slate-900/50 flex space-x-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'overview'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ListTree className="w-4 h-4" />
            Sustainability KPIs & Metrics
          </button>

          <button
            onClick={() => setActiveTab('json')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'json'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code2 className="w-4 h-4" />
            Structured JSON
          </button>

          <button
            onClick={() => setActiveTab('raw_text')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'raw_text'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlignLeft className="w-4 h-4" />
            Raw Extracted Text
          </button>

          <button
            onClick={() => setActiveTab('metadata')}
            className={`py-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'metadata'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Info className="w-4 h-4" />
            Pipeline Audit
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              
              {/* Executive Summary */}
              {data.executive_summary && (
                <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-200 text-xs leading-relaxed">
                  <p className="font-semibold text-emerald-400 uppercase tracking-wider text-[10px] mb-1">
                    Executive Summary
                  </p>
                  <p>{data.executive_summary}</p>
                </div>
              )}

              {/* Company & Billing Period */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
                    <Building className="w-4 h-4 text-emerald-400" />
                    <span>Company & Facility Info</span>
                  </div>
                  <div className="text-xs space-y-1 text-slate-300">
                    <p><span className="text-slate-500">Name:</span> {company.name || document.company_name || '-'}</p>
                    <p><span className="text-slate-500">Reg / GSTIN:</span> {company.registration_id || '-'}</p>
                    <p><span className="text-slate-500">Address:</span> {company.address || '-'}</p>
                    <p><span className="text-slate-500">Sector:</span> {company.industry_sector || '-'}</p>
                  </div>
                </div>

                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-bold text-slate-300">
                    <Calendar className="w-4 h-4 text-emerald-400" />
                    <span>Period & Invoice Info</span>
                  </div>
                  <div className="text-xs space-y-1 text-slate-300">
                    <p><span className="text-slate-500">Billing Month:</span> {period.billing_month || document.reporting_period || '-'}</p>
                    <p><span className="text-slate-500">Start Date:</span> {period.start_date || '-'}</p>
                    <p><span className="text-slate-500">End Date:</span> {period.end_date || '-'}</p>
                    <p><span className="text-slate-500">Issue Date:</span> {period.issue_date || '-'}</p>
                  </div>
                </div>
              </div>

              {/* Energy & Carbon Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Energy Card */}
                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs font-bold text-amber-300">
                      <Zap className="w-4 h-4 text-amber-400" />
                      <span>Energy & Power Profile</span>
                    </div>
                    {energy.total_energy_cost_inr && (
                      <span className="text-xs font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                        INR {energy.total_energy_cost_inr.toLocaleString()}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      <p className="text-slate-500 text-[11px]">Electricity Consumption</p>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {energy.electricity_kwh != null ? `${energy.electricity_kwh.toLocaleString()} kWh` : '-'}
                      </p>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      <p className="text-slate-500 text-[11px]">Peak Demand</p>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {energy.peak_demand_kva_kw != null ? `${energy.peak_demand_kva_kw} kVA/kW` : '-'}
                      </p>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      <p className="text-slate-500 text-[11px]">Power Factor</p>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {energy.power_factor != null ? energy.power_factor : '-'}
                      </p>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      <p className="text-slate-500 text-[11px]">Renewable Solar</p>
                      <p className="text-sm font-bold text-emerald-400 mt-0.5">
                        {energy.renewable_energy_kwh != null ? `${energy.renewable_energy_kwh.toLocaleString()} kWh` : '-'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Carbon Footprint Card */}
                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center space-x-2 text-xs font-bold text-emerald-300">
                    <Flame className="w-4 h-4 text-emerald-400" />
                    <span>GHG Carbon Footprint</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      <p className="text-slate-500 text-[11px]">Scope 1 (Direct Fuel)</p>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {emissions.scope_1_direct_tco2e != null ? `${emissions.scope_1_direct_tco2e} tCO2e` : '-'}
                      </p>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                      <p className="text-slate-500 text-[11px]">Scope 2 (Grid Power)</p>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {emissions.scope_2_indirect_tco2e != null ? `${emissions.scope_2_indirect_tco2e} tCO2e` : '-'}
                      </p>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 col-span-2">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-slate-500 text-[11px]">Total GHG Operational Footprint</p>
                          <p className="text-base font-bold text-emerald-400 mt-0.5">
                            {emissions.total_ghg_emissions_tco2e != null ? `${emissions.total_ghg_emissions_tco2e} tCO2e` : '-'}
                          </p>
                        </div>
                        {emissions.emission_intensity_per_unit && (
                          <div className="text-right">
                            <p className="text-slate-500 text-[11px]">Intensity</p>
                            <p className="text-xs text-slate-300">{emissions.emission_intensity_per_unit}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Water, Waste & Compliance */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Water & Waste */}
                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-bold text-cyan-300">
                    <Droplets className="w-4 h-4 text-cyan-400" />
                    <span>Water & Circular Waste</span>
                  </div>
                  <div className="text-xs space-y-1.5 text-slate-300">
                    <p><span className="text-slate-500">Freshwater Withdrawal:</span> {waterWaste.water_consumption_kl != null ? `${waterWaste.water_consumption_kl.toLocaleString()} kL` : '-'}</p>
                    <p><span className="text-slate-500">Recycled / Treated Water:</span> {waterWaste.recycled_water_kl != null ? `${waterWaste.recycled_water_kl.toLocaleString()} kL` : '-'}</p>
                    <p><span className="text-slate-500">Non-Hazardous Waste:</span> {waterWaste.non_hazardous_waste_kg != null ? `${waterWaste.non_hazardous_waste_kg.toLocaleString()} kg` : '-'}</p>
                    <p><span className="text-slate-500">Hazardous Waste:</span> {waterWaste.hazardous_waste_kg != null ? `${waterWaste.hazardous_waste_kg.toLocaleString()} kg` : '-'}</p>
                    <p><span className="text-slate-500">Waste Recycled Rate:</span> {waterWaste.waste_recycled_percentage != null ? `${waterWaste.waste_recycled_percentage}%` : '-'}</p>
                  </div>
                </div>

                {/* Compliance & Certifications */}
                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-bold text-emerald-300">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Compliance & Certifications</span>
                  </div>
                  <div className="text-xs space-y-1.5 text-slate-300">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-slate-500">Certifications:</span>
                      {compliance.certifications_identified && compliance.certifications_identified.length > 0 ? (
                        compliance.certifications_identified.map((c, i) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800 text-[10px] font-semibold">
                            {c}
                          </span>
                        ))
                      ) : (
                        <span>Standard Industrial</span>
                      )}
                    </div>
                    <p><span className="text-slate-500">Audit Body / Standard:</span> {compliance.audit_standard || '-'}</p>
                    <p><span className="text-slate-500">Compliance Status:</span> <span className="text-emerald-400 font-semibold">{compliance.compliance_status || document.compliance_status || 'Compliant'}</span></p>
                    {compliance.findings_and_recommendations && compliance.findings_and_recommendations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-800">
                        <p className="text-slate-400 text-[11px] font-medium mb-1">Key Recommendations:</p>
                        <ul className="list-disc list-inside space-y-0.5 text-slate-400 text-[11px]">
                          {compliance.findings_and_recommendations.map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Line items table */}
              {lineItems.length > 0 && (
                <div className="glass-card p-4 rounded-xl border border-slate-800 space-y-3">
                  <p className="text-xs font-bold text-slate-300">Extracted Line Items & Tariffs</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 uppercase text-[10px] text-slate-400">
                        <tr>
                          <th className="p-2">Item Description</th>
                          <th className="p-2">Qty</th>
                          <th className="p-2">Unit</th>
                          <th className="p-2">Rate</th>
                          <th className="p-2 text-right">Total Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300">
                        {lineItems.map((item, i) => (
                          <tr key={i}>
                            <td className="p-2 font-medium">{item.item_description}</td>
                            <td className="p-2">{item.quantity != null ? item.quantity.toLocaleString() : '-'}</td>
                            <td className="p-2">{item.unit || '-'}</td>
                            <td className="p-2">{item.unit_rate != null ? item.unit_rate.toFixed(2) : '-'}</td>
                            <td className="p-2 text-right font-semibold text-emerald-400">
                              {item.total_amount != null ? item.total_amount.toLocaleString() : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* TAB 2: STRUCTURED JSON */}
          {activeTab === 'json' && (
            <div className="relative">
              <button
                onClick={handleCopyJson}
                className="absolute top-3 right-3 flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
              </button>
              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 font-mono text-xs overflow-x-auto leading-relaxed max-h-[550px]">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          )}

          {/* TAB 3: RAW EXTRACTED TEXT */}
          {activeTab === 'raw_text' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Original extracted document text via <b>{document.extraction_method}</b></span>
                <span>{document.extracted_text ? document.extracted_text.length : 0} characters</span>
              </div>
              <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-[550px] overflow-y-auto">
                {document.extracted_text || 'No text extracted.'}
              </pre>
            </div>
          )}

          {/* TAB 4: METADATA */}
          {activeTab === 'metadata' && (
            <div className="glass-card p-5 rounded-xl border border-slate-800 space-y-3 text-xs">
              <h4 className="font-bold text-white text-sm">System Pipeline Audit</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-300">
                <p><span className="text-slate-500">Document ID:</span> {document.id}</p>
                <p><span className="text-slate-500">Stored Filename:</span> {document.filename}</p>
                <p><span className="text-slate-500">Original Filename:</span> {document.original_filename}</p>
                <p><span className="text-slate-500">File Size:</span> {(document.file_size / 1024).toFixed(2)} KB ({document.file_size} bytes)</p>
                <p><span className="text-slate-500">Page Count:</span> {document.page_count} pages</p>
                <p><span className="text-slate-500">Extraction Method:</span> {document.extraction_method}</p>
                <p><span className="text-slate-500">Confidence Score:</span> {Math.round((document.confidence_score || 0.85) * 100)}%</p>
                <p><span className="text-slate-500">Created Timestamp:</span> {document.created_at || '-'}</p>
              </div>
              {document.error_message && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs">
                  <p className="font-bold">Error Message:</p>
                  <p>{document.error_message}</p>
                </div>
              )}
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
