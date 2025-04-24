-- Create sequence for user IDs
CREATE SEQUENCE user_id_seq
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- Create users table
CREATE TABLE users (
    user_id NUMBER DEFAULT user_id_seq.NEXTVAL PRIMARY KEY,
    username VARCHAR2(20) UNIQUE NOT NULL,
    password_hash VARCHAR2(255) NOT NULL,
    email VARCHAR2(255) UNIQUE NOT NULL,
    first_name VARCHAR2(30) NOT NULL,
    last_name VARCHAR2(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create index on username for faster lookups
CREATE INDEX idx_users_username ON users(username);

-- Create index on email for faster lookups
CREATE INDEX idx_users_email ON users(email); 