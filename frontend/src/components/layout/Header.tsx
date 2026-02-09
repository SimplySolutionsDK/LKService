import React from 'react';
import { Select } from '../ui/Select';
import type { EmployeeType } from '../../types';
import './Header.css';

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
    <header>
      <div className="header-content">
        <div className="logo">
          <div className="logo-icon">⏱</div>
          <h1>Tidsregistrering Parser</h1>
        </div>
        
        <div className="settings-button">
          <div className="settings-icon">⚙️</div>
          <div className="settings-dropdown">
            <h3 className="settings-dropdown-title">Indstillinger</h3>
            <Select
              label="Medarbejdertype"
              value={employeeType}
              onChange={(e) => onEmployeeTypeChange(e.target.value as EmployeeType)}
              options={employeeTypeOptions}
            />
          </div>
        </div>
      </div>
      
      <p className="subtitle">Upload CSV-filer og få dem formateret med overtidsberegning</p>
    </header>
  );
};
