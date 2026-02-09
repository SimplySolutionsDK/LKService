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
    <div className="flex flex-col gap-2">
      <label htmlFor="employee-select" className="font-medium text-slate-100 text-[0.9rem]">
        Vælg Medarbejder:
      </label>
      <select
        id="employee-select"
        className="py-2.5 px-2.5 border border-border rounded bg-bg-primary text-slate-100 text-[0.9rem] cursor-pointer transition-colors select-arrow hover:enabled:border-accent focus:outline-none focus:border-accent focus:shadow-[0_0_0_3px_rgba(59,130,246,0.1)] disabled:bg-bg-secondary disabled:cursor-not-allowed disabled:opacity-60"
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
        <small className="text-slate-400 text-[0.8rem]">
          {employees.length} medarbejder{employees.length !== 1 ? 'e' : ''} tilgængelig{employees.length !== 1 ? 'e' : ''}
        </small>
      )}
    </div>
  );
};
