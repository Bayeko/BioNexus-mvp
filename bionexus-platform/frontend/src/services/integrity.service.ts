/**
 * Integrity Service - Check audit chain integrity in real-time
 *
 * Calls verify_chain_integrity() API
 * Used by ChainIntegrityBadge for live status updates
 */

import { API_BASE_URL } from '../config';

export interface ChainIntegrityStatus {
  is_valid: boolean;
  total_records: number;
  verified_records: number;
  corrupted_records: Array<{
    id: number;
    error: string;
  }>;
  chain_integrity_ok: boolean;
  checked_at: string;
  safe_to_export: boolean;
}

class IntegrityService {
  private lastCheckTime = 0;
  private cacheTime = 5000; // Cache for 5 seconds to avoid excessive calls

  /**
   * Check audit chain integrity
   *
   * Returns:
   * - is_valid: All records have valid signatures
   * - chain_integrity_ok: Chain is unbroken
   * - safe_to_export: true if both conditions met
   */
  async checkChainIntegrity(): Promise<ChainIntegrityStatus> {
    // Check cache
    const now = Date.now();
    if (now - this.lastCheckTime < this.cacheTime) {
      const cached = sessionStorage.getItem('chainIntegrityStatus');
      if (cached) {
        return JSON.parse(cached);
      }
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/integrity/check/`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Chain integrity check failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Cache result
      this.lastCheckTime = Date.now();
      sessionStorage.setItem('chainIntegrityStatus', JSON.stringify(data));

      return data;
    } catch (error) {
      console.error('Chain integrity check error:', error);
      throw error;
    }
  }

  /**
   * Check if safe to export
   * Quick check - returns true if last check passed
   */
  async isSafeToExport(): Promise<boolean> {
    try {
      const status = await this.checkChainIntegrity();
      return status.safe_to_export;
    } catch {
      return false;
    }
  }

  /**
   * Get detailed corruption report
   */
  async getCorruptionReport(
    detail: boolean = false
  ): Promise<{ total: number; details: any[] }> {
    const status = await this.checkChainIntegrity();

    return {
      total: status.corrupted_records.length,
      details: detail ? status.corrupted_records : [],
    };
  }

  /**
   * Clear cache (force next check to hit API)
   */
  clearCache(): void {
    sessionStorage.removeItem('chainIntegrityStatus');
    this.lastCheckTime = 0;
  }

  private getAccessToken(): string {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      throw new Error('No access token found. Please login.');
    }
    return token;
  }
}

export const integrityService = new IntegrityService();
