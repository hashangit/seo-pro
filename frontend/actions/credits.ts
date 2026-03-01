'use server';

import { withAuth } from '@workos-inc/authkit-nextjs';
import { revalidatePath } from 'next/cache';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function purchaseCredits(amount: number) {
  const auth = await withAuth();
  const token = auth.accessToken;

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(`${API_URL}/api/v1/credits/purchase`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ amount }),
  });

  if (!response.ok) {
    throw new Error('Failed to purchase credits');
  }

  revalidatePath('/dashboard');
  revalidatePath('/settings/credits');
  return response.json();
}

export async function requestCredits(amount: number, reason: string) {
  const auth = await withAuth();
  const token = auth.accessToken;

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(`${API_URL}/api/v1/credits/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ amount, reason }),
  });

  if (!response.ok) {
    throw new Error('Failed to request credits');
  }

  revalidatePath('/settings/credits');
  return response.json();
}
