export interface LandingLinks {
  dashboard: string;
  github: string;
  demo: string;
}

export const landingLinks: LandingLinks = {
  dashboard: import.meta.env.VITE_PUBLIC_DASHBOARD_URL || "/overview",
  github: import.meta.env.VITE_PUBLIC_GITHUB_URL || "https://github.com/madgIitch/Mwangaza",
  demo: import.meta.env.VITE_PUBLIC_DEMO_URL || "/overview?demo=1"
};

export function validPublicUrl(value: string): boolean {
  if (value.startsWith("/")) return !value.startsWith("//");
  try { return new URL(value).protocol === "https:"; } catch { return false; }
}
