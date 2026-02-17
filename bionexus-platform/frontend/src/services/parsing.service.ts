/**
 * Parsing Service - API calls for parsing validation
 */

import { API_BASE_URL } from '../config';

export interface ParsedDataResponse {
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

export interface RawFileResponse {
  blob: Blob;
  fileName: string;
  contentType: string;
}

class ParsingService {
  /**
   * Get ParsedData for validation
   */
  async getParsedData(parsedDataId: number): Promise<ParsedDataResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/parsing/${parsedDataId}/`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to load parsing data: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Validate parsing and submit corrections
   */
  async validateParsing(
    parsedDataId: number,
    data: {
      confirmed_data: Record<string, any>;
      validation_notes: string;
    }
  ): Promise<ParsedDataResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/parsing/${parsedDataId}/validate/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Validation failed');
    }

    return response.json();
  }

  /**
   * Get raw file associated with parsing
   */
  async getRawFile(parsedDataId: number): Promise<RawFileResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/parsing/${parsedDataId}/rawfile/`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to load raw file: ${response.statusText}`);
    }

    const blob = await response.blob();
    const fileName = this.extractFileName(response.headers.get('content-disposition') || '');

    return {
      blob,
      fileName,
      contentType: response.headers.get('content-type') || 'application/octet-stream',
    };
  }

  /**
   * Get correction history for a parsing
   */
  async getCorrectionHistory(parsedDataId: number): Promise<any[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/parsing/${parsedDataId}/corrections/`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.getAccessToken()}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to load correction history');
    }

    const data = await response.json();
    return data.corrections;
  }

  private getAccessToken(): string {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      throw new Error('No access token found. Please login.');
    }
    return token;
  }

  private extractFileName(contentDisposition: string): string {
    const match = contentDisposition.match(/filename="(.+?)"/);
    return match ? match[1] : 'file';
  }
}

export const parsingService = new ParsingService();
