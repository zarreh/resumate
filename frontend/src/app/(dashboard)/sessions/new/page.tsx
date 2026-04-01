"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { JDInput } from "@/components/session/JDInput";
import { startSession } from "@/lib/api/session";

export default function NewSessionPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (params: { text?: string; url?: string }) => {
    setLoading(true);
    try {
      const session = await startSession(params);
      toast.success("Job description analyzed successfully");
      router.push(`/sessions/${session.id}/analysis`);
    } catch {
      toast.error("Failed to analyze job description");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New Session</h1>
        <p className="text-muted-foreground">
          Start a new resume tailoring session by pasting a job description or
          providing a URL.
        </p>
      </div>
      <JDInput onSubmit={handleSubmit} loading={loading} />
    </div>
  );
}
