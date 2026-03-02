'use server';

import { signOut, getSignInUrl } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export async function signInAction() {
  const signInUrl = await getSignInUrl();
  redirect(signInUrl);
}

export async function signOutAction() {
  await signOut();
  redirect('/');
}
