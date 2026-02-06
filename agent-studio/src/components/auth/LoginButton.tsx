"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import React from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginButton() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl");

  if (status === "loading") {
    return <p>Loading...</p>;
  }

  if (session) {
    const userName=session.loginProvider?.user?.name || session.user?.name
    return (
      <div className="flex items-center space-x-4">
        <p className="text-sm text-slate-700">
          <span className="text-slate-500">Signed in as</span>{" "}
          <span className="font-medium text-slate-800">{userName}</span>
        </p>
        <button
          onClick={() => {
            signOut();
            router.push("/");
          }}
          className="px-3 py-1.5 text-sm bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition-colors"
        >
          Sign out
        </button>
      </div>
    );
  }
  return (
    <button
      onClick={() => signIn("keycloak", { callbackUrl: callbackUrl || "/portal" })}
      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
    >
      Sign in with Keycloak
    </button>
  );
}
