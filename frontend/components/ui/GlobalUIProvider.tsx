"use client";

import React, { ReactNode } from "react";
import { ToastProvider } from "./ToastProvider";
import { ConfirmProvider } from "./ConfirmProvider";

export function GlobalUIProvider({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <ConfirmProvider>
        {children}
      </ConfirmProvider>
    </ToastProvider>
  );
}
