# OAuth Callback Page (`/token/callback/oauth_providers/[provider]`)

This page serves as the callback endpoint for the OAuth 2.0 authentication flow. After a user successfully authenticates with an external provider (e.g., GitHub, Google), the provider redirects them back to this page.

## Key Functionality

-   **Handles OAuth Redirect**: This is the designated `callbackUrl` where the user lands after external authentication.
-   **Finalizes Token Exchange**: On page load, it triggers a backend process to finalize the token exchange and securely store the provider's credentials (e.g., access tokens) for the user's agent.
-   **Provides User Feedback**: It informs the user about the status of the operation (success or failure) and instructs them to close the window upon completion.

## State Management

The `AuthCallbackContent` component manages the following state:

-   `providerName: string`: The name of the OAuth provider, extracted from the URL path (`[provider]`).
-   `message: string`: A status message displayed to the user (e.g., "Processing callback...", "Successfully updated credentials...").
-   `isError: boolean`: A flag that indicates if an error occurred during the process.

## Actions and Effects

-   **`useEffect` Hook**: The component's primary logic resides in a `useEffect` hook.
    1.  It waits for the `agentData` (containing `agent_id` and `tenant_name`) to be loaded via the `useAgentData` hook.
    2.  Once the necessary data is available, it calls the `updateProvider` API function. This function sends the provider name, agent ID, and tenant name to the backend, which then completes the credential update process.
    3.  It handles success and error responses from the API, updating the `message` and `isError` state to provide clear feedback to the user.

## Dependencies

-   **`@/lib/apiClient`**: Uses the `updateProvider` function to communicate with the backend API.
-   **`@/lib/contexts/AgentDataContext`**: Relies on the `useAgentData` hook to get essential user and agent information required for the API call.
