import KeycloakProvider from "next-auth/providers/keycloak";
import GoogleProvider from 'next-auth/providers/google';
import GitHubProvider from 'next-auth/providers/github';
import { CustomLinkedInProvider } from "@/lib/providers/customLinkedInProvider";
import { CustomKeycloakProvider } from "@/lib/providers/customAuthProvider";
import { CustomServiceNowProvider } from "@/lib/providers/customServiceNowProvider";

export const providerMap = {
  keycloak: CustomKeycloakProvider,
  google: GoogleProvider,
  linkedin: CustomLinkedInProvider,
  github: GitHubProvider,
  servicenow: CustomServiceNowProvider,
};
