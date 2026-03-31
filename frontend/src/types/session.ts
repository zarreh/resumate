/** Types for job descriptions, sessions, and matching. */

// ---------------------------------------------------------------------------
// JD Analysis
// ---------------------------------------------------------------------------

export interface JDAnalysis {
  role_title: string;
  company_name: string | null;
  seniority_level: string;
  industry: string;
  required_skills: string[];
  preferred_skills: string[];
  ats_keywords: string[];
  tech_stack: string[];
  responsibilities: string[];
  qualifications: string[];
  domain_expectations: string[];
}

export interface JobDescriptionResponse {
  id: string;
  raw_text: string;
  analysis: JDAnalysis | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

export interface SessionResponse {
  id: string;
  job_description_id: string;
  current_gate: string;
  selected_entry_ids: string[];
  context_text: string | null;
  style_preference: string | null;
  analysis: JDAnalysis | null;
  enhanced_resume: EnhancedResume | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Matching
// ---------------------------------------------------------------------------

export interface SkillMatch {
  skill: string;
  matched: boolean;
  matched_by: string[];
}

export interface GapAnalysis {
  unmatched_required: string[];
  unmatched_preferred: string[];
  missing_tech: string[];
}

export interface MatchResult {
  overall_score: number;
  required_skills_score: number;
  preferred_skills_score: number;
  tech_stack_score: number;
  required_matches: SkillMatch[];
  preferred_matches: SkillMatch[];
  tech_matches: SkillMatch[];
  gap_analysis: GapAnalysis;
  recommended_section_order: string[];
}

export interface RankedEntry {
  entry_id: string;
  entry_type: string;
  title: string;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  bullet_points: string[];
  tags: string[];
  source: string;
  similarity_score: number;
}

export interface MatchResponse {
  ranked_entries: RankedEntry[];
  match_result: MatchResult;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export const SENIORITY_LABELS: Record<string, string> = {
  junior: "Junior",
  mid: "Mid-Level",
  senior: "Senior",
  staff: "Staff",
  lead: "Lead",
  principal: "Principal",
  manager: "Manager",
  director: "Director",
  vp: "VP",
  "c-level": "C-Level",
};

export function seniorityLabel(level: string): string {
  return SENIORITY_LABELS[level] || level;
}

// ---------------------------------------------------------------------------
// Enhanced Resume
// ---------------------------------------------------------------------------

export interface EnhancedBullet {
  id: string;
  original_text: string;
  enhanced_text: string;
  source_entry_id: string;
  relevance_score: number;
}

export interface ResumeSectionEntry {
  entry_id: string;
  title: string;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  bullets: EnhancedBullet[];
}

export interface ResumeSection {
  id: string;
  section_type: string;
  title: string;
  entries: ResumeSectionEntry[];
}

export interface EnhancedResume {
  summary: string;
  sections: ResumeSection[];
  skills: string[];
  metadata: Record<string, unknown>;
}

export interface GenerateResponse {
  resume: EnhancedResume;
}
