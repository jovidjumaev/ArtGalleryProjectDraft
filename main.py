from connect import connect_db

def main():
    conn = connect_db()
    print("🎨 Connected to the Art Gallery Database!")

    # You can now call functions like run_query1(conn), insert_data(conn), etc.

if __name__ == "__main__":
    main()
