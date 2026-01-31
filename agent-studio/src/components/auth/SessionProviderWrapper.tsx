"use client";

import { SessionProvider } from "next-auth/react";
import React from "react";

interface SessionProviderWrapperProps {
  children: React.ReactNode;
}

export default function SessionProviderWrapper({
  children,
}: SessionProviderWrapperProps) {
  return <SessionProvider>{children}</SessionProvider>;
}
