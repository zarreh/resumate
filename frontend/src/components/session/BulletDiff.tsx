"use client";

import { cn } from "@/lib/utils";

interface BulletDiffProps {
  original: string;
  enhanced: string;
}

/**
 * Simple word-level diff display between original and enhanced bullet text.
 * Green = added, Red = removed, normal = unchanged.
 */
export function BulletDiff({ original, enhanced }: BulletDiffProps) {
  const diff = computeWordDiff(original, enhanced);

  return (
    <div className="space-y-2 text-sm">
      <div>
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Original
        </span>
        <p className="mt-1 text-muted-foreground">{original}</p>
      </div>
      <div>
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Enhanced
        </span>
        <p className="mt-1">
          {diff.map((part, i) => (
            <span
              key={i}
              className={cn(
                part.type === "added" &&
                  "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
                part.type === "removed" &&
                  "bg-red-100 text-red-800 line-through dark:bg-red-900/30 dark:text-red-300"
              )}
            >
              {part.text}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Simple word-level diff (no external dependency)
// ---------------------------------------------------------------------------

interface DiffPart {
  type: "unchanged" | "added" | "removed";
  text: string;
}

function computeWordDiff(original: string, enhanced: string): DiffPart[] {
  const origWords = original.split(/(\s+)/);
  const enhWords = enhanced.split(/(\s+)/);

  // LCS-based diff
  const m = origWords.length;
  const n = enhWords.length;

  // Build LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    new Array<number>(n + 1).fill(0)
  );

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origWords[i - 1] === enhWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to build diff
  const parts: DiffPart[] = [];
  let i = m;
  let j = n;

  const stack: DiffPart[] = [];
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origWords[i - 1] === enhWords[j - 1]) {
      stack.push({ type: "unchanged", text: origWords[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      stack.push({ type: "added", text: enhWords[j - 1] });
      j--;
    } else {
      stack.push({ type: "removed", text: origWords[i - 1] });
      i--;
    }
  }

  // Reverse (we built it backwards) and merge adjacent same-type parts
  stack.reverse();
  for (const part of stack) {
    const last = parts[parts.length - 1];
    if (last && last.type === part.type) {
      last.text += part.text;
    } else {
      parts.push({ ...part });
    }
  }

  return parts;
}
