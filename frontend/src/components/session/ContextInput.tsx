"use client";

import { Textarea } from "@/components/ui/textarea";

interface ContextInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function ContextInput({ value, onChange }: ContextInputProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Additional Context
      </h3>
      <p className="text-sm text-muted-foreground">
        Add any missing context that the AI should know about (e.g., specific
        achievements, domain expertise, or context not in your career history).
      </p>
      <Textarea
        placeholder="e.g., I led a team of 5 engineers at my last role but it's not reflected in my resume..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
      />
    </div>
  );
}
