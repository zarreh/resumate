"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { CompanyResearch, JDAnalysis } from "@/types/session";
import { seniorityLabel } from "@/types/session";

interface AnalysisViewProps {
  analysis: JDAnalysis;
  companyResearch?: CompanyResearch | null;
}

export function AnalysisView({ analysis, companyResearch }: AnalysisViewProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold">{analysis.role_title}</h2>
        <div className="mt-1 flex flex-wrap gap-2 text-sm text-muted-foreground">
          {analysis.company_name && <span>{analysis.company_name}</span>}
          {analysis.company_name && <span>&middot;</span>}
          <span>{seniorityLabel(analysis.seniority_level)}</span>
          <span>&middot;</span>
          <span>{analysis.industry}</span>
        </div>
      </div>

      {/* Company Research */}
      {companyResearch && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Company Research
          </h3>
          <div className="space-y-3 text-sm">
            {companyResearch.summary && (
              <p>{companyResearch.summary}</p>
            )}
            {companyResearch.mission && (
              <div>
                <span className="font-medium">Mission: </span>
                {companyResearch.mission}
              </div>
            )}
            {companyResearch.products.length > 0 && (
              <div>
                <span className="font-medium">Products: </span>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {companyResearch.products.map((p) => (
                    <Badge key={p} variant="outline">{p}</Badge>
                  ))}
                </div>
              </div>
            )}
            {companyResearch.culture && (
              <div>
                <span className="font-medium">Culture: </span>
                {companyResearch.culture}
              </div>
            )}
            {companyResearch.recent_news.length > 0 && (
              <div>
                <span className="font-medium">Recent News:</span>
                <ul className="mt-1 list-inside list-disc space-y-0.5">
                  {companyResearch.recent_news.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex flex-wrap gap-4 text-muted-foreground">
              {companyResearch.headquarters && (
                <span>HQ: {companyResearch.headquarters}</span>
              )}
              {companyResearch.size_and_funding && (
                <span>{companyResearch.size_and_funding}</span>
              )}
              {companyResearch.industry && (
                <span>{companyResearch.industry}</span>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Required Skills */}
      {analysis.required_skills.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Required Skills
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {analysis.required_skills.map((skill) => (
              <Badge key={skill} variant="default">
                {skill}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Preferred Skills */}
      {analysis.preferred_skills.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Preferred Skills
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {analysis.preferred_skills.map((skill) => (
              <Badge key={skill} variant="secondary">
                {skill}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Tech Stack */}
      {analysis.tech_stack.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Tech Stack
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {analysis.tech_stack.map((tech) => (
              <Badge key={tech} variant="outline">
                {tech}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Responsibilities */}
      {analysis.responsibilities.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Key Responsibilities
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm">
            {analysis.responsibilities.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Card>
      )}

      {/* Qualifications */}
      {analysis.qualifications.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Qualifications
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm">
            {analysis.qualifications.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </Card>
      )}

      {/* Domain Expectations */}
      {analysis.domain_expectations.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Domain Expectations
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {analysis.domain_expectations.map((d) => (
              <Badge key={d} variant="destructive">
                {d}
              </Badge>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
