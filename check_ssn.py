from db import get_connection

def check_existing_ssns():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Query to get all SSNs from Artist table
        print("\nExisting SSNs in Artist table:")
        print("--------------------------------")
        cur.execute("SELECT socialSecurityNumber FROM Artist ORDER BY socialSecurityNumber")
        for row in cur:
            print(row[0])
            
        print("\nExisting SSNs in Collector table:")
        print("--------------------------------")
        cur.execute("SELECT socialSecurityNumber FROM Collector ORDER BY socialSecurityNumber")
        for row in cur:
            print(row[0])
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    check_existing_ssns() 