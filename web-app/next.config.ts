import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactStrictMode: true,
  output: "standalone",
  images: {
    // Card art is loaded straight from Scryfall's CDN instead of through
    // /_next/image. Scryfall rejects requests whose User-Agent is "default
    // or generic" with a 400, and Node's fetch sends "node" - so every
    // optimizer request failed while the same URL loaded fine in a browser,
    // which sends a real User-Agent. The optimizer offers no way to set an
    // upstream header, so there is nothing to configure around it.
    //
    // Serving direct is the better trade here anyway: these are already
    // right-sized JPEGs (~60KB) behind a CDN with a year-long cache-control,
    // so proxying them would spend VPS CPU re-encoding and evict the ISR
    // entries from the size-capped .next/cache for very little saving.
    unoptimized: true,
    // Unused while unoptimized is set, but kept deliberately: it records the
    // one host card art may come from, and is what makes the optimizer legal
    // again if it is ever re-enabled behind a proxy that sets a User-Agent.
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cards.scryfall.io",
      },
    ],
  },
};

export default nextConfig;
