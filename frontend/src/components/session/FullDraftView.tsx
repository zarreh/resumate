"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SectionView } from "@/components/session/SectionView";
import { SkillsEditor } from "@/components/session/SkillsEditor";
import type { EnhancedResume } from "@/types/session";

interface FullDraftViewProps {
  resume: EnhancedResume;
  bulletStatuses?: Record<string, "pending" | "approved" | "rejected">;
  showControls?: boolean;
  onBulletApprove?: (bulletId: string) => void;
  onBulletReject?: (bulletId: string) => void;
  onBulletEdit?: (bulletId: string, text: string) => void;
  onSkillsChange?: (skills: string[]) => void;
}

export function FullDraftView({
  resume,
  bulletStatuses = {},
  showControls = false,
  onBulletApprove,
  onBulletReject,
  onBulletEdit,
  onSkillsChange,
}: FullDraftViewProps) {
  const totalBullets = resume.sections.reduce(
    (acc, s) => acc + s.entries.reduce((a, e) => a + e.bullets.length, 0),
    0
  );

  return (
    <div className="space-y-6">
      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Professional Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{resume.summary}</p>
        </CardContent>
      </Card>

      {/* Stats bar */}
      <div className="flex items-center gap-6 text-sm text-muted-foreground">
        <span>{resume.sections.length} sections</span>
        <span>{totalBullets} bullets</span>
        <span>{resume.skills.length} skills</span>
      </div>

      {/* Sections */}
      {resume.sections.map((section) => (
        <SectionView
          key={section.id}
          section={section}
          bulletStatuses={bulletStatuses}
          showControls={showControls}
          onBulletApprove={onBulletApprove}
          onBulletReject={onBulletReject}
          onBulletEdit={onBulletEdit}
        />
      ))}

      {/* Skills */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skills</CardTitle>
        </CardHeader>
        <CardContent>
          <SkillsEditor
            skills={resume.skills}
            onChange={onSkillsChange || (() => {})}
            readOnly={!onSkillsChange}
          />
        </CardContent>
      </Card>
    </div>
  );
}
