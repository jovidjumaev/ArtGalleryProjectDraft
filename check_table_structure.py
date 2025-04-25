from db import get_connection

def check_table_structure():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        print("\nChecking Buyer table structure:")
        print("=" * 50)
        cur.execute("""
            SELECT column_name, data_type, data_length
            FROM user_tab_columns
            WHERE table_name = 'BUYER'
            ORDER BY column_id
        """)
        
        columns = cur.fetchall()
        for col in columns:
            print(f"Column: {col[0]}, Type: {col[1]}, Length: {col[2]}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table_structure() 