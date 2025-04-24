import oracledb

def get_connection():
    dsn = oracledb.makedsn("csdb.fu.campus", 1521, sid="cs40")
    return oracledb.connect(
        user="jjumaev",
        password="34fgres3456@2001",
        dsn=dsn
    )
