"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface JDInputProps {
  onSubmit: (text: string) => void;
  loading?: boolean;
}

export function JDInput({ onSubmit, loading = false }: JDInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (trimmed) {
      onSubmit(trimmed);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Paste Job Description</h2>
        <p className="text-sm text-muted-foreground">
          Paste the full job description text below to start a new tailoring
          session.
        </p>
      </div>

      <Textarea
        placeholder="Paste the job description here..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        className="font-mono text-sm"
        disabled={loading}
      />

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          {text.length > 0 ? `${text.length} characters` : ""}
        </span>
        <Button
          onClick={handleSubmit}
          disabled={!text.trim() || loading}
          size="lg"
        >
          {loading ? "Analyzing..." : "Analyze Job Description"}
        </Button>
      </div>
    </div>
  );
}
