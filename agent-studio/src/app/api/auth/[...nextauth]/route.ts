import NextAuth, { NextAuthOptions, getServerSession} from "next-auth";

import { NextResponse } from "next/server";

import GoogleProvider from 'next-auth/providers/google';
import GitHubProvider from 'next-auth/providers/github';
import { CustomLinkedInProvider } from "@/lib/providers/customLinkedInProvider";
import { CustomKeycloakProvider } from "@/lib/providers/customAuthProvider";
import { CustomServiceNowProvider } from "@/lib/providers/customServiceNowProvider";


import { getAuthProvidersWithSecrets } from "@/lib/iam";
import { providerMap } from "@/lib/providers/providerMap";

type Provider = NextAuthOptions['providers'][number];

async function getDynamicProviders(tenant?: string): Promise<Provider[]> {
  try {
    // Use tenant if provided, otherwise default to 'default'
    const tenantName = tenant || 'default';
    console.log(`Fetching dynamic providers for tenant: ${tenantName}`);
    
    const providersData = await getAuthProvidersWithSecrets(tenantName);
    const builtInProviders = providersData.filter(p => p.is_built_in);

    return builtInProviders.map(p => {
      const providerFactory = (providerMap as any)[p.provider_type.toLowerCase()];

      if (!providerFactory) {
        console.warn(`Unknown provider from API: ${p.provider_name}`);
        return null;
      }

      const config: any = {
        clientId: p.client_id,
        clientSecret: p.client_secret,
        id: p.provider_id,
        name: p.provider_name,
        ...p.options
      };
      

      return providerFactory(config);
    }).filter((p): p is Provider => p !== null);
  } catch (error) {
    console.error("Error fetching dynamic providers:", error);
    return [];
  }
}



async function refreshAccessToken(raw_provider:any, token: any) {
  try {

   
    const url = raw_provider.token;
    const res = await fetch(url, {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams({
        client_id: raw_provider.clientId,
        client_secret: raw_provider.clientSecret,
        grant_type: "refresh_token",
        refresh_token: token.refreshToken,
      }),
    });

    const refreshed = await res.json();

     console.info(" refreshed Access Token", refreshed)
    if (!res.ok) throw refreshed;

    return {
      ...token,
      accessToken: refreshed.access_token,
      accessTokenExpires: Date.now() + refreshed.expires_in * 1000,
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
    };
  } catch (e) {
    // Force re-login if refresh fails
    return { ...token, error: "RefreshAccessTokenError" };
  }
}





