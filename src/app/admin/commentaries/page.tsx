import { getAllCommentaries, getAllHadiths, getAllNarrators } from '@/app/actions/graph-actions';
import { CommentariesManagerClient } from './client';

export default async function CommentariesManagerPage() {
    const commentaries = await getAllCommentaries();
    const hadiths = await getAllHadiths();
    const narrators = await getAllNarrators();

    return (
        <CommentariesManagerClient
            commentaries={commentaries}
            hadiths={hadiths}
            narrators={narrators}
        />
    );
}
