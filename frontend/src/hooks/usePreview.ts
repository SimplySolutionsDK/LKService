import { useState, useCallback } from 'react';
import type { 
  PreviewData, 
  TabType, 
  OutputFormat, 
  CallOutSelections, 
  StatusMessage, 
  EmployeeType 
} from '../types';
import { api } from '../services/api';

export const usePreview = () => {
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('daily');
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('daily');
  const [callOutSelections, setCallOutSelections] = useState<CallOutSelections>({});
  const [status, setStatus] = useState<StatusMessage | undefined>();
  const [isLoading, setIsLoading] = useState(false);

  const loadPreview = useCallback(async (files: File[], employeeType: EmployeeType) => {
    setIsLoading(true);
    setStatus({ type: 'loading', message: 'Behandler filer...' });

    try {
      const data = await api.preview(files, employeeType);
      setPreviewData(data);
      setCallOutSelections({});
      setStatus({
        type: 'success',
        message: `✓ ${data.total_records} registreringer behandlet fra ${files.length} fil(er)`,
      });
      
      // Scroll to preview after a short delay
      setTimeout(() => {
        const previewCard = document.querySelector('.preview-card');
        if (previewCard) {
          previewCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    } catch (error) {
      setStatus({
        type: 'error',
        message: `✕ Fejl: ${error instanceof Error ? error.message : 'Ukendt fejl'}`,
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const exportData = useCallback(async () => {
    if (!previewData?.session_id) {
      setStatus({ type: 'error', message: '✕ Ingen data at eksportere. Upload filer først.' });
      return;
    }

    try {
      const response = await fetch(`/api/export/${previewData.session_id}`, {
        method: 'POST',
        body: (() => {
          const formData = new FormData();
          formData.append('output_format', outputFormat);
          formData.append('call_out_selections', JSON.stringify(callOutSelections));
          return formData;
        })(),
      });

      if (response.ok) {
        const blob = await response.blob();
        const filename = api.getFilename(response);

        // Trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        setStatus({ type: 'success', message: `✓ Download startet: ${filename}` });
      } else {
        const error = await response.json();
        setStatus({ type: 'error', message: `✕ Fejl: ${error.detail || 'Ukendt fejl'}` });
      }
    } catch (error) {
      setStatus({
        type: 'error',
        message: `✕ Fejl: ${error instanceof Error ? error.message : 'Ukendt fejl'}`,
      });
    }
  }, [previewData, outputFormat, callOutSelections]);

  const updateCallOutSelection = useCallback((date: string, checked: boolean) => {
    setCallOutSelections(prev => ({ ...prev, [date]: checked }));
  }, []);

  const clearPreview = useCallback(() => {
    setPreviewData(null);
    setCallOutSelections({});
    setStatus(undefined);
  }, []);

  return {
    previewData,
    activeTab,
    outputFormat,
    callOutSelections,
    status,
    isLoading,
    setActiveTab,
    setOutputFormat,
    loadPreview,
    exportData,
    updateCallOutSelection,
    clearPreview,
  };
};
