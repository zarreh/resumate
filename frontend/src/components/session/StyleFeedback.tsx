"use client";

import { Textarea } from "@/components/ui/textarea";

interface StyleFeedbackProps {
  value: string;
  onChange: (value: string) => void;
}

export function StyleFeedback({ value, onChange }: StyleFeedbackProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Style & Tone Feedback
      </h3>
      <p className="text-sm text-muted-foreground">
        Review the sample bullets above and provide feedback on the writing
        style. Your feedback will be applied to all remaining bullets.
      </p>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g., Keep bullets shorter and more technical. Use stronger action verbs. Less corporate jargon..."
        rows={4}
        className="resize-none"
      />
    </div>
  );
}
