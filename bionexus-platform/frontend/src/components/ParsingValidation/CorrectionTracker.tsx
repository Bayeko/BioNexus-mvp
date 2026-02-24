/**
 * CorrectionTracker - Shows all human corrections made to AI-extracted data
 *
 * 21 CFR Part 11: Document who changed what, when, and why
 */

import React from 'react';
import { AlertCircle, FileText } from 'lucide-react';

interface Correction {
  field: string;
  original: any;
  corrected: any;
  notes: string;
}

interface CorrectionTrackerProps {
  corrections: Correction[];
}

const CorrectionTracker: React.FC<CorrectionTrackerProps> = ({ corrections }) => {
  if (corrections.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center space-x-2">
        <AlertCircle className="w-5 h-5 text-yellow-600" />
        <h3 className="font-bold text-gray-900">
          {corrections.length} Correction{corrections.length !== 1 ? 's' : ''}
        </h3>
      </div>

      <div className="space-y-2 max-h-32 overflow-y-auto">
        {corrections.map((correction, idx) => (
          <div key={idx} className="bg-white p-3 rounded border border-yellow-200 text-xs">
            <div className="flex items-start space-x-2">
              <FileText className="w-3 h-3 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900">
                  {correction.field}
                </p>
                <p className="text-gray-600 font-mono truncate">
                  {JSON.stringify(correction.original)} →{' '}
                  {JSON.stringify(correction.corrected)}
                </p>
                {correction.notes && (
                  <p className="text-gray-700 italic mt-1">
                    Reason: {correction.notes}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-600 italic">
        All corrections will be recorded in the audit trail with timestamp and
        your attribution.
      </p>
    </div>
  );
};

export default CorrectionTracker;
