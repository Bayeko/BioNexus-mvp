/**
 * RawFileViewer - Display PDF/CSV raw file for comparison
 *
 * Shows the original machine-generated file alongside the parsing validation form
 */

import React, { useEffect, useState } from 'react';
import { Download, AlertCircle } from 'lucide-react';
import { parsingService } from '../../services/parsing.service';

interface RawFileViewerProps {
  parsedDataId: number;
}

const RawFileViewer: React.FC<RawFileViewerProps> = ({ parsedDataId }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fileType, setFileType] = useState<'pdf' | 'csv' | 'text'>('text');

  useEffect(() => {
    const loadFile = async () => {
      try {
        setIsLoading(true);
        const response = await parsingService.getRawFile(parsedDataId);

        // Create object URL from blob
        const url = URL.createObjectURL(response.blob);
        setFileUrl(url);
        setFileName(response.fileName);

        // Determine file type
        if (response.fileName.endsWith('.pdf')) {
          setFileType('pdf');
        } else if (response.fileName.endsWith('.csv')) {
          setFileType('csv');
        } else {
          setFileType('text');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load file');
      } finally {
        setIsLoading(false);
      }
    };

    loadFile();

    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [parsedDataId]);

  const handleDownload = () => {
    if (fileUrl) {
      const link = document.createElement('a');
      link.href = fileUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600 text-sm">Loading file...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-600 mx-auto mb-2" />
          <p className="text-red-600 text-sm font-semibold">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-gray-100 border-b border-gray-200 p-4 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900 text-sm">Original File</h3>
          <p className="text-xs text-gray-600 font-mono">{fileName}</p>
        </div>
        <button
          onClick={handleDownload}
          className="p-2 hover:bg-gray-200 rounded transition-colors"
          title="Download original file"
        >
          <Download className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto bg-white">
        {fileType === 'pdf' ? (
          <iframe
            src={fileUrl || ''}
            className="w-full h-full border-0"
            title="Original PDF"
          />
        ) : fileType === 'csv' ? (
          <CSVViewer fileUrl={fileUrl || ''} />
        ) : (
          <TextViewer fileUrl={fileUrl || ''} />
        )}
      </div>
    </div>
  );
};

// CSV Viewer Component
const CSVViewer: React.FC<{ fileUrl: string }> = ({ fileUrl }) => {
  const [rows, setRows] = useState<string[][]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(fileUrl)
      .then((r) => r.text())
      .then((csv) => {
        const parsed = csv.split('\n').map((line) => line.split(','));
        setRows(parsed);
      })
      .catch((err) => setError(err.message));
  }, [fileUrl]);

  if (error) return <div className="p-4 text-red-600">{error}</div>;

  return (
    <div className="overflow-auto p-4">
      <table className="border-collapse border border-gray-300">
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={idx}
              className={idx === 0 ? 'bg-gray-100' : 'bg-white'}
            >
              {row.map((cell, cellIdx) => (
                <td
                  key={cellIdx}
                  className="border border-gray-300 px-4 py-2 text-sm font-mono"
                >
                  {cell.trim()}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Text Viewer Component
const TextViewer: React.FC<{ fileUrl: string }> = ({ fileUrl }) => {
  const [content, setContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(fileUrl)
      .then((r) => r.text())
      .then(setContent)
      .catch((err) => setError(err.message));
  }, [fileUrl]);

  if (error) return <div className="p-4 text-red-600">{error}</div>;

  return (
    <pre className="p-4 text-xs font-mono text-gray-900 whitespace-pre-wrap overflow-auto h-full">
      {content}
    </pre>
  );
};

export default RawFileViewer;
