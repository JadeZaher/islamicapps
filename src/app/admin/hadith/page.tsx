import { getAllHadiths } from '@/app/actions/graph-actions';
import { HadithManagerClient } from './client';

export default async function HadithManagerPage() {
    const hadiths = await getAllHadiths();

    return <HadithManagerClient hadiths={hadiths} />;
}
