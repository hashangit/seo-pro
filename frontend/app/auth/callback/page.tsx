import { redirect } from "next/navigation";
import { logger, LogContext } from "@/lib/logger";

interface SearchParams {
  code?: string;
  state?: string;
  error?: string;
  error_description?: string;
}

export default async function AuthCallbackPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;

  // Handle WorkOS callback
  // The WorkOS React SDK handles token exchange automatically via WorkOSProvider
  // We just need to redirect based on state or error

  // Handle errors from WorkOS
  if (params.error) {
    const errorDesc = params.error_description;
    logger.error(LogContext.AUTH, { error: params.error, description: errorDesc });
    // Redirect to home with error info that could be displayed to user
    redirect(`/?auth_error=${encodeURIComponent(params.error)}`);
  }

  // Parse state parameter to get returnTo URL
  let stateParam: { returnTo?: string } | null = null;
  if (params.state) {
    try {
      stateParam = JSON.parse(decodeURIComponent(params.state));
    } catch (error) {
      logger.error(LogContext.AUTH, error);
    }
  }

  const redirectTo = stateParam?.returnTo || "/";
  redirect(redirectTo);
}
