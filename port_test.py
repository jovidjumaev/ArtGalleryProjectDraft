import socket

try:
    socket.create_connection(("csdb.fu.campus", 1521), timeout=5)
    print("✅ Port 1521 is open from this network.")
except Exception as e:
    print("❌ Port 1521 is NOT reachable.")
    print(e)
