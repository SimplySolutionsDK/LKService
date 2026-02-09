import React from 'react';
import { Select } from '../ui/Select';
import type { EmployeeType } from '../../types';

interface HeaderProps {
  employeeType: EmployeeType;
  onEmployeeTypeChange: (type: EmployeeType) => void;
}

const employeeTypeOptions = [
  { value: 'Svend', label: 'Svend (Faglært)' },
  { value: 'Lærling', label: 'Lærling' },
  { value: 'Funktionær', label: 'Funktionær' },
  { value: 'Elev', label: 'Elev (Handels/Kontor)' },
];

export const Header: React.FC<HeaderProps> = ({ employeeType, onEmployeeTypeChange }) => {
  return (
    <header className="text-center mb-10 relative max-md:mb-6">
      <div className="relative flex items-start justify-center mb-4 max-md:justify-between max-md:w-full">
        <div className="flex items-center justify-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-accent to-violet-500 rounded-xl flex items-center justify-center text-2xl shadow-[0_4px_20px_var(--color-accent-glow)] max-md:w-10 max-md:h-10 max-md:text-xl">
            ⏱
          </div>
          <h1 className="text-[1.75rem] font-bold tracking-tight max-md:text-2xl">
            Tidsregistrering Parser
          </h1>
        </div>

        <div className="absolute right-0 top-0 cursor-pointer group max-md:static max-md:ml-auto">
          <div className="w-11 h-11 bg-bg-card border border-border rounded-xl flex items-center justify-center text-xl transition-all group-hover:border-accent group-hover:bg-bg-secondary group-hover:rotate-45">
            ⚙️
          </div>
          <div className="absolute right-0 top-[calc(100%+0.5rem)] bg-bg-card border border-border rounded-xl p-5 min-w-[280px] opacity-0 invisible -translate-y-2.5 transition-all shadow-[0_8px_32px_rgba(0,0,0,0.3)] z-[100] group-hover:opacity-100 group-hover:visible group-hover:translate-y-0">
            <h3 className="text-base font-semibold mb-4 text-slate-100">Indstillinger</h3>
            <Select
              label="Medarbejdertype"
              value={employeeType}
              onChange={(e) => onEmployeeTypeChange(e.target.value as EmployeeType)}
              options={employeeTypeOptions}
            />
          </div>
        </div>
      </div>

      <p className="text-slate-400 text-[0.95rem] mt-2 max-md:text-[0.85rem]">
        Upload CSV-filer og få dem formateret med overtidsberegning
      </p>
    </header>
  );
};
