import type { CurrentListItem, CurrentListPage } from "../models/api";
import type { CurrentListFilters } from "../api/client";

export interface ImportedCurrentList {
  version: 1;
  season: string;
  fileName: string;
  fileHash: string;
  importedAt: string;
  items: CurrentListItem[];
}

const STORAGE_KEY = "fantalab-current-list-import";

export function filterCurrentList(items: CurrentListItem[], filters: CurrentListFilters = {}): CurrentListPage {
  let filtered = [...items];
  if (filters.search) filtered = filtered.filter((item) => item.name.toLocaleLowerCase("it").includes(filters.search!.toLocaleLowerCase("it")));
  if (filters.role) filtered = filtered.filter((item) => item.classic_role === filters.role);
  if (filters.team) filtered = filtered.filter((item) => item.team.toLocaleLowerCase("it") === filters.team!.toLocaleLowerCase("it"));
  if (filters.mappingStatus) filtered = filtered.filter((item) => item.mapping_status === filters.mappingStatus);
  if (filters.minQuotation !== undefined) filtered = filtered.filter((item) => (item.quotation ?? -1) >= filters.minQuotation!);
  if (filters.maxQuotation !== undefined) filtered = filtered.filter((item) => (item.quotation ?? Infinity) <= filters.maxQuotation!);
  const key = filters.sortBy ?? "quotation";
  filtered.sort((a, b) => {
    const av = (a as unknown as Record<string, string | number | null>)[key];
    const bv = (b as unknown as Record<string, string | number | null>)[key];
    const result = typeof av === "string" ? av.localeCompare(String(bv), "it") : Number(av ?? -Infinity) - Number(bv ?? -Infinity);
    return filters.sortOrder === "asc" ? result : -result;
  });
  const page = filters.page ?? 1;
  const pageSize = filters.pageSize ?? 25;
  return { items: filtered.slice((page - 1) * pageSize, page * pageSize), page, page_size: pageSize, total_items: filtered.length, total_pages: filtered.length ? Math.ceil(filtered.length / pageSize) : 0 };
}

export const currentListStore = {
  get(): ImportedCurrentList | null {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as ImportedCurrentList | null;
      return parsed?.version === 1 && Array.isArray(parsed.items) ? parsed : null;
    } catch { return null; }
  },
  save(value: ImportedCurrentList) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    window.dispatchEvent(new Event("fantalab-current-list-updated"));
  },
  remove() {
    localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new Event("fantalab-current-list-updated"));
  }
};
