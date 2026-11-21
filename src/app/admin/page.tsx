import { redirect } from 'next/navigation';

// The sidebar already lists every section, so /admin lands on the first one.
export default function AdminPage() {
    redirect('/admin/hadith');
}
