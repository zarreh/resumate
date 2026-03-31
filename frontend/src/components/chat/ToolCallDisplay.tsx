"use client";

import type { ToolCallInfo } from "@/types/chat";
import { Wrench } from "lucide-react";

interface ToolCallDisplayProps {
  toolCalls: ToolCallInfo[];
}

export default function ToolCallDisplay({ toolCalls }: ToolCallDisplayProps) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-1.5">
      {toolCalls.map((tc, idx) => (
        <span
          key={idx}
          className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
        >
          <Wrench className="h-3 w-3" />
          {tc.name}
        </span>
      ))}
    </div>
  );
}
