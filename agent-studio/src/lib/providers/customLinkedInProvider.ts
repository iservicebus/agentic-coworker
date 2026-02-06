export const CustomLinkedInProvider = ( options: any ) => {
  
  const defaultAuthorization = {
      url: 'https://www.linkedin.com/oauth/v2/authorization',
      params: {
        scope: 'openid profile email w_member_social', // Modern OIDC scopes
      },
    }

  const authorization = { ...defaultAuthorization, ...options?.authorization, params: { ...defaultAuthorization.params, ...options?.authorization?.params}}

  return {
    id: 'linkedin',
    name: 'LinkedIn',
    type: 'oauth' as const,
    issuer: 'https://www.linkedin.com',
    userinfo: 'https://api.linkedin.com/v2/userinfo',

    token: {
      url: 'https://www.linkedin.com/oauth/v2/accessToken',
      async request(context: any) {
        const { params, provider } = context;

        const body = new URLSearchParams();
        body.append('grant_type', 'authorization_code');
        body.append('code', params.code);
        body.append('redirect_uri', provider.callbackUrl);
        body.append('client_id', provider.clientId);
        body.append('client_secret', provider.clientSecret);

        const response = await fetch(provider.token.url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: body.toString(),
        });

        if (!response.ok) {
          const errorBody = await response.text();
          console.error("LinkedIn Token Request Failed:", errorBody);
          throw new Error("LinkedIn token request failed");
        }

        const tokens = await response.json();
        return { tokens };
      },
    },


    profile(profile: any) {
      return {
        id: profile.sub,
        name: profile.name,
        email: profile.email,
        image: profile.picture,
      };
    },
    ...options,
  };
};
