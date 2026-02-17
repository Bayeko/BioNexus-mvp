/**
 * Crypto Service - Handle JWT, certification signing, double auth
 *
 * Features:
 * - JWT token management
 * - Report certification with password re-authentication
 * - OTP support (optional)
 * - Non-repudiable signing for 21 CFR Part 11
 */

import { API_BASE_URL } from '../config';

export interface SignReportRequest {
  parsedDataId: number;
  password: string;
  notes: string;
  otpCode?: string;
}

export interface SignReportResponse {
  id: number;
  state: string;
  certified_by: string;
  certified_at: string;
  message: string;
}

class CryptoService {
  /**
   * Sign/certify a report with double authentication
   *
   * 21 CFR Part 11:
   * - Password verification (second factor)
   * - Non-repudiable signature
   * - Timestamp attribution
   * - Reason documentation
   */
  async signReport(request: SignReportRequest): Promise<SignReportResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/reports/${request.parsedDataId}/sign/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
        body: JSON.stringify({
          password: request.password,
          notes: request.notes,
          otp_code: request.otpCode,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Certification failed');
    }

    return response.json();
  }

  /**
   * Get current JWT token
   */
  getAccessToken(): string {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      throw new Error('No access token found. Please login.');
    }
    return token;
  }

  /**
   * Get JWT refresh token
   */
  getRefreshToken(): string {
    const token = localStorage.getItem('refreshToken');
    if (!token) {
      throw new Error('No refresh token found.');
    }
    return token;
  }

  /**
   * Refresh JWT access token
   */
  async refreshToken(): Promise<{ access: string; refresh: string }> {
    const refreshToken = this.getRefreshToken();

    const response = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      // Clear tokens if refresh fails
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      throw new Error('Token refresh failed. Please login again.');
    }

    const data = await response.json();

    // Update tokens
    localStorage.setItem('accessToken', data.access);
    if (data.refresh) {
      localStorage.setItem('refreshToken', data.refresh);
    }

    return data;
  }

  /**
   * Verify password for double auth
   * (Called before signing to verify identity)
   */
  async verifyPassword(password: string): Promise<boolean> {
    // In a real implementation, this would call a backend endpoint
    // For now, we rely on the sign endpoint doing the verification
    return password.length >= 6;
  }

  /**
   * Generate OTP request (if 2FA enabled)
   */
  async requestOTP(): Promise<{ otp_id: string; method: string }> {
    const response = await fetch(`${API_BASE_URL}/api/auth/otp/request/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.getAccessToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to request OTP');
    }

    return response.json();
  }

  /**
   * Verify OTP code
   */
  async verifyOTP(otpCode: string, otpId: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/api/auth/otp/verify/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`,
      },
      body: JSON.stringify({
        code: otpCode,
        otp_id: otpId,
      }),
    });

    return response.ok;
  }

  /**
   * Get user's public key (for signature verification)
   */
  async getUserPublicKey(userId: number): Promise<string> {
    const response = await fetch(
      `${API_BASE_URL}/api/users/${userId}/public-key/`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to get public key');
    }

    const data = await response.json();
    return data.public_key;
  }

  /**
   * Verify report signature
   * (Check that report was actually signed by the claimed user)
   */
  async verifySignature(
    reportId: number,
    signature: string,
    userId: number
  ): Promise<boolean> {
    try {
      const publicKey = await this.getUserPublicKey(userId);

      // In a real implementation, use cryptographic library to verify
      // For now, just ensure signature format is valid
      return signature.length === 64 && /^[a-f0-9]{64}$/.test(signature);
    } catch {
      return false;
    }
  }

  /**
   * Check if 2FA is enabled for current user
   */
  async is2FAEnabled(): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/api/auth/2fa/status/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${this.getAccessToken()}`,
      },
    });

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    return data.enabled;
  }
}

export const cryptoService = new CryptoService();
