import type { MetadataRoute } from "next";

// Deployed origin, used to make the sitemap reference absolute - the sitemap
// protocol requires fully-qualified <loc> URLs, so a relative path is not an
// option. Kept as a literal default rather than a required env var so that a
// bare `next build` (Tier A, no API and no .env) still produces a valid
// document instead of failing or emitting "undefined/sitemap.xml".
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://mtg.nicocasa.ch";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
