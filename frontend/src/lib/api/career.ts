import { apiClient, getAccessToken } from "@/lib/api";
import type {
  CareerEntry,
  CareerEntryCreate,
  CareerEntryUpdate,
  ImportResponse,
} from "@/types/career";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function listEntries(): Promise<CareerEntry[]> {
  return apiClient<CareerEntry[]>("/api/v1/career/entries");
}

export async function getEntry(id: string): Promise<CareerEntry> {
  return apiClient<CareerEntry>(`/api/v1/career/entries/${id}`);
}

export async function createEntry(
  data: CareerEntryCreate,
): Promise<CareerEntry> {
  return apiClient<CareerEntry>("/api/v1/career/entries", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateEntry(
  id: string,
  data: CareerEntryUpdate,
): Promise<CareerEntry> {
  return apiClient<CareerEntry>(`/api/v1/career/entries/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteEntry(id: string): Promise<void> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE}/api/v1/career/entries/${id}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new Error("Failed to delete entry");
  }
}

export async function confirmAllEntries(): Promise<{ confirmed: number }> {
  return apiClient<{ confirmed: number }>("/api/v1/career/entries/confirm-all", {
    method: "POST",
  });
}

export async function uploadResume(file: File): Promise<ImportResponse> {
  const token = getAccessToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/career/import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Upload failed");
  }

  return res.json() as Promise<ImportResponse>;
}
