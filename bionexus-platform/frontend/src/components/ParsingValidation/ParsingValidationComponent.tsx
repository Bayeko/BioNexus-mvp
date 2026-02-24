/**
 * ParsingValidationComponent - Split-view parsing validation
 *
 * Layout:
 * [Raw File Viewer] | [Validation Form]
 *     PDF/CSV        | Dynamic form from Pydantic schema
 *
 * Features:
 * - Real-time correction tracking
 * - Visual distinction for human corrections
 * - Chain integrity badge
 * - Double auth certification modal
 */

import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Shield, Lock } from 'lucide-react';
import RawFileViewer from './RawFileViewer';
import DynamicFormBuilder from './DynamicFormBuilder';
import CorrectionTracker from './CorrectionTracker';
import ChainIntegrityBadge from './ChainIntegrityBadge';
import CertificationModal from './CertificationModal';
import { parsingService } from '../../services/parsing.service';
import { integrityService } from '../../services/integrity.service';

interface ParsedData {
  id: number;
  state: 'pending' | 'validated' | 'rejected';
  extraction_model: string;
  extraction_confidence: number;
  extracted_data: Record<string, any>;
  confirmed_data: Record<string, any>;
  corrections: Array<{
    field: string;
    original: any;
    corrected: any;
    notes: string;
  }>;
  created_at: string;
  validated_at?: string;
  validated_by_id?: number;
}

interface ParsingValidationProps {
  parsedDataId: number;
  onValidationComplete?: () => void;
}

const ParsingValidationComponent: React.FC<ParsingValidationProps> = ({
  parsedDataId,
  onValidationComplete,
}) => {
  const [parsedData, setParsedData] = useState<ParsedData | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [corrections, setCorrections] = useState<any[]>([]);
  const [chainStatus, setChainStatus] = useState<any>(null);
  const [showCertification, setShowCertification] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load parsing data on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        const data = await parsingService.getParsedData(parsedDataId);
        setParsedData(data);
        setFormData(data.confirmed_data || data.extracted_data);
        setCorrections(data.corrections || []);

        // Check chain integrity
        const chainResult = await integrityService.checkChainIntegrity();
        setChainStatus(chainResult);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [parsedDataId]);

  // Track corrections when form changes
  const handleFormChange = (
    fieldName: string,
    newValue: any,
    reason?: string
  ) => {
    setFormData((prev) => ({
      ...prev,
      [fieldName]: newValue,
      [`_notes_${fieldName}`]: reason || '',
    }));

    // Track correction
    const original = parsedData?.extracted_data[fieldName];
    if (original !== newValue) {
      setCorrections((prev) => {
        const existing = prev.find((c) => c.field === fieldName);
        if (existing) {
          return prev.map((c) =>
            c.field === fieldName
              ? { ...c, corrected: newValue, notes: reason }
              : c
          );
        }
        return [
          ...prev,
          { field: fieldName, original, corrected: newValue, notes: reason },
        ];
      });
    }
  };

  const handleValidate = async () => {
    try {
      if (!parsedData) return;

      await parsingService.validateParsing(parsedDataId, {
        confirmed_data: formData,
        validation_notes: `Corrected ${corrections.length} fields`,
      });

      onValidationComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading parsing data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <div className="flex items-center">
          <AlertCircle className="w-5 h-5 text-red-600 mr-3" />
          <div>
            <h3 className="font-semibold text-red-900">Error</h3>
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!parsedData) {
    return <div className="text-center p-4">No parsing data found</div>;
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Parsing Validation
            </h1>
            <p className="text-gray-600 text-sm">
              Review and correct AI-extracted data
            </p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Chain Integrity Badge */}
            <ChainIntegrityBadge status={chainStatus} />

            {/* Confidence Indicator */}
            <div className="flex items-center space-x-2">
              <Shield className="w-5 h-5 text-blue-600" />
              <div>
                <p className="text-xs font-semibold text-gray-700">
                  CONFIDENCE
                </p>
                <p className="text-lg font-bold text-blue-600">
                  {Math.round(parsedData.extraction_confidence * 100)}%
                </p>
              </div>
            </div>

            {/* Model Info */}
            <div>
              <p className="text-xs font-semibold text-gray-700">MODEL</p>
              <p className="text-sm font-mono text-gray-600">
                {parsedData.extraction_model}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Split View */}
      <div className="flex-1 overflow-hidden flex">
        {/* Left: Raw File Viewer */}
        <div className="w-1/2 border-r border-gray-200 overflow-auto bg-white">
          <RawFileViewer parsedDataId={parsedDataId} />
        </div>

        {/* Right: Validation Form */}
        <div className="w-1/2 overflow-auto flex flex-col">
          <div className="flex-1 overflow-auto p-6">
            <DynamicFormBuilder
              extractedData={parsedData.extracted_data}
              confirmedData={parsedData.confirmed_data}
              onFieldChange={handleFormChange}
            />
          </div>

          {/* Correction Summary */}
          {corrections.length > 0 && (
            <div className="border-t border-gray-200 bg-yellow-50 p-4">
              <CorrectionTracker corrections={corrections} />
            </div>
          )}
        </div>
      </div>

      {/* Footer - Actions */}
      <div className="bg-white border-t border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {parsedData.state === 'validated' && (
            <>
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-green-700 font-semibold">
                Validated by {parsedData.validated_by_id}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {/* Corrections info */}
          <span className="text-sm text-gray-600">
            {corrections.length} correction{corrections.length !== 1 ? 's' : ''}
          </span>

          {/* Validate Button */}
          <button
            onClick={handleValidate}
            disabled={
              parsedData.state === 'validated' ||
              !chainStatus?.safe_to_export
            }
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {parsedData.state === 'validated' ? 'Already Validated' : 'Validate'}
          </button>

          {/* Certification Button */}
          <button
            onClick={() => setShowCertification(true)}
            disabled={
              parsedData.state !== 'validated' ||
              !chainStatus?.safe_to_export
            }
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
          >
            <Lock className="w-4 h-4" />
            <span>Certify for Audit</span>
          </button>
        </div>
      </div>

      {/* Certification Modal */}
      {showCertification && (
        <CertificationModal
          parsedDataId={parsedDataId}
          onClose={() => setShowCertification(false)}
          onSuccess={() => {
            setShowCertification(false);
            onValidationComplete?.();
          }}
        />
      )}
    </div>
  );
};

export default ParsingValidationComponent;
