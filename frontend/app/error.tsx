"use client";

import { useEffect } from "react";

import { ErrorScreen } from "@/components/ui/ErrorScreen";

export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Route render failed", error);
  }, [error]);

  return <ErrorScreen onRetry={reset} />;
}
