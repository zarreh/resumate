"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BulletCard } from "@/components/session/BulletCard";
import type { DiffMode } from "@/components/session/BulletDiff";
import type { ResumeSection, ReviewAnnotation } from "@/types/session";

interface SectionViewProps {
  section: ResumeSection;
  bulletStatuses?: Record<string, "pending" | "approved" | "rejected">;
  annotations?: Record<string, ReviewAnnotation[]>;
  diffMode?: DiffMode;
  changesOnly?: boolean;
  showControls?: boolean;
  onBulletApprove?: (bulletId: string) => void;
  onBulletReject?: (bulletId: string) => void;
  onBulletEdit?: (bulletId: string, text: string) => void;
}

export function SectionView({
  section,
  bulletStatuses = {},
  annotations = {},
  diffMode = "unified",
  changesOnly = false,
  showControls = false,
  onBulletApprove,
  onBulletReject,
  onBulletEdit,
}: SectionViewProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{section.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {section.entries.map((entry) => (
          <div key={entry.entry_id} className="space-y-3">
            {/* Entry header */}
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-semibold">{entry.title}</h4>
                {entry.organization && (
                  <p className="text-sm text-muted-foreground">
                    {entry.organization}
                  </p>
                )}
              </div>
              {(entry.start_date || entry.end_date) && (
                <span className="text-sm text-muted-foreground">
                  {entry.start_date || ""}
                  {entry.start_date && entry.end_date ? " — " : ""}
                  {entry.end_date || "Present"}
                </span>
              )}
            </div>

            {/* Bullets */}
            <div className="space-y-3">
              {entry.bullets
                .filter(
                  (bullet) =>
                    !changesOnly ||
                    bullet.original_text !== bullet.enhanced_text
                )
                .map((bullet) => (
                <BulletCard
                  key={bullet.id}
                  bullet={bullet}
                  status={bulletStatuses[bullet.id] || "pending"}
                  annotations={annotations[bullet.id] || []}
                  diffMode={diffMode}
                  showControls={showControls}
                  onApprove={
                    onBulletApprove
                      ? () => onBulletApprove(bullet.id)
                      : undefined
                  }
                  onReject={
                    onBulletReject
                      ? () => onBulletReject(bullet.id)
                      : undefined
                  }
                  onEdit={
                    onBulletEdit
                      ? (text) => onBulletEdit(bullet.id, text)
                      : undefined
                  }
                />
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
