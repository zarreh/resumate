export interface CareerEntry {
  id: string;
  entry_type: string;
  title: string;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  bullet_points: string[];
  tags: string[];
  source: string;
  raw_text: string | null;
}

export interface CareerEntryCreate {
  entry_type: string;
  title: string;
  organization?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  bullet_points?: string[];
  tags?: string[];
  raw_text?: string | null;
}

export interface CareerEntryUpdate {
  entry_type?: string;
  title?: string;
  organization?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  bullet_points?: string[];
  tags?: string[];
  source?: string;
}

export interface ImportResponse {
  filename: string;
  content_type: string;
  text: string;
  char_count: number;
}

export interface ParsedBulletPoint {
  text: string;
  tags: string[];
}

export interface ParsedResumeEntry {
  entry_type: string;
  title: string;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  bullet_points: ParsedBulletPoint[];
  tags: string[];
  raw_text: string | null;
}

export interface ParsedResumeResponse {
  entries: ParsedResumeEntry[];
  entry_count: number;
}

export const ENTRY_TYPES = [
  { value: "work_experience", label: "Work Experience" },
  { value: "education", label: "Education" },
  { value: "project", label: "Project" },
  { value: "certification", label: "Certification" },
  { value: "volunteer", label: "Volunteer" },
] as const;

export function entryTypeLabel(type: string): string {
  return ENTRY_TYPES.find((t) => t.value === type)?.label ?? type;
}
