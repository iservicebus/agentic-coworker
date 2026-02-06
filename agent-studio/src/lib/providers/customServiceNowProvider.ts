import { OAuthConfig } from "next-auth/providers/oauth";

export const CustomServiceNowProvider =( options: any ) => {
  return {
  id: "servicenow",
  name: "ServiceNow",
  type: "oauth",


  async profile(profileData: any) {
    const user = profileData?.result?.[0] ?? {};
    return {
      id: user.sys_id,
      name: user.name,
      email: user.email,
    };
  },

  ...options,

} satisfies OAuthConfig<any>

}; 
