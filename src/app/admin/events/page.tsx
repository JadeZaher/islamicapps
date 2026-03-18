import { getAllHistoricalEvents } from '@/app/actions/graph-actions';
import { EventsManagerClient } from './client';

export default async function EventsManagerPage() {
    const events = await getAllHistoricalEvents();

    return <EventsManagerClient events={events} />;
}
