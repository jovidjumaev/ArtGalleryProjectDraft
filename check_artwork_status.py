from db import get_connection

def check_artwork_status():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Check artwork status
        print("\nChecking artwork status:")
        print("=" * 50)
        cur.execute("""
            SELECT a.artworkId, a.workTitle, a.status, a.askingPrice, 
                   a.artistLastName, a.artistFirstName
            FROM Artwork a
            WHERE a.workTitle = 'Pamir'
            AND a.artistLastName = 'Jumaev'
            AND a.artistFirstName = 'Jovid'
        """)
        
        artwork = cur.fetchone()
        if artwork:
            print(f"Artwork ID: {artwork[0]}")
            print(f"Title: {artwork[1]}")
            print(f"Status: {artwork[2]}")
            print(f"Asking Price: {artwork[3]}")
            print(f"Artist: {artwork[5]} {artwork[4]}")
        else:
            print("No artwork found with these details")
            
        # Check sales
        print("\nChecking sales records:")
        print("=" * 50)
        cur.execute("""
            SELECT s.INVOICENUMBER, s.SALEDATE, s.SALEPRICE, s.SALETAX, 
                   s.AMOUNTREMITTEDTOOWNER, a.artworkId, a.workTitle, a.status
            FROM Sale s
            JOIN Artwork a ON s.ARTWORKID = a.artworkId
            WHERE a.workTitle = 'Pamir'
            AND a.artistLastName = 'Jumaev'
            AND a.artistFirstName = 'Jovid'
        """)
        
        sales = cur.fetchall()
        if sales:
            print(f"Found {len(sales)} sales records:")
            for sale in sales:
                print(f"\nInvoice #: {sale[0]}")
                print(f"Sale Date: {sale[1]}")
                print(f"Sale Price: {sale[2]}")
                print(f"Sale Tax: {sale[3]}")
                print(f"Amount to Owner: {sale[4]}")
                print(f"Artwork ID: {sale[5]}")
                print(f"Artwork Title: {sale[6]}")
                print(f"Current Status: {sale[7]}")
        else:
            print("No sales records found for this artwork")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_artwork_status() 