"""
import sqlite3

conn = sqlite3.connect("database.sqlite")
cursor = conn.cursor()

def get_all_perfumes():
    cursor.execute("SELECT * FROM perfumes WHERE is_active = 1")
    rows = cursor.fetchall()
    perfumes = []
    for row in rows:
        perfumes.append({
            "id": row[0],
            "name": row[1],
            "brand": row[2],
            "category": row[3],
            "scent_category": row[4],
            "description": row[5],
            "volume": row[6],
            "type": row[7],
            "photo": row[8],
            "photo2": row[9]
        })
    return perfumes
"""

