"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { getSession } from "@/lib/api/session";

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const sessionId = params.id as string;

  useEffect(() => {
    async function redirect() {
      try {
        const session = await getSession(sessionId);
        // Route to the current gate page
        const gate = session.current_gate;
        if (gate === "analysis") {
          router.replace(`/dashboard/sessions/${sessionId}/analysis`);
        } else if (gate === "calibration") {
          router.replace(`/dashboard/sessions/${sessionId}/calibration`);
        } else if (gate === "review") {
          router.replace(`/dashboard/sessions/${sessionId}/review`);
        } else if (gate === "final") {
          router.replace(`/dashboard/sessions/${sessionId}/final`);
        } else {
          router.replace(`/dashboard/sessions/${sessionId}/analysis`);
        }
      } catch {
        toast.error("Failed to load session");
        router.replace("/dashboard/sessions");
      } finally {
        setLoading(false);
      }
    }
    redirect();
  }, [sessionId, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading session...</p>
      </div>
    );
  }

  return null;
}
