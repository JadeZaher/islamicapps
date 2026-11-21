ALTER TABLE "parallel_research_runs" DISABLE ROW LEVEL SECURITY;--> statement-breakpoint
DROP TABLE "parallel_research_runs" CASCADE;--> statement-breakpoint
ALTER TABLE "cross_parallels" DROP CONSTRAINT IF EXISTS "cross_parallels_research_run_id_fk";
--> statement-breakpoint
ALTER TABLE "cross_parallels" DROP COLUMN "research_run_id";--> statement-breakpoint
DROP TYPE "public"."research_outcome";