// Round 5: narrators with no teacher (or no student) before the recalibration who have one now, with names. Read-only.
// Usage: node --env-file=.env.local datasets/hadith-data/chain-audit/round5/regained.cjs <pairs-before.json> <pairs-after.json>
const fs = require('fs');
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connect_timeout: 30 });
const read = (file) => JSON.parse(fs.readFileSync(file, 'utf8')).pairs;
(async () => {
  const before = read(process.argv[2]); const after = read(process.argv[3]);
  const key = (p) => `${p.student_id}|${p.teacher_id}`;
  const had = new Set(before.map(key));
  const studentsBefore = new Set(before.map((p) => p.student_id)); const teachersBefore = new Set(before.map((p) => p.teacher_id));
  const tally = new Map();
  for (const p of after) {
    if (had.has(key(p))) continue;
    if (!studentsBefore.has(p.student_id)) { const e = tally.get(p.student_id) || { teachers: 0, students: 0 }; e.teachers++; tally.set(p.student_id, e); }
    if (!teachersBefore.has(p.teacher_id)) { const e = tally.get(p.teacher_id) || { teachers: 0, students: 0 }; e.students++; tally.set(p.teacher_id, e); }
  }
  const ids = [...tally.keys()];
  const names = await sql`select id, name_ar from narrators where id in ${sql(ids)}`;
  const nameOf = new Map(names.map((n) => [n.id, n.name_ar]));
  const top = [...tally.entries()].sort((a, b) => (b[1].teachers + b[1].students) - (a[1].teachers + a[1].students)).slice(0, 12);
  console.log('narrators who gained a first teacher or first student:', tally.size);
  for (const [id, e] of top) console.log(id, nameOf.get(id), `first-teachers ${e.teachers}, first-students ${e.students}`);
  await sql.end();
})();
