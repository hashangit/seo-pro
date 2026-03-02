import { authkitMiddleware } from '@workos-inc/authkit-nextjs';

export default authkitMiddleware({
  middlewareAuth: {
    enabled: true,
    unauthenticatedPaths: [
      '/',
      '/login',
      '/signup',
      '/callback',
      '/api/auth/:path*',
      '/features',
      '/pricing',
    ],
  },
});

export const config = {
  matcher: [
    // Only run middleware on protected routes
    '/dashboard/:path*',
    '/settings/:path*',
    '/audits/:path*',
    '/admin/:path*',
    '/credits/:path*',
    '/analysis/:path*',
  ],
};
