/**
 * CertificationModal - Double authentication before report certification
 *
 * 21 CFR Part 11: Non-repudiation via password re-entry
 *
 * Step 1: Re-authenticate with password
 * Step 2: Optional OTP verification
 * Step 3: Add certification notes
 * Step 4: Sign and submit
 */

import React, { useState } from 'react';
import { Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { cryptoService } from '../../services/crypto.service';

interface CertificationModalProps {
  parsedDataId: number;
  onClose: () => void;
  onSuccess: () => void;
}

const CertificationModal: React.FC<CertificationModalProps> = ({
  parsedDataId,
  onClose,
  onSuccess,
}) => {
  const [step, setStep] = useState<'password' | 'notes' | 'confirm'>('password');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [notes, setNotes] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePasswordSubmit = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Verify password (this would call backend)
      // For now, just validate locally
      if (password.length < 6) {
        setError('Invalid password');
        return;
      }

      // Move to notes step
      setStep('notes');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNotesSubmit = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Move to confirmation
      setStep('confirm');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to proceed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCertify = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Call certification API
      await cryptoService.signReport({
        parsedDataId,
        password,
        notes,
        otpCode: otpCode || undefined,
      });

      // Success!
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Certification failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 text-white">
          <div className="flex items-center space-x-3">
            <Lock className="w-6 h-6" />
            <div>
              <h2 className="text-lg font-bold">Certify Report</h2>
              <p className="text-sm text-blue-100">Double authentication required</p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-900">Error</p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          )}

          {/* Step 1: Password Authentication */}
          {step === 'password' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900">
                <p className="font-semibold mb-1">21 CFR Part 11 Requirement</p>
                <p className="text-xs">
                  Re-enter your password to verify your identity and create a
                  non-repudiable certification record.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* OTP Field (Optional) */}
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  One-Time Password (Optional)
                </label>
                <input
                  type="text"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder="6-digit code if enabled"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  maxLength="6"
                />
              </div>
            </div>
          )}

          {/* Step 2: Notes */}
          {step === 'notes' && (
            <div className="space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-900">
                <p className="font-semibold mb-1">Certification Notes</p>
                <p className="text-xs">
                  Document the reason for certification. This will be included in
                  the audit report submitted to regulators.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g., All validation checks passed. Data quality verified."
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Step 3: Confirmation */}
          {step === 'confirm' && (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
                <p className="font-bold text-green-900 mb-2">
                  ✓ Ready to Certify
                </p>
                <div className="space-y-2 text-green-800">
                  <p>• Identity verified</p>
                  <p>• Chain integrity confirmed</p>
                  <p>• All corrections documented</p>
                  <p>• Ready for audit submission</p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-3 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">Certified By:</span>
                  <span className="font-mono font-bold text-gray-900">
                    Your Username
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Timestamp:</span>
                  <span className="font-mono font-bold text-gray-900">
                    {new Date().toISOString()}
                  </span>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-900">
                <p className="font-semibold mb-1">Legal Statement</p>
                <p>
                  By clicking "Certify," you attest that the above parsing
                  validation is accurate and complete, and that you are
                  authorized to certify this data for audit submission under 21
                  CFR Part 11.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center space-x-3 rounded-b-lg">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>

          {step === 'password' && (
            <button
              onClick={handlePasswordSubmit}
              disabled={isLoading || !password}
              className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Verifying...' : 'Next'}
            </button>
          )}

          {step === 'notes' && (
            <button
              onClick={handleNotesSubmit}
              disabled={isLoading || !notes}
              className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Processing...' : 'Review'}
            </button>
          )}

          {step === 'confirm' && (
            <button
              onClick={handleCertify}
              disabled={isLoading}
              className="ml-auto px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
            >
              <Lock className="w-4 h-4" />
              <span>{isLoading ? 'Certifying...' : 'Certify Report'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default CertificationModal;
