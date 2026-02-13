"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  static getDerivedStateFromProps(props: ErrorBoundaryProps, state: ErrorBoundaryState): ErrorBoundaryState {
    return state;
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ hasError: true, error });
  }

  render() {
    if (this.state as ErrorBoundaryState).hasError) {
      return (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Something went wrong</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <AlertCircle className="h-12 w-12 text-destructive" />
              <div>
                <h3 className="text-lg font-semibold mb-2">An error occurred</h3>
                <p className="text-sm text-muted-foreground">
                  {this.state.error?.message || "Please try again or contact support if the problem persists."}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}

export function FallbackError({ error }: { error: Error | null }) {
  return (
    <div className="min-h-[400px] flex items-center justify-center rounded-lg border border-destructive bg-destructive/10 p-6">
      <AlertCircle className="h-12 w-12 text-destructive mb-4" />
      <div className="text-center">
        <h1 className="text-xl font-bold mb-2">Something went wrong</h1>
        <p className="text-muted-foreground mb-4">
          {error?.message || "An unexpected error occurred. Please try again."}
        </p>
      </div>
    </div>
  );
}
