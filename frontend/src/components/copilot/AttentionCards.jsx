import React from 'react';
import { AlertCircle, AlertTriangle, Info, ArrowRight, CheckCircle2, FileText, BarChart2, Sparkles, Upload } from 'lucide-react';

export default function AttentionCards({
  attentionData,
  isLoading = false,
  error = null,
  onSelectAction,
  onSelectSource,
  onUploadClick
}) {
  if (isLoading) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-3">
        <div className="h-4 bg-slate-200 rounded w-1/3 animate-pulse" />
        <div className="h-16 bg-slate-100 rounded animate-pulse" />
        <div className="h-16 bg-slate-100 rounded animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-xs text-rose-700 flex items-center justify-between shadow-2xs">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>Unable to load proactive attention items.</span>
        </div>
      </div>
    );
  }

  const items = attentionData?.items || [];
  const summary = attentionData?.summary || { total: 0, high: 0, medium: 0, low: 0 };

  if (items.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 text-center shadow-2xs space-y-3">
        <div className="w-10 h-10 rounded-full bg-emerald-50 text-[#0f6b56] border border-emerald-200 flex items-center justify-center mx-auto shadow-2xs">
          <CheckCircle2 className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-slate-900">Nothing currently requires your attention</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            All extracted sustainability metrics are verified and reporting periods are up to date.
          </p>
        </div>
        {onUploadClick && (
          <div className="pt-2">
            <button
              onClick={onUploadClick}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-[#0f6b56] hover:bg-teal-800 text-white rounded-md text-xs font-medium shadow-2xs transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Document</span>
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-5 shadow-2xs space-y-4">
      {/* Header Banner */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-[#0f6b56]" />
          <h3 className="text-xs font-bold text-slate-900 tracking-tight">
            Here's what needs your attention
          </h3>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
            {summary.total} item{summary.total > 1 ? 's' : ''}
          </span>
        </div>

        <div className="hidden sm:flex items-center space-x-2 text-[11px] text-slate-500">
          {summary.high > 0 && (
            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200 font-semibold text-[10px]">
              {summary.high} High
            </span>
          )}
          {summary.medium > 0 && (
            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-semibold text-[10px]">
              {summary.medium} Medium
            </span>
          )}
        </div>
      </div>

      {/* Cards List */}
      <div className="space-y-3">
        {items.map((item) => {
          const isHigh = item.severity === 'HIGH';
          const isMedium = item.severity === 'MEDIUM';

          const cardBorder = isHigh
            ? 'border-rose-200 bg-rose-50/20'
            : isMedium
            ? 'border-amber-200 bg-amber-50/20'
            : 'border-slate-200 bg-slate-50/40';

          const badgeClass = isHigh
            ? 'bg-rose-100 text-rose-800 border-rose-300'
            : isMedium
            ? 'bg-amber-100 text-amber-800 border-amber-300'
            : 'bg-slate-100 text-slate-700 border-slate-300';

          return (
            <div
              key={item.id}
              className={`border rounded-lg p-3.5 text-xs transition-all ${cardBorder} shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3`}
            >
              {/* Left Column: Details */}
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border uppercase tracking-wider leading-none ${badgeClass}`}>
                    {item.severity}
                  </span>
                  <span className="font-bold text-slate-900 text-xs">
                    {item.title}
                  </span>
                  {item.percentage_change !== null && item.percentage_change !== undefined && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${item.percentage_change > 0 ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {item.percentage_change > 0 ? `+${item.percentage_change}%` : `${item.percentage_change}%`}
                    </span>
                  )}
                </div>

                <p className="text-slate-600 text-[11px] leading-relaxed">
                  {item.message}
                </p>

                {item.reason && (
                  <div className="text-[10px] text-slate-500 flex items-center space-x-1 pt-0.5">
                    <span className="font-semibold text-slate-700">Reason:</span>
                    <span>{item.reason}</span>
                  </div>
                )}

                {/* Previous vs Current Value preview if present */}
                {item.current_value !== null && item.previous_value !== null && (
                  <div className="text-[10px] text-slate-500 flex items-center space-x-3 pt-0.5">
                    <span>Previous: <strong className="text-slate-800">{item.previous_value} {item.unit || ''}</strong></span>
                    <span>&rarr;</span>
                    <span>Current: <strong className="text-slate-800">{item.current_value} {item.unit || ''}</strong></span>
                  </div>
                )}
              </div>

              {/* Right Column: Action Button */}
              <div className="shrink-0 flex items-center self-end sm:self-center">
                <button
                  onClick={() => {
                    if (onSelectAction) {
                      onSelectAction({
                        type: item.action_type,
                        label: item.action_label,
                        target: item.action_target
                      });
                    }
                  }}
                  className={`inline-flex items-center space-x-1 px-3 py-1.5 rounded-md text-[11px] font-semibold border transition-all cursor-pointer shadow-2xs ${
                    isHigh
                      ? 'bg-rose-600 hover:bg-rose-700 text-white border-rose-600'
                      : isMedium
                      ? 'bg-white hover:bg-amber-50 text-amber-900 border-amber-300'
                      : 'bg-white hover:bg-slate-100 text-slate-800 border-slate-300'
                  }`}
                >
                  <span>{item.action_label || 'Review'}</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
