"use client";

import { Loader2 } from "lucide-react";

interface ThinkingIndicatorProps {
  label?: string;
}

export default function ThinkingIndicator({
  label = "Thinking...",
}: ThinkingIndicatorProps) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>{label}</span>
    </div>
  );
}
