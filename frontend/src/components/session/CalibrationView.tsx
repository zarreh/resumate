"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BulletDiff } from "@/components/session/BulletDiff";
import type { EnhancedResume } from "@/types/session";

interface CalibrationViewProps {
  resume: EnhancedResume;
}

/**
 * Displays the calibration preview — summary + first 2-3 sample bullets
 * with word-level diffs against originals.
 */
export function CalibrationView({ resume }: CalibrationViewProps) {
  // Collect all bullets across sections, take first 3
  const allBullets = resume.sections.flatMap((s) =>
    s.entries.flatMap((e) =>
      e.bullets.map((b) => ({
        ...b,
        sectionTitle: s.title,
        entryTitle: e.title,
      }))
    )
  );
  const sampleBullets = allBullets.slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Summary Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Professional Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{resume.summary}</p>
        </CardContent>
      </Card>

      {/* Sample Bullets */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Sample Enhanced Bullets ({sampleBullets.length})
        </h3>

        {sampleBullets.map((bullet) => (
          <Card key={bullet.id}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">
                  {bullet.entryTitle}
                </CardTitle>
                <span className="text-xs text-muted-foreground">
                  {bullet.sectionTitle}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <BulletDiff
                original={bullet.original_text}
                enhanced={bullet.enhanced_text}
              />
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  Relevance:
                </span>
                <span
                  className={`text-xs font-medium ${
                    bullet.relevance_score >= 0.8
                      ? "text-green-600"
                      : bullet.relevance_score >= 0.5
                        ? "text-yellow-600"
                        : "text-red-600"
                  }`}
                >
                  {Math.round(bullet.relevance_score * 100)}%
                </span>
              </div>
            </CardContent>
          </Card>
        ))}

        {allBullets.length > 3 && (
          <p className="text-sm text-muted-foreground">
            +{allBullets.length - 3} more bullets will be generated with the
            same style after approval.
          </p>
        )}
      </div>

      {/* Skills Preview */}
      {resume.skills.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Skills</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {resume.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full bg-muted px-3 py-1 text-xs font-medium"
                >
                  {skill}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
