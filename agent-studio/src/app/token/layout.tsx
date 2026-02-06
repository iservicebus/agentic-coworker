import AuthGuard from "@/components/auth/AuthGuard";
import React, { Suspense } from "react";

export default function TokenLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthGuard>{children}</AuthGuard>
    </Suspense>
  );
}
