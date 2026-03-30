"use client";

import { useAuth } from "@/context/AuthProvider";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {user?.name}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-border p-6">
          <h3 className="font-medium">Career History</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your work experience, education, and skills
          </p>
        </div>
        <div className="rounded-lg border border-border p-6">
          <h3 className="font-medium">Sessions</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Start a new resume tailoring session
          </p>
        </div>
        <div className="rounded-lg border border-border p-6">
          <h3 className="font-medium">Chat</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Talk to the AI about your career history
          </p>
        </div>
      </div>
    </div>
  );
}
