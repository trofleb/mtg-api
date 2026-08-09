import type { NextConfig } from "next";

// Content-Security-Policy. Deliberately not nonce-based: a nonce has to be
// minted per request in middleware, which forces every route out of the
// static/ISR caches the card page exists to use. The trade is that inline
// script and style stay allowed, so this policy is a defence-in-depth layer
// (it constrains where content may come *from*) rather than XSS-proof.
//
// What actually needs the allowances, all verified against a production
// build's HTML:
//   script-src 'unsafe-inline'  the RSC payload ships as `self.__next_f.push`
//                               inline <script> blocks on every page
//   style-src  'unsafe-inline'  next/font injects a <style> block, and Next's
//                               built-in error pages inline their whole CSS
//   img-src    cards.scryfall.io  images.unoptimized is set, so card art is
//                               fetched by the browser straight from the CDN
//   font-src   'self'          next/font/google self-hosts into /_next/static
const contentSecurityPolicy = [
  "default-src 'self'",
  // 'unsafe-eval' is dev-only: Turbopack's HMR runtime evaluates modules.
  // A production build never needs it, so it is not granted there.
  `script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === "production" ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://cards.scryfall.io",
  "font-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  // The one that matters. http:// is answered with a 301, so without HSTS the
  // first request of every session still goes out in the clear and is
  // interceptable before the redirect is ever seen. Not testable below the
  // HTTP layer - it applies before any document exists to run a test inside.
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  // Redundant with frame-ancestors above for modern browsers, kept for the
  // ones that only understand this.
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
];

const nextConfig: NextConfig = {
  /* config options here */
  reactStrictMode: true,
  output: "standalone",
  // Stops advertising the framework and its presence on every response.
  poweredByHeader: false,
  async headers() {
    // Matched by source pattern, not by whether a React tree rendered - so
    // this covers /robots.txt, /favicon.ico and /_next/static as well as
    // real pages, and is assertable without an API behind it.
    return [{ source: "/:path*", headers: securityHeaders }];
  },
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
