import React from 'react';
import { Button } from '../ui/Button';
import type { OutputFormat } from '../../types';

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
    <div className="p-4 px-5 border-t border-border flex justify-between items-center flex-wrap gap-4 max-md:flex-col max-md:items-stretch">
      <div className="flex items-center gap-3 flex-1 min-w-[250px] max-md:flex-col max-md:items-stretch">
        <label htmlFor="outputFormat" className="text-[0.85rem] text-slate-400 whitespace-nowrap">
          Eksport format:
        </label>
        <select
          id="outputFormat"
          className="flex-1 min-w-[200px] w-full py-2.5 px-3.5 bg-bg-secondary border border-border rounded-lg text-slate-100 font-sans text-[0.9rem] cursor-pointer transition-colors select-arrow hover:border-accent focus:border-accent focus:outline-none"
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
        className="!w-auto py-2.5 px-6 whitespace-nowrap max-md:!w-full"
      >
        <span>📥</span>
        Download CSV
      </Button>
    </div>
  );
};
