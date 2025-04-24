try:
    import oracledb
except ImportError:
    print("Error: oracledb package not found")
    print("Please install it using: pip install oracledb")
    import sys
    sys.exit(1)

def get_connection():
    dsn = oracledb.makedsn("csdb.fu.campus", 1521, sid="cs40")
    return oracledb.connect(
        user="jjumaev",
        password="34fgres3456@2001",
        dsn=dsn
    )
