import React, { useState, useEffect } from 'react';
import { Card, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { EmployeeSelect } from './EmployeeSelect';
import { DateRangePicker } from './DateRangePicker';
import type { Employee, ApiFetchParams, EmployeeType } from '../../types';
import { api } from '../../services/api';
import './ApiFetchCard.css';

interface ApiFetchCardProps {
  onDataFetched: (params: ApiFetchParams) => void;
  employeeType: EmployeeType;
  isLoading: boolean;
}

export const ApiFetchCard: React.FC<ApiFetchCardProps> = ({
  onDataFetched,
  employeeType: _employeeType,
  isLoading,
}) => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [selectedEmployeeName, setSelectedEmployeeName] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [loadingEmployees, setLoadingEmployees] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load employees on mount
  useEffect(() => {
    const loadEmployees = async () => {
      setLoadingEmployees(true);
      setError(null);
      try {
        const response = await api.fetchEmployees();
        setEmployees(response.results || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load employees');
      } finally {
        setLoadingEmployees(false);
      }
    };

    loadEmployees();
  }, []);

  // Set default date range (current week)
  useEffect(() => {
    const today = new Date();
    const monday = new Date(today);
    monday.setDate(today.getDate() - today.getDay() + 1);
    
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    setStartDate(monday.toISOString().split('T')[0]);
    setEndDate(sunday.toISOString().split('T')[0]);
  }, []);

  const handleEmployeeChange = (employeeId: number, employeeName: string) => {
    setSelectedEmployeeId(employeeId);
    setSelectedEmployeeName(employeeName);
  };

  const handleFetchData = () => {
    if (!selectedEmployeeId || !startDate || !endDate) {
      return;
    }

    if (new Date(endDate) < new Date(startDate)) {
      setError('Slut dato skal være efter start dato');
      return;
    }

    setError(null);
    onDataFetched({
      employeeId: selectedEmployeeId,
      employeeName: selectedEmployeeName,
      startDate,
      endDate,
    });
  };

  const canFetch = selectedEmployeeId && startDate && endDate && !isLoading;

  return (
    <Card>
      <CardTitle icon="🔍">Hent fra API</CardTitle>
      
      <div className="api-fetch-content">
        <p className="api-fetch-description">
          Vælg en medarbejder og datointerval for at hente tidsregistreringer direkte fra API.
        </p>

        <EmployeeSelect
          employees={employees}
          selectedEmployeeId={selectedEmployeeId}
          onEmployeeChange={handleEmployeeChange}
          disabled={isLoading}
          isLoading={loadingEmployees}
        />

        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          disabled={isLoading}
        />

        {error && (
          <div className="api-fetch-error">
            {error}
          </div>
        )}

        <Button
          onClick={handleFetchData}
          disabled={!canFetch}
          variant="primary"
        >
          {isLoading ? 'Henter data...' : 'Hent Data'}
        </Button>
      </div>
    </Card>
  );
};
