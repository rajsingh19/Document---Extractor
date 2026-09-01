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
    'Extracting information',
    'Checking extracted data',
    'Saving results'
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
      setErrorMessage('Please upload a PDF document (.pdf).');
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setErrorMessage('File size exceeds 10 MB limit.');
      return;
    }
    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsProcessing(true);
    setErrorMessage(null);
    setProcessStep(0);

    // Simulate clean sequential step indicators for user feedback
    const stepInterval = setInterval(() => {
      setProcessStep((prev) => (prev < 3 ? prev + 1 : prev));
    }, 900);

    try {
      const result = await uploadDocument(file, true, forceOcr);
      clearInterval(stepInterval);
      setProcessStep(3);
      setTimeout(() => {
        setIsProcessing(false);
        setFile(null);
        if (onUploadSuccess) onUploadSuccess(result);
      }, 500);
    } catch (err) {
      clearInterval(stepInterval);
      setIsProcessing(false);
      console.error('Upload failed:', err);
      const detail = err.response?.data?.detail || err.message || 'Failed to upload and process document.';
      setErrorMessage(detail);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Upload a document</h3>
          <p className="text-xs text-slate-500 mt-0.5">Extract metrics, billing data, and compliance from business PDFs.</p>
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

      {errorMessage && (
        <div className="mb-4 p-3 rounded-md bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {isProcessing ? (
        <div className="py-8 text-center space-y-4">
          <Loader2 className="w-8 h-8 text-teal-700 animate-spin mx-auto" />
          <div>
            <h4 className="text-sm font-medium text-slate-900">Processing document...</h4>
            <p className="text-xs text-slate-500 mt-1">{file?.name}</p>
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
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-teal-700 border-t-transparent animate-spin shrink-0" />
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
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-teal-600 bg-teal-50/30'
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
          <Upload className="w-8 h-8 text-slate-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-700">
            Drag and drop a PDF here
          </p>
          <p className="text-xs text-slate-500 my-1.5">or</p>
          <button
            type="button"
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 shadow-sm"
          >
            Choose File
          </button>
          <p className="text-[11px] text-slate-400 mt-3">PDF documents only &bull; Up to 10 MB</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="w-5 h-5 text-teal-700" />
              <div>
                <p className="text-sm font-medium text-slate-900">{file.name}</p>
                <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
            <button
              onClick={() => setFile(null)}
              className="p-1 rounded hover:bg-slate-200 text-slate-500"
              title="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between pt-2">
            <label className="flex items-center space-x-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={forceOcr}
                onChange={(e) => setForceOcr(e.target.checked)}
                className="rounded border-slate-300 text-teal-700 focus:ring-teal-600"
              />
              <span>Force Tesseract OCR (for scanned images)</span>
            </label>

            <div className="flex items-center space-x-2">
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-3 py-1.5 border border-slate-300 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
              )}
              <button
                type="button"
                onClick={handleUpload}
                className="px-4 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-xs font-medium transition-colors shadow-sm"
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
