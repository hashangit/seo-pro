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
    ],
  },
});

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/settings/:path*',
    '/audits/:path*',
    '/admin/:path*',
  ],
};
