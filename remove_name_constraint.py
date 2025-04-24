from db import get_connection

def remove_name_constraint():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Drop the unique constraint
        cur.execute("""
            ALTER TABLE Artist
            DROP CONSTRAINT ARTIST_FIRSTNAME_LASTNAME_UK
        """)
        
        conn.commit()
        print("✅ Successfully removed the name uniqueness constraint!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    remove_name_constraint() 