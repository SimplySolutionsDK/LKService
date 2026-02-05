import React from 'react';
import { Card, CardTitle } from '../ui/Card';
import { Select } from '../ui/Select';
import { Button } from '../ui/Button';
import { Status } from '../ui/Status';
import type { EmployeeType, StatusMessage } from '../../types';
import './SettingsCard.css';

interface SettingsCardProps {
  employeeType: EmployeeType;
  onEmployeeTypeChange: (type: EmployeeType) => void;
  onPreview: () => void;
  previewDisabled: boolean;
  status?: StatusMessage;
}

const employeeTypeOptions = [
  { value: 'Svend', label: 'Svend (Faglært)' },
  { value: 'Lærling', label: 'Lærling' },
  { value: 'Funktionær', label: 'Funktionær' },
  { value: 'Elev', label: 'Elev (Handels/Kontor)' },
];

export const SettingsCard: React.FC<SettingsCardProps> = ({
  employeeType,
  onEmployeeTypeChange,
  onPreview,
  previewDisabled,
  status,
}) => {
  return (
    <Card>
      <CardTitle icon="⚙️">Indstillinger</CardTitle>
      
      <Select
        label="Medarbejdertype"
        value={employeeType}
        onChange={(e) => onEmployeeTypeChange(e.target.value as EmployeeType)}
        options={employeeTypeOptions}
      />

      <Button
        variant="primary"
        onClick={onPreview}
        disabled={previewDisabled}
        style={{ marginTop: '1rem' }}
      >
        <span>👁</span>
        Vis Preview
      </Button>

      {status && <Status type={status.type} message={status.message} />}
    </Card>
  );
};
