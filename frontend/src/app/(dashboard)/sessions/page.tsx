"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function SessionsPage() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sessions</h1>
          <p className="text-muted-foreground">
            Manage your resume tailoring sessions.
          </p>
        </div>
        <Button onClick={() => router.push("/dashboard/sessions/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Session
        </Button>
      </div>

      <div className="rounded-lg border border-dashed p-8 text-center">
        <p className="text-muted-foreground">
          No sessions yet. Start a new session by pasting a job description.
        </p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push("/dashboard/sessions/new")}
        >
          <Plus className="mr-2 h-4 w-4" />
          Start New Session
        </Button>
      </div>
    </div>
  );
}
