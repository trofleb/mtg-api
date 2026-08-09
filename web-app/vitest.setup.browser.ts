// Setup for the "browser" Vitest project (real Chromium via Playwright).
//
// The one thing that must not be dropped from this file: the globals.css
// import below. Without it Tailwind v4 never runs, every element renders at
// its unstyled default, and a layout assertion passes or fails for reasons
// that have nothing to do with the component. That is the exact failure mode
// this layer exists to prevent, so `search-form.browser.test.tsx` asserts
// that Tailwind is really applied before it trusts any measurement.
import "./app/globals.css";

import React from "react";
import { vi } from "vitest";

// vi.mock works the same in Browser Mode as in jsdom, so the Next.js mocks
// from vitest.setup.ts carry over unchanged. What does *not* carry over is
// @testing-library/react: its render() does not behave in Browser Mode.
// Browser specs use vitest-browser-react's render + locators instead, and it
// unmounts between tests on its own - hence no cleanup() here.
// ResizeObserver is also omitted: the browser has a real one.

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  })),
  usePathname: vi.fn(() => "/"),
  useSearchParams: vi.fn(() => new URLSearchParams()),
  useParams: vi.fn(() => ({})),
}));

// biome-ignore lint/suspicious/noExplicitAny: mirrors the jsdom setup's mock
type AnyProps = any;

// `__esModule: true` is load-bearing, not boilerplate. next/image and
// next/link are CommonJS, so Vite compiles `import Image from "next/image"`
// through an esbuild interop helper that only unwraps `.default` when the
// module marks itself as ESM. Without the flag the helper hands the importer
// the whole namespace object, and React rejects it with "Element type is
// invalid: ... but got: object".
//
// Nothing caught this before because no browser spec had yet rendered a
// component importing either module - search-form.browser.test.tsx uses
// neither. Found by card-tile.browser.test.tsx.

vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: AnyProps) => React.createElement("img", props),
}));

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href, ...props }: AnyProps) =>
    React.createElement("a", { href, ...props }, children),
}));
