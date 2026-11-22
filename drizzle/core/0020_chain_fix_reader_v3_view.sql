-- Reader v3 (2026-11-22): a reading made from the text and the sources' context, never the stored chain, is view `text_and_context`.
-- Widened, never narrowed; the table is empty on production at 0020 (no reading has been submitted). src/db/AGENTS.md §Chain fixes.
ALTER TABLE "chain_fix_submissions" DROP CONSTRAINT "chain_fix_submissions_view_check";--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_view_check" CHECK ("chain_fix_submissions"."view" in ('text_only', 'text_and_context', 'text_and_stored_chain'));