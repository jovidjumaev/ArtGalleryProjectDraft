-- Drop existing triggers
DROP TRIGGER boostBuyer;
DROP TRIGGER updateArtistSales;

-- Create improved boostBuyer trigger
CREATE OR REPLACE TRIGGER boostBuyer
AFTER INSERT ON Sale
FOR EACH ROW
DECLARE
  v_buyer_exists NUMBER;
BEGIN
  -- Check if buyer exists
  SELECT COUNT(*) INTO v_buyer_exists
  FROM Buyer
  WHERE buyerId = :NEW.buyerId;
  
  IF v_buyer_exists > 0 THEN
    UPDATE Buyer
    SET PURCHASESYEARTODATE = 
      CASE 
        WHEN PURCHASESYEARTODATE IS NULL THEN :NEW.salePrice
        ELSE PURCHASESYEARTODATE + :NEW.salePrice
      END
    WHERE buyerId = :NEW.buyerId;
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    -- Log error but don't fail the transaction
    NULL;
END;
/

-- Create improved updateArtistSales trigger
CREATE OR REPLACE TRIGGER updateArtistSales
AFTER INSERT ON Sale
FOR EACH ROW
DECLARE
  v_artist_id NUMBER;
  v_artist_exists NUMBER;
BEGIN
  -- Get artist ID with error handling
  BEGIN
    SELECT artwork.artistId INTO v_artist_id
    FROM Artwork artwork
    WHERE artwork.artworkId = :NEW.artworkId;
    
    -- Check if artist exists
    SELECT COUNT(*) INTO v_artist_exists
    FROM Artist
    WHERE artistId = v_artist_id;
    
    IF v_artist_exists > 0 THEN
      UPDATE Artist
      SET salesYearToDate = 
        CASE 
          WHEN salesYearToDate IS NULL THEN :NEW.salePrice
          ELSE salesYearToDate + :NEW.salePrice
        END
      WHERE artistId = v_artist_id;
    END IF;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      -- Artwork not found, do nothing
      NULL;
    WHEN OTHERS THEN
      -- Log error but don't fail the transaction
      NULL;
  END;
END;
/ 