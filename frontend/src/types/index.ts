export interface TimeEntry {
  case_number: string;
  activity: string;
  start_time: string;
  end_time: string;
  total_hours: number;
}

export interface OvertimeBreakdown {
  ot_weekday_hour_1_2: number;
  ot_weekday_hour_3_4: number;
  ot_weekday_hour_5_plus: number;
  ot_saturday_day: number;
  ot_saturday_night: number;
  ot_sunday_before_noon: number;
  ot_sunday_after_noon: number;
}

export interface DailyRecord {
  worker: string;
  date: string;
  day: string;
  day_type: 'Weekday' | 'Saturday' | 'Sunday';
  total_hours: number;
  normal_hours: number;
  overtime_breakdown: OvertimeBreakdown;
  has_call_out_qualifying_time: boolean;
  entries: TimeEntry[];
}

export interface WeeklyRecord {
  worker_name: string;
  year: number;
  week_number: number;
  total_hours: number;
  normal_hours: number;
  overtime_breakdown: OvertimeBreakdown;
}

export interface PreviewData {
  success: boolean;
  session_id: string;
  total_records: number;
  daily: DailyRecord[];
  weekly: WeeklyRecord[];
}

export type EmployeeType = 'Svend' | 'Lærling' | 'Funktionær' | 'Elev';

export type OutputFormat = 'daily' | 'detailed' | 'weekly' | 'weekly_detailed' | 'combined';

export type TabType = 'daily' | 'weekly';

export interface CallOutSelections {
  [date: string]: boolean;
}

export interface StatusMessage {
  type: 'success' | 'error' | 'loading';
  message: string;
}
