import type { CartItem, MenuItem } from "./types";

export function money(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(amount) + " so'm";
}

export function priceNumber(value: string | number): number {
  return typeof value === "number" ? value : Number(value);
}

export function productMeta(item: Pick<MenuItem, "id" | "name">): { cookTimeMin: number; calories: number } {
  const base = [...item.id].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const lower = item.name.toLowerCase();
  let cookTimeMin = 10 + (base % 12);
  if (lower.includes("tea") || lower.includes("water") || lower.includes("ayran")) cookTimeMin = 4 + (base % 5);
  if (lower.includes("osh") || lower.includes("lagman")) cookTimeMin = 16 + (base % 8);

  let calories = 260 + (base % 360);
  if (lower.includes("water") || lower.includes("tea")) calories = 0;
  if (lower.includes("ayran")) calories = 95;

  return { cookTimeMin, calories };
}

export function estimateCartTime(items: CartItem[], activeOrdersCount = 3): { min: number; max: number; label: string } {
  if (items.length === 0) return { min: 0, max: 0, label: "Taxminan 0 daqiqa" };
  const maxCook = Math.max(...items.map((item) => item.cookTimeMin));
  const queueTime = activeOrdersCount * 2;
  const base = maxCook + queueTime;
  const min = Math.max(5, base - 3);
  const max = base + 3;
  return { min, max, label: `Taxminan ${min}-${max} daqiqa` };
}

export function displayCategoryName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("drink")) return "Ichimliklar";
  if (lower.includes("main")) return "Burgerlar";
  if (lower.includes("dish")) return "Burgerlar";
  return name;
}

export function fallbackFoodImage(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("tea") || lower.includes("water") || lower.includes("ayran")) {
    return "linear-gradient(145deg, #dcfce7, #86efac)";
  }
  if (lower.includes("lagman")) return "linear-gradient(145deg, #fee2e2, #fca5a5)";
  if (lower.includes("manti")) return "linear-gradient(145deg, #fef3c7, #fcd34d)";
  return "linear-gradient(145deg, #f0fdf4, #4ade80)";
}

export function usableImageUrl(url: string | null | undefined): string | null {
  if (!url || url.includes("example.com")) return null;
  return url;
}
