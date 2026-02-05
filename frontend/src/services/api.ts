import type { PreviewData, EmployeeType, OutputFormat, CallOutSelections } from '../types';

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

  getFilename(response: Response): string {
    const contentDisposition = response.headers.get('Content-Disposition');
    if (contentDisposition) {
      const match = contentDisposition.match(/filename=(.+)/);
      if (match) return match[1];
    }
    return 'time_registration.csv';
  },
};
