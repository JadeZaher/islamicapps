-- fillfactor = 90 on the three tables whose derived columns are rewritten after every load and
-- decision, so those updates stay HOT and do not touch unrelated indexes (section 4.3).
-- drizzle-kit cannot express table storage parameters.
ALTER TABLE "hadiths" SET (fillfactor = 90);
--> statement-breakpoint
ALTER TABLE "chains" SET (fillfactor = 90);
--> statement-breakpoint
ALTER TABLE "chain_mentions" SET (fillfactor = 90);
