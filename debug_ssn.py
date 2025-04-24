from db import get_connection

def check_ssns_with_names():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        print("\nArtists in database:")
        print("-------------------")
        cur.execute("""
            SELECT socialSecurityNumber, firstName, lastName 
            FROM Artist 
            ORDER BY socialSecurityNumber
        """)
        for row in cur:
            print(f"SSN: {row[0]} - Name: {row[1]} {row[2]}")
            
        print("\nCollectors in database:")
        print("----------------------")
        cur.execute("""
            SELECT socialSecurityNumber, firstName, lastName 
            FROM Collector 
            ORDER BY socialSecurityNumber
        """)
        for row in cur:
            print(f"SSN: {row[0]} - Name: {row[1]} {row[2]}")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    check_ssns_with_names() 