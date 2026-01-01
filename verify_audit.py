
import sqlite3
import pandas as pd

conn = sqlite3.connect('instance/rental.db')
query = "SELECT * FROM audit_log ORDER BY id DESC LIMIT 5"
df = pd.read_sql_query(query, conn)
pd.set_option('display.max_colwidth', None)
print(df[['action', 'target_type', 'details', 'timestamp']])
conn.close()
