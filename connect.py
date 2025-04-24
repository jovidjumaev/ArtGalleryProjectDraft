import oracledb

try:
    # Build the DSN using the SID format
    dsn = oracledb.makedsn("csdb.fu.campus", 1521, sid="cs40")

    connection = oracledb.connect(
        user="jjumaev",
        password="34fgres3456@2001",  # ← put your real password
        dsn=dsn
    )

    print("✅ Connected to Oracle!")

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Artist")
    for row in cursor:
        print(row)

    cursor.close()
    connection.close()

except Exception as e:
    print("❌ Connection failed:")
    print(e)
