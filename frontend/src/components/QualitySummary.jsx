import React, { useState } from 'react';
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';

export default function QualitySummary({ qualityScore, qualitySummary = {}, documentType }) {
  const [showBreakdown, setShowBreakdown] = useState(false);
  const score = qualityScore != null ? Math.round(qualityScore) : 0;
  const breakdown = qualitySummary.scoring_breakdown || {};
  const expectedMissingList = qualitySummary.expected_missing_list || qualitySummary.missing_fields || [];
  const notApplicableList = qualitySummary.not_applicable_list || [];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-900">Extraction Quality</h3>
        <span className={`text-base font-bold ${
          score >= 85 ? 'text-emerald-700' : score >= 70 ? 'text-amber-700' : 'text-rose-700'
        }`}>
          {score} <span className="text-xs font-normal text-slate-400">/ 100</span>
        </span>
      </div>

      <div className="pt-3 space-y-2 text-xs">
        <div className="flex items-center justify-between text-slate-600">
          <span>Expected fields</span>
          <span className="font-semibold text-slate-900">
            {qualitySummary.expected_fields_found ?? 4} / {qualitySummary.total_expected_fields ?? 4} found
          </span>
        </div>

        <div className="flex items-center justify-between text-slate-600">
          <span>Evidence backed</span>
          <span className="font-semibold text-slate-900">
            {qualitySummary.evidence_backed ?? 4} / {qualitySummary.expected_fields_found ?? 4}
          </span>
        </div>

        <div className="flex items-center justify-between text-slate-600">
          <span>High confidence</span>
          <span className="font-medium text-slate-800">
            {qualitySummary.high_confidence ?? 0}
          </span>
        </div>

        {qualitySummary.medium_confidence > 0 && (
          <div className="flex items-center justify-between text-slate-600">
            <span>Medium confidence</span>
            <span className="font-medium text-amber-700">
              {qualitySummary.medium_confidence}
            </span>
          </div>
        )}

        {qualitySummary.low_confidence > 0 && (
          <div className="flex items-center justify-between text-slate-600">
            <span>Low confidence</span>
            <span className="font-medium text-rose-700">
              {qualitySummary.low_confidence}
            </span>
          </div>
        )}

        <div className="flex items-center justify-between text-slate-600">
          <span>Needs review</span>
          <span className={`font-semibold ${(qualitySummary.expected_fields_missing || 0) > 0 ? 'text-amber-700' : 'text-slate-800'}`}>
            {qualitySummary.expected_fields_missing ?? 0}
          </span>
        </div>

        {qualitySummary.not_applicable_fields > 0 && (
          <div className="flex items-center justify-between text-slate-600">
            <span>Not applicable</span>
            <span className="text-slate-500 font-medium">
              {qualitySummary.not_applicable_fields} (0 penalty)
            </span>
          </div>
        )}
      </div>

      {/* Expandable Why This Score Breakdown */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <button
          onClick={() => setShowBreakdown(!showBreakdown)}
          className="text-xs text-teal-700 hover:text-teal-900 font-medium flex items-center gap-1 transition-colors"
        >
          <span>Why this score?</span>
          {showBreakdown ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showBreakdown && (
          <div className="mt-3 p-3 rounded-md bg-slate-50 border border-slate-200 text-xs space-y-1.5 text-slate-700 font-mono">
            <div className="flex justify-between">
              <span className="font-sans text-slate-600">Base score</span>
              <span className="font-semibold text-slate-900">+{breakdown.base_score || 100}</span>
            </div>

            {breakdown.ocr_penalty > 0 && (
              <div className="flex justify-between text-rose-700">
                <span className="font-sans">OCR fallback penalty</span>
                <span>-{breakdown.ocr_penalty}</span>
              </div>
            )}

            {breakdown.expected_missing_penalty > 0 && (
              <div className="flex justify-between text-amber-700">
                <span className="font-sans">Expected field missing</span>
                <span>-{breakdown.expected_missing_penalty}</span>
              </div>
            )}

            {breakdown.low_confidence_penalty > 0 && (
              <div className="flex justify-between text-rose-700">
                <span className="font-sans">Low confidence penalty</span>
                <span>-{breakdown.low_confidence_penalty}</span>
              </div>
            )}

            {breakdown.medium_confidence_penalty > 0 && (
              <div className="flex justify-between text-amber-700">
                <span className="font-sans">Medium confidence penalty</span>
                <span>-{breakdown.medium_confidence_penalty}</span>
              </div>
            )}

            {breakdown.evidence_penalty > 0 && (
              <div className="flex justify-between text-amber-700">
                <span className="font-sans">Unbacked evidence penalty</span>
                <span>-{breakdown.evidence_penalty}</span>
              </div>
            )}

            <div className="pt-2 border-t border-slate-200 flex justify-between font-bold text-slate-900">
              <span className="font-sans">Final Quality Score</span>
              <span>{score}</span>
            </div>

            {expectedMissingList.length > 0 && (
              <p className="text-[11px] font-sans text-amber-800 pt-1.5 border-t border-slate-200">
                <b>Missing expected:</b> {expectedMissingList.join(', ')}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
