export interface TimeEntry {
  case_number: string;
  activity: string;
  start_time: string;
  end_time: string;
  total_hours: number;
  duration_display?: string;  // Optional HH:MM format (e.g., "2:26")
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
  absent_type?: AbsenceType;
  credited_hours?: number;
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

export type AbsenceType = 'None' | 'Vacation' | 'Sick' | 'Kursus';

export interface AbsenceSelections {
  [date: string]: AbsenceType;
}

export interface StatusMessage {
  type: 'success' | 'error' | 'loading';
  message: string;
}

// Employee API response types
export interface SecondaryDepartment {
  branchDepartmentId: number;
  branchOfficeId: number;
  name: string;
  usesOfficeHours: boolean;
}

export interface Employee {
  employeeId: number;
  number: number;
  firstname: string;
  lastname: string;
  telephone: string;
  barCode: string;
  hourPay: number;
  payLineProductNo: string;
  payLineProductText: string;
  payLineCategoryNo: string;
  payLineUnit: string;
  deleted: boolean;
  hideOnPlanner: boolean;
  branchDepartmentId: number;
  nameInitials: string;
  onlineBookingAllowed: boolean;
  secondaryDepartments: SecondaryDepartment[];
  plannerSortOrder: number;
}

export interface EmployeeSearchResponse {
  totalCount: number;
  results: Employee[];
}

// Time Registration API response types
export interface TimeRegistration {
  timeRegistrationId: number;
  employeeId: number;
  caseId: number;
  caseNo: number;
  registrationTypeId: number;
  plannerAppointmentId: number | null;
  comments: string | null;
  isUpdated: boolean;
  startTimeUtc: string;
  endTimeUtc: string;
  elapsedMinutes: number;
  elapsedHours: number;
}

export interface TimeRegistrationResponse {
  totalCount: number;
  results: TimeRegistration[];
}

// API fetch params
export interface ApiFetchParams {
  employeeId: number;
  employeeName: string;
  startDate: string;
  endDate: string;
}
