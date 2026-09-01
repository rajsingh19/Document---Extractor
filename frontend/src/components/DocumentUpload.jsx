import React, { useState, useRef } from 'react';
import { UploadCloud, FileCheck2, Loader2, Sparkles, Zap, FileSpreadsheet, ScanText, AlertCircle } from 'lucide-react';
import { uploadDocument, seedSampleDocument } from '../services/api';

export default function DocumentUpload({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStage, setProcessingStage] = useState('');
  const [forceOcr, setForceOcr] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a valid PDF document (.pdf).');
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadProgress(10);
    setProcessingStage('Uploading document to server...');

    try {
      setProcessingStage('Extracting text & running LLM structured extraction...');
      const result = await uploadDocument(file, true, forceOcr, (progress) => {
        setUploadProgress(Math.min(progress, 80));
      });

      setUploadProgress(100);
      setProcessingStage('Extraction completed successfully!');
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setProcessingStage('');
        if (onUploadSuccess) onUploadSuccess(result);
      }, 700);

    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Failed to extract document. Please check the backend connection.');
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSeedSample = async (sampleType) => {
    setError(null);
    setIsUploading(true);
    setUploadProgress(40);
    const label = sampleType === 'electricity' 
      ? 'Generating Industrial Electricity Bill...' 
      : sampleType === 'esg' 
      ? 'Generating MSME ESG Audit Report...' 
      : 'Generating Scanned Low-Quality Receipt (Testing OCR Fallback)...';
    
    setProcessingStage(label);

    try {
      const result = await seedSampleDocument(sampleType);
      setUploadProgress(100);
      setProcessingStage('Sample document processed!');
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setProcessingStage('');
        if (onUploadSuccess) onUploadSuccess(result);
      }, 600);
    } catch (err) {
      console.error('Sample generation error:', err);
      setError(err.response?.data?.detail || 'Failed to generate sample document.');
      setIsUploading(false);
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl mb-8">
      <div className="flex flex-col lg:flex-row gap-6 items-stretch">
        
        {/* Drag & Drop Box */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-emerald-400 bg-emerald-950/20'
              : 'border-slate-700 hover:border-slate-500 bg-slate-900/40 hover:bg-slate-900/70'
          } ${isUploading ? 'pointer-events-none opacity-80' : ''}`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFileSelect(e.target.files?.[0])}
            accept=".pdf,application/pdf"
            className="hidden"
          />

          {isUploading ? (
            <div className="flex flex-col items-center space-y-3 py-2">
              <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-white">{processingStage}</p>
                <div className="w-56 h-2 bg-slate-800 rounded-full overflow-hidden mx-auto">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-2.5">
              <div className="p-3.5 rounded-full bg-slate-800/80 border border-slate-700 text-emerald-400 shadow-inner">
                <UploadCloud className="w-7 h-7" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-200">
                  <span className="text-emerald-400 font-bold hover:underline">Click to upload</span> or drag and drop MSME PDF
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Electricity Bills, Energy Audits, Water/Waste Logs, or ESG Compliance Documents (.pdf)
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Action Panel & Sample Buttons */}
        <div className="lg:w-80 flex flex-col justify-between space-y-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800/80">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                Quick Test Samples
              </span>
              
              {/* Force OCR Toggle */}
              <label className="flex items-center space-x-1.5 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
                <input
                  type="checkbox"
                  checked={forceOcr}
                  onChange={(e) => setForceOcr(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5"
                />
                <span>Force OCR</span>
              </label>
            </div>
            <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">
              Don't have a document handy? Click a sample below to generate and test instant extraction:
            </p>

            <div className="space-y-2">
              <button
                onClick={() => handleSeedSample('electricity')}
                disabled={isUploading}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 hover:border-amber-500/40 transition-all text-xs font-medium text-slate-200 disabled:opacity-50"
              >
                <span className="flex items-center gap-2">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Industrial Electricity Bill
                </span>
                <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">PyMuPDF</span>
              </button>

              <button
                onClick={() => handleSeedSample('esg')}
                disabled={isUploading}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 hover:border-emerald-500/40 transition-all text-xs font-medium text-slate-200 disabled:opacity-50"
              >
                <span className="flex items-center gap-2">
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                  MSME ESG Audit Report
                </span>
                <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">PyMuPDF</span>
              </button>

              <button
                onClick={() => handleSeedSample('scanned')}
                disabled={isUploading}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-left border border-slate-700 hover:border-blue-500/40 transition-all text-xs font-medium text-slate-200 disabled:opacity-50"
              >
                <span className="flex items-center gap-2">
                  <ScanText className="w-3.5 h-3.5 text-blue-400" />
                  Scanned Waste Manifest
                </span>
                <span className="text-[10px] text-blue-400 bg-blue-950/60 px-1.5 py-0.5 rounded border border-blue-800/40">OCR Fallback</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-start space-x-2 p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
