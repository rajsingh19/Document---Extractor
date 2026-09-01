import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-react';
import { uploadDocument } from '../services/api';

export default function UploadDocument({ onUploadSuccess, onCancel }) {
  const [file, setFile] = useState(null);
  const [forceOcr, setForceOcr] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processStep, setProcessStep] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  const steps = [
    'Reading document',
    'Identifying document type',
    'Extracting information',
    'Validating extracted values',
    'Preparing sustainability metrics'
  ];

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
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    setErrorMessage(null);
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Please upload a PDF file.');
      return;
    }
    if (selectedFile.size > 25 * 1024 * 1024) {
      setErrorMessage('File is too large (maximum 25 MB).');
      return;
    }
    if (selectedFile.size === 0) {
      setErrorMessage('The selected file is empty.');
      return;
    }
    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsProcessing(true);
    setErrorMessage(null);
    setProcessStep(0);

    // Step simulation for realistic progress feedback
    const stepInterval = setInterval(() => {
      setProcessStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 750);

    try {
      const result = await uploadDocument(file, true, forceOcr);
      clearInterval(stepInterval);
      setProcessStep(4);
      setTimeout(() => {
        setIsProcessing(false);
        setFile(null);
        if (onUploadSuccess) onUploadSuccess(result);
      }, 400);
    } catch (err) {
      clearInterval(stepInterval);
      setIsProcessing(false);
      console.error('Upload error:', err);
      const detail = err.response?.data?.detail || err.message || 'Unable to process this document. Please try again.';
      setErrorMessage(detail);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 mb-5 shadow-xs">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 mb-3.5 border-b border-slate-100">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Upload Document</h3>
          <p className="text-xs text-slate-500 mt-0.5">Extract and verify sustainability metrics from your PDF bills and manifests.</p>
        </div>
        {onCancel && (
          <button
            onClick={onCancel}
            disabled={isProcessing}
            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Error Message Alert */}
      {errorMessage && (
        <div className="mb-4 p-3 rounded bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Progress / Step Indicator State */}
      {isProcessing ? (
        <div className="py-6 text-center space-y-4">
          <Loader2 className="w-6 h-6 text-[#0f6b56] animate-spin mx-auto" />
          <div>
            <h4 className="text-sm font-medium text-slate-900">Processing document</h4>
            <p className="text-xs text-slate-500 mt-0.5">{file?.name}</p>
          </div>

          <div className="max-w-xs mx-auto space-y-2 text-left pt-2">
            {steps.map((step, idx) => {
              const isDone = processStep > idx;
              const isCurrent = processStep === idx;
              return (
                <div key={idx} className="flex items-center space-x-2 text-xs">
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  ) : isCurrent ? (
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-[#0f6b56] border-t-transparent animate-spin shrink-0" />
                  ) : (
                    <span className="w-3.5 h-3.5 rounded-full border border-slate-300 shrink-0" />
                  )}
                  <span className={isCurrent ? 'font-semibold text-slate-900' : isDone ? 'text-slate-600' : 'text-slate-400'}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : !file ? (
        /* Drag & Drop Area */
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-7 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-teal-600 bg-teal-50/20'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          <Upload className="w-7 h-7 text-slate-400 mx-auto mb-2.5" />
          <p className="text-sm font-medium text-slate-700">
            Drag & drop your PDF here
          </p>
          <p className="text-xs text-slate-500 my-1">or</p>
          <button
            type="button"
            className="px-3 py-1 bg-white border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50 shadow-2xs"
          >
            Choose PDF
          </button>
          <p className="text-[11px] text-slate-400 mt-2.5">Supported format: PDF &bull; Maximum 25 MB</p>
        </div>
      ) : (
        /* Selected File Review */
        <div className="space-y-3.5">
          <div className="p-3 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <FileText className="w-4 h-4 text-[#0f6b56]" />
              <div>
                <p className="text-xs font-medium text-slate-900">{file.name}</p>
                <p className="text-[11px] text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
            <button
              onClick={() => setFile(null)}
              className="p-1 rounded hover:bg-slate-200 text-slate-500"
              title="Remove file"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center space-x-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={forceOcr}
                onChange={(e) => setForceOcr(e.target.checked)}
                className="rounded border-slate-300 text-[#0f6b56] focus:ring-teal-600"
              />
              <span>Force OCR (for scanned image documents)</span>
            </label>

            <div className="flex items-center space-x-2">
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-3 py-1.5 border border-slate-200 rounded text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
              )}
              <button
                type="button"
                onClick={handleUpload}
                className="px-4 py-1.5 bg-[#0f6b56] hover:bg-[#0c5947] text-white rounded text-xs font-semibold transition-colors shadow-2xs"
              >
                Upload & Extract
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
