#!/bin/bash
# Quick test - Import Eastern Hockey Federation data

echo "================================================================================"
echo "TESTING EASTERN HOCKEY FEDERATION IMPORT"
echo "================================================================================"
echo ""
echo "This will import ONE division from EHF to verify multi-league support works"
echo ""
echo "Season: 10477 (Eastern Hockey Federation)"
echo "Database: hockey_ehf_test.db"
echo ""

# Run pipeline for EHF (just import phase, one division test)
python3 full_pipeline.py \
  --season-id 10477 \
  --db-path hockey_ehf_test.db \
  --phase import \
  --log-level INFO

echo ""
echo "================================================================================"
echo "✅ EASTERN HOCKEY FEDERATION IMPORT COMPLETE"
echo "================================================================================"
echo ""
echo "Validating database..."
python3 -c "
import sqlite3
db = sqlite3.connect('hockey_ehf_test.db')
c = db.cursor()

c.execute('SELECT COUNT(*) FROM teams')
teams = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM games')
games = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM goals')
goals = c.fetchone()[0]

print(f'Teams: {teams}')
print(f'Games: {games}')
print(f'Goals: {goals}')
print('')
print('Sample teams:')
c.execute('SELECT team_name FROM teams LIMIT 5')
for row in c.fetchall():
    print(f'  - {row[0]}')

db.close()
"
echo ""
echo "Test database: hockey_ehf_test.db"
echo "You can delete this after reviewing."
