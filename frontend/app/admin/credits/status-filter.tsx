'use client';

import { useRouter, usePathname } from 'next/navigation';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface StatusFilterProps {
  currentStatus?: string;
}

export function StatusFilter({ currentStatus }: StatusFilterProps) {
  const router = useRouter();
  const pathname = usePathname();

  const handleValueChange = (value: string) => {
    const params = new URLSearchParams();
    if (value) {
      params.set('status', value);
    }
    const queryString = params.toString();
    router.push(queryString ? `${pathname}?${queryString}` : pathname);
  };

  return (
    <Select value={currentStatus || ''} onValueChange={handleValueChange}>
      <SelectTrigger className="w-40">
        <SelectValue placeholder="All Statuses" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="">All Statuses</SelectItem>
        <SelectItem value="pending">Pending</SelectItem>
        <SelectItem value="proof_uploaded">Proof Uploaded</SelectItem>
        <SelectItem value="approved">Approved</SelectItem>
        <SelectItem value="rejected">Rejected</SelectItem>
      </SelectContent>
    </Select>
  );
}
