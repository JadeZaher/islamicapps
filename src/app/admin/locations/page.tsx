import { getAllLocations } from '@/app/actions/graph-actions';
import { LocationsManagerClient } from './client';

export default async function LocationsManagerPage() {
    const locations = await getAllLocations();

    return <LocationsManagerClient locations={locations} />;
}
