import NextAuth, { DefaultSession, DefaultUser, TokenSet } from "next-auth";
import { JWT, DefaultJWT } from "next-auth/jwt";
import ProviderType from "next-auth/providers";

declare module "next-auth" {


interface Account extends Partial<TokenSet> {
  /**
   * This value depends on the type of the provider being used to create the account.
   * - oauth: The OAuth account's id, returned from the `profile()` callback.
   * - email: The user's email address.
   * - credentials: `id` returned from the `authorize()` callback
   */
  providerAccountId: string
  /** id of the user this account belongs to. */
  userId?: string
  /** id of the provider used for this account */
  provider: string
  /** Provider's type for this account */
  type: ProviderType
  loginProvider: any

}




  interface Session extends DefaultSession {
    accessToken?: string;
    idToken?: string;
    error?: string;
    loginProvider?:any;
    provider?: any;
    tenant?: string;
    user: {
      id?: string;
    } & DefaultSession["user"];
  }

  interface User extends DefaultUser {
    // Add any custom user properties if needed from Keycloak profile
  }
}

declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    accessToken?: string;
    idToken?: string;
    refreshToken?: string;
    accessTokenExpires?: number;
    error?: string;
    tenant?: string;
    // Add preferred_username if you expect it from Keycloak token
    preferred_username?: string; 
  }
}
