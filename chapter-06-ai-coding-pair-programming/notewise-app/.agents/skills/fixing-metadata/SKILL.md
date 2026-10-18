---
name: fixing-metadata
description: "Inspect, fix, and verify Next.js SEO metadata including page titles, descriptions, canonical URLs, Open Graph, Twitter cards, robots, and metadataBase in the App Router."
---

# Fixing Next.js Metadata

## When to Use
- Auditing or implementing SEO metadata for a Next.js route or application.
- Fixing incorrect titles, descriptions, canonical links, Open Graph images, or social previews.
- Working with the App Router Metadata API or `generateMetadata`.

## Procedure
1. Identify whether the route uses the App Router or Pages Router. Inspect root layouts, route layouts/pages, existing metadata helpers, environment configuration, and canonical URL policy.
2. Use the framework's typed Metadata API for App Router routes. Set shared defaults in the root layout and only override fields that are page-specific.
3. Provide a concise, accurate title and description that describe the actual page. Use a stable `metadataBase` from the configured public site URL so relative canonical and image URLs resolve correctly.
4. Set canonical URLs intentionally and consistently. Do not derive public URLs from untrusted request headers or point private, authenticated, duplicate, or non-production routes at an incorrect canonical.
5. Configure Open Graph title, description, URL, site name, locale, and image with valid absolute or correctly resolved URLs and appropriate dimensions/alt text. Configure Twitter card metadata consistently where needed.
6. Add robots directives only when the route's intended indexing policy is known. Do not expose secrets, private user content, or dynamic document titles in public metadata.
7. Verify generated HTML/head metadata for the target route and run the frontend type check, linter, and production build. Check that metadata is not duplicated or accidentally replaced by nested layouts.

## Constraints
- Keep metadata server-side and use framework-supported APIs; do not add client-side effects to populate SEO tags.
- Avoid keyword stuffing, placeholder copy, and invented social preview assets or URLs.
- Preserve existing layout behavior while making focused metadata changes.
