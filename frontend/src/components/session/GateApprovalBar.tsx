"use client";

import { Button } from "@/components/ui/button";

interface GateApprovalBarProps {
  onApprove: () => void;
  loading?: boolean;
  disabled?: boolean;
  label?: string;
}

export function GateApprovalBar({
  onApprove,
  loading = false,
  disabled = false,
  label = "Approve & Continue",
}: GateApprovalBarProps) {
  return (
    <div className="sticky bottom-0 border-t bg-background px-6 py-4">
      <div className="flex items-center justify-end">
        <Button
          onClick={onApprove}
          disabled={disabled || loading}
          size="lg"
        >
          {loading ? "Processing..." : label}
        </Button>
      </div>
    </div>
  );
}
