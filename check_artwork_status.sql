-- Check artwork status
SELECT a.artworkId, a.workTitle, a.status, a.askingPrice
FROM Artwork a
WHERE a.workTitle = 'Pamir'
AND a.artistLastName = 'Jumaev'
AND a.artistFirstName = 'Jovid';

-- Check for any sales of this artwork
SELECT s.INVOICENUMBER, s.SALEDATE, s.SALEPRICE, s.SALETAX, s.AMOUNTREMITTEDTOOWNER
FROM Sale s
JOIN Artwork a ON s.ARTWORKID = a.artworkId
WHERE a.workTitle = 'Pamir'
AND a.artistLastName = 'Jumaev'
AND a.artistFirstName = 'Jovid'; 