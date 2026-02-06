/**
 * Utility function to get tenant ID from cookie
 * This function can be used in both client-side React components and API client
 */
export function getTenantFromCookie(): string | null {
  if (typeof document === 'undefined') {
    // Server-side rendering - no cookies available
    return null;
  }
  
  const cookies = document.cookie.split(';');
  const tenantCookie = cookies.find(c => c.trim().startsWith('tenant='));
  
  if (tenantCookie) {
    const tenantValue = tenantCookie.split('=')[1];
    return tenantValue || null;
  }
  
  return null;
}