async function buildAuthOptions(tenant?: string): Promise<NextAuthOptions> {

 let providers: Provider[];

 try {
    providers = await getDynamicProviders(tenant);
  } catch (error) {
    console.error("Failed to get dynamic providers:", error);
    providers = [];
  } 
  
  if (providers.length === 0) {
    console.warn("Dynamic provider list is empty. Attempting to use static fallback providers.");
  }
  const static_providers: Provider[] = [

    CustomKeycloakProvider(
      {
      id: "testprovider", //id
      name: "TestProvider", // name

      clientId: "agent-host",
      clientSecret: "host-secret",
      issuer: "http://localhost:8888/realms/default",

      authorization: {
              "url": "http://localhost:8888/realms/default/protocol/openid-connect/auth",
              "params": { "scope": "openid email profile" }
          },
      token: "http://localhost:8888/realms/default/protocol/openid-connect/token",
  
      userinfo: "http://localhost:8888/realms/default/protocol/openid-connect/userinfo",
      jwks_endpoint: "http://localhost:8888/realms/default/protocol/openid-connect/certs"
    }),

  ]

  providers.push(...static_providers)
      
  //console.info(" total provider list", providers)

  const authOptions: NextAuthOptions = {
    providers: providers,

    // Use consistent cookie names regardless of tenant to prevent state cookie issues
    cookies: {
      sessionToken: {
        name: `next-auth.session-token`,
        options: {
          httpOnly: true,
          sameSite: 'lax',
          path: '/',
          secure: process.env.NODE_ENV === 'production'
        }
      },
      callbackUrl: {
        name: `next-auth.callback-url`,
        options: {
          sameSite: 'lax',
          path: '/',
          secure: process.env.NODE_ENV === 'production'
        }
      },
      csrfToken: {
        name: `next-auth.csrf-token`,
        options: {
          httpOnly: true,
          sameSite: 'lax',
          path: '/',
          secure: process.env.NODE_ENV === 'production'
        }
      },
      pkceCodeVerifier: {
        name: `next-auth.pkce.code_verifier`,
        options: {
          httpOnly: true,
          sameSite: 'lax',
          path: '/',
          secure: process.env.NODE_ENV === 'production',
          maxAge: 60 * 15 // 15 minutes
        }
      },
      state: {
        name: `next-auth.state`,
        options: {
          httpOnly: true,
          sameSite: 'lax',
          path: '/',
          secure: process.env.NODE_ENV === 'production',
          maxAge: 60 * 15 // 15 minutes
        }
      },
      nonce: {
        name: `next-auth.nonce`,
        options: {
          httpOnly: true,
          sameSite: 'lax',
          path: '/',
          secure: process.env.NODE_ENV === 'production'
        }
      }
    },
    
    session: {
      strategy: "jwt",

      // How long the NextAuth session cookie is valid (unrelated to KC access token),
      // You typically want it >= SSO Session Idle
      maxAge: 8 * 60 * 60, // 8 hours
      updateAge: 5 * 60,   // re-issue cookie every 5 minutes if active

    },
    callbacks: {


      async signIn({ user, account, profile }) {
        const LOGIN_PROVIDER = process.env.LOGIN_PROVIDER ||"keycloak"
        // 1. Get the session on the server-side to check if user is already logged in
        // We pass `authOptions` to `getServerSession` to prevent an infinite loop.
        const session = await getServerSession({ req: null, res: null, ...authOptions });
        
        // 2. If a session exists, we are trying to link an account
        if (session != null){
            if(session.provider == LOGIN_PROVIDER ) {
            const loginProvider = {user: session.user, accessToken: session.accessToken, idToken: session.idToken, provider:session.provider}

            console.log("Existing session found. Linking account...", session.loginProvider)
            account && (account.loginProvider=loginProvider)
          }else {
            account && (account.loginProvider = session.loginProvider)
          }
      }
        
        // Store tenant in account for JWT callback (tenant is already in cookie from TenantSelector)
        if (account && tenant) {
          (account as any).tenant = tenant;
          console.log("Tenant attached to account during sign-in:", tenant);
        }
        
        return true
      },


      async jwt({ token, account, trigger, session }) {

        // Persist the OAuth access_token to the token right after signin
        if (account) {

          token.accessToken = account.access_token;
          token.idToken = account.id_token; // Persist id_token
          token.refreshToken = account.refresh_token; // Persist refresh_token
          token.provider = account.provider
          token.loginProvider = account.loginProvider
          if (account.expires_at) {
            token.accessTokenExpires = account.expires_at * 1000;
          }

          // Get tenant from account (set in signIn callback)
          if ((account as any).tenant) {
            token.tenant = (account as any).tenant;
            console.log("Tenant set in JWT during sign-in:", token.tenant);
          }
        }

        // Handle session updates (e.g., when tenant is set)
        if (trigger === "update" && session?.tenant) {
          token.tenant = session.tenant;
        }

        const raw_provider = providers.find(p => p.id === token.provider);
        return refreshAccessToken(raw_provider, token) 

        //return token;
      },
      async session({ session, token }) {

        session.provider = token.provider
        session.accessToken = token.accessToken as string;
        session.idToken = token.idToken as string; // Make id_token available in session
        session.error = token.error as string | undefined; // For handling refresh errors
        session.loginProvider = token.loginProvider
        session.tenant = token.tenant as string | undefined; // Add tenant to session

        // Add user id (sub) and preferred_username to session
        if (token.sub) {
          session.user.id = token.sub;
        }
        if (token.preferred_username) {
          session.user.name = token.preferred_username as string;
        }
        if (token.email) {
          session.user.email = token.email as string;
        }
        return session;
      },
    },
    // Enable debug messages in the console if you are having problems
    // debug: process.env.NODE_ENV === 'development',
  };
  return authOptions
}

export async function GET(req: Request, context: any) {
    // Extract tenant from cookie
    const cookieHeader = req.headers.get('cookie') || '';

    
    const tenantMatch = cookieHeader.match(/tenant=([^;]+)/);
    const tenant = tenantMatch ? decodeURIComponent(tenantMatch[1]) : undefined;
    
    console.log("NextAuth GET route invoked with tenant:", tenant);
    console.log("DEBUG - Request URL:", req.url);
    
    const options = await buildAuthOptions(tenant);
    if (options.providers.length === 0) {
        console.error("No dynamic or static authentication providers are configured. Auth is disabled.");
        return NextResponse.json({ error: "No authentication providers configured." }, { status: 500 });
    }
    
    const handler = NextAuth(options);
    return handler(req, context);
}

export async function POST(req: Request, context: any) {
    // Extract tenant from cookie
    const cookieHeader = req.headers.get('cookie') || '';

    
    const tenantMatch = cookieHeader.match(/tenant=([^;]+)/);
    const tenant = tenantMatch ? decodeURIComponent(tenantMatch[1]) : undefined;
    
    console.log("NextAuth POST route invoked with tenant:", tenant);
    console.log("DEBUG - Request URL:", req.url);
    
    const options = await buildAuthOptions(tenant);
    if (options.providers.length === 0) {
        console.error("No dynamic or static authentication providers are configured. Auth is disabled.");
        return NextResponse.json({ error: "No authentication providers configured." }, { status: 500 });
    }
    
    const handler = NextAuth(options);
    return handler(req, context);
}
