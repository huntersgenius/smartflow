import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import toast, { Toaster } from "react-hot-toast";

import App from "./App";
import { isAuthError } from "./shared/api";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: (failureCount, error) => !isAuthError(error) && failureCount < 1,
    },
    mutations: {
      onError: (error) => {
        if (error instanceof Error) {
          toast.error(error.message);
        }
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <Toaster position="top-center" toastOptions={{ duration: 2600 }} />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
