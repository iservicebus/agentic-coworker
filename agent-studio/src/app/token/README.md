# Token Route Layout (`/token/layout.tsx`)

This layout component serves as a wrapper for all pages within the `/token/*` route segment.

## Primary Purpose: Authentication Enforcement

The main responsibility of this layout is to enforce authentication using the `<AuthGuard>` component.

-   **`AuthGuard`**: This component wraps all child routes (e.g., `/token/start/...` and `/token/callback/...`). It checks if the user is currently authenticated with the application. If the user is not logged in, the `AuthGuard` will typically redirect them to a login page, preventing unauthenticated access to the OAuth flow pages.

This ensures that only logged-in users can attempt to link external OAuth provider accounts.
