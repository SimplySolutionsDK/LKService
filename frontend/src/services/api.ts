import type { 
  PreviewData, 
  EmployeeType, 
  OutputFormat, 
  CallOutSelections, 
  AbsenceSelections,
  EmployeeSearchResponse,
  ApiFetchParams
} from '../types';

export const api = {
  async preview(files: File[], employeeType: EmployeeType): Promise<PreviewData> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('employee_type', employeeType);

    const response = await fetch('/api/preview', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to preview files');
    }

    return response.json();
  },

  async export(
    sessionId: string,
    outputFormat: OutputFormat,
    callOutSelections: CallOutSelections
  ): Promise<Blob> {
    const formData = new FormData();
    formData.append('output_format', outputFormat);
    formData.append('call_out_selections', JSON.stringify(callOutSelections));

    const response = await fetch(`/api/export/${sessionId}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to export data');
    }

    return response.blob();
  },

  async markAbsence(sessionId: string, absenceSelections: AbsenceSelections): Promise<PreviewData> {
    const formData = new FormData();
    formData.append('absence_selections', JSON.stringify(absenceSelections));
    
    const response = await fetch(`/api/mark-absence/${sessionId}`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to mark absence');
    }
    
    return response.json();
  },

  getFilename(response: Response): string {
    const contentDisposition = response.headers.get('Content-Disposition');
    if (contentDisposition) {
      const match = contentDisposition.match(/filename=(.+)/);
      if (match) return match[1];
    }
    return 'time_registration.csv';
  },

  async fetchEmployees(): Promise<EmployeeSearchResponse> {
    const response = await fetch('/api/fetch-employees', {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch employees');
    }

    return response.json();
  },

  async fetchTimeRegistrations(
    params: ApiFetchParams,
    employeeType: EmployeeType
  ): Promise<PreviewData> {
    const formData = new FormData();
    formData.append('employee_id', params.employeeId.toString());
    formData.append('employee_name', params.employeeName);
    formData.append('start_date', params.startDate);
    formData.append('end_date', params.endDate);
    formData.append('employee_type', employeeType);

    const response = await fetch('/api/fetch-from-external', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch time registrations');
    }

    return response.json();
  },
};
