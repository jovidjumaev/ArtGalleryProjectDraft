from db import get_connection

def get_available_zips():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Query to get all ZIP codes
        cur.execute("SELECT zip FROM ZIPS ORDER BY zip")
        
        print("\nAvailable ZIP codes in database:")
        print("--------------------------------")
        for row in cur:
            print(row[0])
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    get_available_zips() 