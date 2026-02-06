import { OAuthConfig, OAuthUserConfig } from "next-auth/providers/oauth";

// Define the user profile structure we expect from Keycloak
export interface KeycloakProfile extends Record<string, any> {
  exp: number;
  iat: number;
  auth_time: number;
  jti: string;
  iss: string;
  aud: string;
  sub: string;
  typ: string;
  azp: string;
  session_state: string;
  at_hash: string;
  acr: string;
  sid: string;
  email_verified: boolean;
  name: string;
  preferred_username: string;
  given_name: string;
  family_name: string;
  email: string;
}

// Create the custom Keycloak provider
export function CustomKeycloakProvider<P extends KeycloakProfile>(options: any): OAuthConfig<P> {

  return {
    id: "keycloak",
    name: "Keycloak",
    type: "oauth",
    wellKnown: undefined, // Disable OIDC discovery
    
    
    // Map the Keycloak profile to the NextAuth user object
    profile(profile) {
      return {
        id: profile.sub,
        name: profile.name ?? profile.preferred_username,
        email: profile.email,
        image: null, // Keycloak doesn't provide an image URL by default
      };
    },
    ...options,
  };
}
