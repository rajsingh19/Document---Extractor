import React from 'react';
import { Check, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react';

export default function QualitySummary({ qualityScore, qualitySummary = {}, documentType }) {
  const score = qualityScore != null ? Math.round(qualityScore) : 0;
  const breakdown = qualitySummary.scoring_breakdown || {};
  const expectedMissingList = qualitySummary.expected_missing_list || qualitySummary.missing_fields || [];
  const reviewReasons = qualitySummary.review_reasons || [];
  const expectedFound = qualitySummary.expected_fields_found ?? 0;
  const totalExpected = qualitySummary.total_expected_fields ?? 0;
  const isOCR = breakdown.ocr_penalty > 0;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-4">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Extraction Quality</h3>
          <p className="text-[11px] text-slate-400">Deterministic scoring</p>
        </div>
        <div className="text-right">
          <span className="text-lg font-bold text-slate-900">{score}</span>
          <span className="text-xs text-slate-400 font-normal ml-1">/ 100</span>
        </div>
      </div>

      {/* Why This Score Section */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-slate-700">Why this score?</h4>
        
        <ul className="space-y-1.5 text-xs text-slate-700">
          
          {/* 1. Required fields check */}
          {expectedMissingList.length === 0 ? (
            <li className="flex items-center space-x-2 text-emerald-800">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Required fields extracted ({expectedFound}/{totalExpected || expectedFound})</span>
            </li>
          ) : (
            <li className="flex items-center space-x-2 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>
                Missing {expectedMissingList.length} expected field{expectedMissingList.length > 1 ? 's' : ''} ({expectedMissingList.join(', ')})
              </span>
            </li>
          )}

          {/* 2. Evidence anchor check */}
          {breakdown.evidence_penalty === 0 ? (
            <li className="flex items-center space-x-2 text-emerald-800">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Evidence found for extracted values</span>
            </li>
          ) : (
            <li className="flex items-center space-x-2 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>Some fields missing verbatim source text evidence</span>
            </li>
          )}

          {/* 3. Validation and consistency */}
          {reviewReasons.length === 0 ? (
            <li className="flex items-center space-x-2 text-emerald-800">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Values passed validation</span>
            </li>
          ) : (
            <li className="flex items-center space-x-2 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>{reviewReasons[0]}</span>
            </li>
          )}

          {/* 4. OCR check */}
          {isOCR && (
            <li className="flex items-center space-x-2 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>OCR fallback used (scanned document)</span>
            </li>
          )}

          {/* 5. Low/Medium confidence flag */}
          {qualitySummary.low_confidence > 0 && (
            <li className="flex items-center space-x-2 text-rose-800">
              <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>{qualitySummary.low_confidence} field(s) require review (low confidence)</span>
            </li>
          )}

        </ul>
      </div>

    </div>
  );
}
