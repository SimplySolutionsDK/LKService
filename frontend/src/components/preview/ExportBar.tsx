import React from 'react';
import { Button } from '../ui/Button';
import type { OutputFormat } from '../../types';
import './ExportBar.css';

interface ExportBarProps {
  outputFormat: OutputFormat;
  onFormatChange: (format: OutputFormat) => void;
  onExport: () => void;
}

const formatOptions = [
  { value: 'daily', label: 'Daglig oversigt (standard)' },
  { value: 'detailed', label: 'Daglig oversigt (detaljeret DBR 2026)' },
  { value: 'weekly', label: 'Ugentlig opsummering' },
  { value: 'weekly_detailed', label: 'Ugentlig opsummering (detaljeret)' },
  { value: 'combined', label: 'Kombineret (begge)' },
];

export const ExportBar: React.FC<ExportBarProps> = ({
  outputFormat,
  onFormatChange,
  onExport,
}) => {
  return (
    <div className="export-bar">
      <div className="export-format">
        <label htmlFor="outputFormat">Eksport format:</label>
        <select
          id="outputFormat"
          value={outputFormat}
          onChange={(e) => onFormatChange(e.target.value as OutputFormat)}
        >
          {formatOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <Button
        variant="success"
        onClick={onExport}
        className="export-btn"
      >
        <span>📥</span>
        Download CSV
      </Button>
    </div>
  );
};
