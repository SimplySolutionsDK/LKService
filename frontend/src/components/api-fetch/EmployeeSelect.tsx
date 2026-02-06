import React from 'react';
import type { Employee } from '../../types';

interface EmployeeSelectProps {
  employees: Employee[];
  selectedEmployeeId: number | null;
  onEmployeeChange: (employeeId: number, employeeName: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

export const EmployeeSelect: React.FC<EmployeeSelectProps> = ({
  employees,
  selectedEmployeeId,
  onEmployeeChange,
  disabled = false,
  isLoading = false,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const employeeId = parseInt(e.target.value);
    if (!employeeId) return;
    
    const employee = employees.find(emp => emp.employeeId === employeeId);
    if (employee) {
      const fullName = `${employee.firstname} ${employee.lastname}`.trim() || 
                       employee.firstname || 
                       employee.lastname || 
                       `Employee ${employee.employeeId}`;
      onEmployeeChange(employeeId, fullName);
    }
  };

  return (
    <div className="employee-select-group">
      <label htmlFor="employee-select">Vælg Medarbejder:</label>
      <select
        id="employee-select"
        value={selectedEmployeeId || ''}
        onChange={handleChange}
        disabled={disabled || isLoading}
      >
        <option value="">
          {isLoading ? 'Indlæser medarbejdere...' : 'Vælg en medarbejder'}
        </option>
        {employees.map((employee) => {
          const fullName = `${employee.firstname} ${employee.lastname}`.trim() || 
                          employee.firstname || 
                          employee.lastname || 
                          `Employee ${employee.employeeId}`;
          return (
            <option key={employee.employeeId} value={employee.employeeId}>
              {fullName}
            </option>
          );
        })}
      </select>
      {employees.length > 0 && (
        <small className="employee-count">
          {employees.length} medarbejder{employees.length !== 1 ? 'e' : ''} tilgængelig{employees.length !== 1 ? 'e' : ''}
        </small>
      )}
    </div>
  );
};
