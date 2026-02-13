import { redirect } from "next/navigation";

export default function AuthCallbackPage({
  searchParams,
}: {
  searchParams: { code?: string; state?: string; error?: string; error_description?: string };
}) {
  // Handle WorkOS callback
  // The WorkOS React SDK handles token exchange automatically via WorkOSProvider
  // We just need to redirect based on state or error

  // Handle errors from WorkOS
  if (searchParams.error) {
    const errorDesc = searchParams.error_description;
    console.error("WorkOS auth error:", searchParams.error, errorDesc);
    // Redirect to home with error info that could be displayed to user
    redirect(`/?auth_error=${encodeURIComponent(searchParams.error)}`);
  }

  // Parse state parameter to get returnTo URL
  let stateParam: { returnTo?: string } | null = null;
  if (searchParams.state) {
    try {
      stateParam = JSON.parse(decodeURIComponent(searchParams.state));
    } catch (error) {
      console.error("Failed to parse state parameter:", error);
    }
  }

  const redirectTo = stateParam?.returnTo || "/";
  redirect(redirectTo);
}
