'use server';

import { withAuth } from '@workos-inc/authkit-nextjs';
import { revalidatePath } from 'next/cache';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function approveCreditRequest(requestId: string, adminNotes?: string) {
  const auth = await withAuth();
  const token = auth.accessToken;

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(
    `${API_URL}/api/v1/admin/credits/requests/${requestId}/approve`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ admin_notes: adminNotes }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to approve credit request' }));
    throw new Error(error.detail || 'Failed to approve credit request');
  }

  revalidatePath('/admin/credits');
  return response.json();
}

export async function rejectCreditRequest(requestId: string, reason: string) {
  const auth = await withAuth();
  const token = auth.accessToken;

  if (!token) {
    throw new Error('Unauthorized');
  }

  const response = await fetch(
    `${API_URL}/api/v1/admin/credits/requests/${requestId}/reject`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ reason }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to reject credit request' }));
    throw new Error(error.detail || 'Failed to reject credit request');
  }

  revalidatePath('/admin/credits');
  return response.json();
}
