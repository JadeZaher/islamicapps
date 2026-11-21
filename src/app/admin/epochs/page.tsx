export const dynamic = 'force-dynamic';

import { listEpochs } from '@/db/queries/epoch';
import { EpochsManagerClient } from './client';

/** Eras: review state, citation and wording. Creating eras is left to the seed and future curation. */
export default async function EpochsManagerPage() {
    const { available, items } = await listEpochs();
    return <EpochsManagerClient available={available} epochs={items} />;
}
