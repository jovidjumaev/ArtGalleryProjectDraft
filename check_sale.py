import oracledb
from db import get_connection

try:
    conn = get_connection()
    cur = conn.cursor()
    
    # First get the artwork ID
    artwork_query = """
    SELECT A.artworkId, A.workTitle
    FROM Artwork A 
    JOIN Artist AR ON A.artistId = AR.artistId 
    WHERE LOWER(A.workTitle) = LOWER('My Only One') 
    AND LOWER(AR.firstName) = LOWER('Jovid') 
    AND LOWER(AR.lastName) = LOWER('Jumaev')
    """
    
    cur.execute(artwork_query)
    artwork = cur.fetchone()
    
    if artwork:
        print(f"\nArtwork found:")
        print(f"ID: {artwork[0]}")
        print(f"Title: {artwork[1]}")
        
        # Now check if this artwork ID exists in the Sale table
        sale_query = """
        SELECT invoiceNumber, saleDate, salePrice
        FROM Sale
        WHERE artworkId = :artwork_id
        """
        
        cur.execute(sale_query, artwork_id=artwork[0])
        sale = cur.fetchone()
        
        if sale:
            print(f"\nSale record found:")
            print(f"Invoice Number: {sale[0]}")
            print(f"Sale Date: {sale[1]}")
            print(f"Sale Price: ${sale[2]}")
        else:
            print("\nNo sale record found for this artwork.")
    else:
        print("Artwork not found in the database.")

except oracledb.Error as error:
    print(f"Database error: {error}")
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close() 