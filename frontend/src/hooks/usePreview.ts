import { useState, useCallback } from 'react';
import type {
  PreviewData,
  TabType,
  OutputFormat,
  CallOutSelections,
  AbsenceSelections,
  AbsenceType,
  StatsOverrides,
  StatusMessage,
  EmployeeType,
  ApiFetchParams,
} from '../types';
import { api } from '../services/api';

export const usePreview = () => {
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('daily');
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('daily');
  const [callOutSelections, setCallOutSelections] = useState<CallOutSelections>({});
  const [absenceSelections, setAbsenceSelections] = useState<AbsenceSelections>({});
  const [statsOverrides, setStatsOverrides] = useState<StatsOverrides>({});
  const [status, setStatus] = useState<StatusMessage | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isHalfSickLoading, setIsHalfSickLoading] = useState(false);

  const loadPreview = useCallback(async (files: File[], employeeType: EmployeeType) => {
    setIsLoading(true);
    setStatus({ type: 'loading', message: 'Behandler filer...' });

    try {
      const data = await api.preview(files, employeeType);
      setPreviewData(data);
      setCallOutSelections({});
      setAbsenceSelections({});
      setStatsOverrides({});
      setStatus({
        type: 'success',
        message: `✓ ${data.total_records} registreringer behandlet fra ${files.length} fil(er)`,
      });

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
      if (Object.keys(statsOverrides).length > 0) {
        await api.saveStatsOverrides(previewData.session_id, statsOverrides);
      }

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
  }, [previewData, outputFormat, callOutSelections, statsOverrides]);

  const updateCallOutSelection = useCallback((date: string, checked: boolean) => {
    setCallOutSelections(prev => ({ ...prev, [date]: checked }));
  }, []);

  const updateAbsenceSelection = useCallback(async (date: string, absenceType: AbsenceType) => {
    const newSelections = { ...absenceSelections, [date]: absenceType };
    setAbsenceSelections(newSelections);

    if (previewData?.session_id) {
      try {
        const updatedData = await api.markAbsence(previewData.session_id, newSelections);
        setPreviewData(updatedData);
      } catch (error) {
        setStatus({
          type: 'error',
          message: `✕ Fejl ved opdatering: ${error instanceof Error ? error.message : 'Ukendt fejl'}`,
        });
      }
    }
  }, [absenceSelections, previewData]);

  const applyHalfSickDay = useCallback(async (date: string) => {
    if (!previewData?.session_id) return;

    setIsHalfSickLoading(true);
    try {
      const updatedData = await api.markHalfSickDay(previewData.session_id, date);
      setPreviewData(updatedData);
      setStatus({ type: 'success', message: `✓ Halv sygedag tilføjet for ${date}` });
    } catch (error) {
      setStatus({
        type: 'error',
        message: `✕ Fejl ved halv sygedag: ${error instanceof Error ? error.message : 'Ukendt fejl'}`,
      });
    } finally {
      setIsHalfSickLoading(false);
    }
  }, [previewData]);

  const updateStatsOverride = useCallback(
    (field: keyof StatsOverrides, value: number) => {
      setStatsOverrides(prev => ({ ...prev, [field]: value }));
    },
    []
  );

  const resetStatsOverride = useCallback(
    (field: keyof StatsOverrides) => {
      setStatsOverrides(prev => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const loadPreviewFromApi = useCallback(async (params: ApiFetchParams, employeeType: EmployeeType) => {
    setIsLoading(true);
    setStatus({ type: 'loading', message: 'Henter data fra API...' });

    try {
      const data = await api.fetchTimeRegistrations(params, employeeType);
      setPreviewData(data);
      setCallOutSelections({});
      setAbsenceSelections({});
      setStatsOverrides({});
      setStatus({
        type: 'success',
        message: `✓ ${data.total_records} registreringer hentet for ${params.employeeName}`,
      });

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

  const clearPreview = useCallback(() => {
    setPreviewData(null);
    setCallOutSelections({});
    setAbsenceSelections({});
    setStatsOverrides({});
    setStatus(undefined);
  }, []);

  return {
    previewData,
    activeTab,
    outputFormat,
    callOutSelections,
    absenceSelections,
    statsOverrides,
    status,
    isLoading,
    isHalfSickLoading,
    setActiveTab,
    setOutputFormat,
    loadPreview,
    loadPreviewFromApi,
    exportData,
    updateCallOutSelection,
    updateAbsenceSelection,
    applyHalfSickDay,
    updateStatsOverride,
    resetStatsOverride,
    clearPreview,
  };
};
