import type { MetadataRoute } from "next";

// See app/robots.ts for why this is a literal default rather than a required
// environment variable.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://mtg.nicocasa.ch";

// Only the search entry point is listed. Card pages are deliberately absent:
// enumerating them means querying the API at build time, and the whole point
// of this route being Tier A is that it renders with no API, no database and
// no stub. A card sitemap belongs behind a real crawl budget decision anyway -
// there are tens of thousands of oracle ids and none of them changes often.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1,
    },
  ];
}
