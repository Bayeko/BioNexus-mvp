/**
 * Application Configuration
 */

// API Base URL
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Feature Flags
export const FEATURES = {
  chainIntegrityBadge: true,
  doubleAuthCertification: true,
  correctionTracking: true,
  rawFileViewer: true,
  dynamicFormBuilder: true,
};

// Cache Settings
export const CACHE = {
  chainIntegrityCheckInterval: 30000, // 30 seconds
  chainIntegrityTimeout: 5000, // 5 seconds cache
};

// UI Settings
export const UI = {
  animationDuration: 200, // milliseconds
  maxCorrectionNoteLength: 500,
  maxCertificationNoteLength: 1000,
};

// 21 CFR Part 11 Settings
export const COMPLIANCE = {
  requirePasswordReauth: true,
  require2FA: false, // Can be enabled per user
  signatureAlgorithm: 'SHA256',
  minPasswordLength: 8,
  tokenExpiration: 900000, // 15 minutes
  refreshTokenExpiration: 604800000, // 7 days
};
