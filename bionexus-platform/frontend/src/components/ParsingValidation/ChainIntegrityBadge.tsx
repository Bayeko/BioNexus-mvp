/**
 * ChainIntegrityBadge - Real-time audit chain integrity indicator
 *
 * Shows:
 * - Chain status: VALID ✓ or CORRUPTED ✗
 * - Record counts (verified/corrupted)
 * - Last check timestamp
 * - Safe to export indicator
 *
 * Calls verify_chain_integrity() API every 30 seconds
 */

import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle, RefreshCw, Clock } from 'lucide-react';
import { integrityService } from '../../services/integrity.service';

interface ChainStatus {
  is_valid: boolean;
  total_records: number;
  verified_records: number;
  corrupted_records: any[];
  chain_integrity_ok: boolean;
  checked_at: string;
  safe_to_export: boolean;
}

interface ChainIntegrityBadgeProps {
  status?: ChainStatus;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
}

const ChainIntegrityBadge: React.FC<ChainIntegrityBadgeProps> = ({
  status: initialStatus,
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
}) => {
  const [status, setStatus] = useState<ChainStatus | null>(initialStatus || null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // Refresh chain status
  const refreshStatus = async () => {
    try {
      setIsRefreshing(true);
      const result = await integrityService.checkChainIntegrity();
      setStatus(result);
    } catch (error) {
      console.error('Failed to check chain integrity:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(refreshStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  // Initial load if not provided
  useEffect(() => {
    if (!status && autoRefresh) {
      refreshStatus();
    }
  }, []);

  if (!status) {
    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <div className="animate-spin">
          <RefreshCw className="w-4 h-4" />
        </div>
        <span className="text-xs">Checking...</span>
      </div>
    );
  }

  const isValid = status.chain_integrity_ok && status.is_valid;
  const bgColor = isValid ? 'bg-green-100' : 'bg-red-100';
  const borderColor = isValid ? 'border-green-300' : 'border-red-300';
  const textColor = isValid ? 'text-green-900' : 'text-red-900';
  const Icon = isValid ? Shield : AlertTriangle;

  return (
    <div className="relative">
      {/* Badge Button */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`px-3 py-2 rounded-lg border ${bgColor} ${borderColor} ${textColor} text-xs font-bold flex items-center space-x-2 hover:shadow-md transition-shadow`}
      >
        <Icon className="w-4 h-4" />
        <span>{isValid ? 'CHAIN VERIFIED' : 'CHAIN ERROR'}</span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            refreshStatus();
          }}
          disabled={isRefreshing}
          className="ml-2 p-1 hover:bg-white/30 rounded disabled:opacity-50"
        >
          <RefreshCw
            className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`}
          />
        </button>
      </button>

      {/* Detailed Popup */}
      {showDetails && (
        <div className={`absolute right-0 mt-2 w-80 bg-white border ${borderColor} rounded-lg shadow-xl z-50 p-4`}>
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-gray-900 text-sm">
              Audit Chain Integrity
            </h3>
            <button
              onClick={() => setShowDetails(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          {/* Status Indicator */}
          <div className={`p-3 rounded-lg mb-3 ${bgColor} border ${borderColor}`}>
            <div className="flex items-center space-x-2">
              <Icon className={`w-5 h-5 ${isValid ? 'text-green-600' : 'text-red-600'}`} />
              <span className={`font-bold ${textColor}`}>
                {isValid ? '✓ Chain Integrity Valid' : '✗ Chain Corrupted'}
              </span>
            </div>
          </div>

          {/* Statistics */}
          <div className="space-y-2 mb-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-700">Total Records:</span>
              <span className="font-mono font-bold text-gray-900">
                {status.total_records}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-700">Verified:</span>
              <span className="font-mono font-bold text-green-600">
                {status.verified_records}
              </span>
            </div>
            {status.corrupted_records.length > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-700">Corrupted:</span>
                <span className="font-mono font-bold text-red-600">
                  {status.corrupted_records.length}
                </span>
              </div>
            )}
          </div>

          {/* Corrupted Records Details */}
          {status.corrupted_records.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded p-2 mb-3 max-h-32 overflow-y-auto">
              <p className="text-xs font-bold text-red-900 mb-2">
                Corrupted Records:
              </p>
              {status.corrupted_records.slice(0, 5).map((record, idx) => (
                <div key={idx} className="text-xs text-red-800 mb-1">
                  <p className="font-mono">ID: {record.id}</p>
                  <p className="text-xs text-red-700 truncate">{record.error}</p>
                </div>
              ))}
              {status.corrupted_records.length > 5 && (
                <p className="text-xs text-red-700 font-semibold">
                  ...and {status.corrupted_records.length - 5} more
                </p>
              )}
            </div>
          )}

          {/* Last Check Time */}
          <div className="flex items-center space-x-2 text-xs text-gray-600 border-t border-gray-200 pt-2">
            <Clock className="w-3 h-3" />
            <span>
              Last checked: {new Date(status.checked_at).toLocaleTimeString()}
            </span>
          </div>

          {/* Safe to Export Info */}
          <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded">
            <p className="text-xs font-semibold text-blue-900">
              {status.safe_to_export
                ? '✓ Safe to export certified reports'
                : '✗ Cannot export until chain is verified'}
            </p>
          </div>

          {/* 21 CFR Part 11 Note */}
          <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-900">
            <p className="font-semibold">21 CFR Part 11 Compliance</p>
            <p className="text-xs mt-1">
              This verification proves data integrity. Any corruption prevents
              certified report generation.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChainIntegrityBadge;
