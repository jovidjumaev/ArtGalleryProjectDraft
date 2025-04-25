-- Check trigger existence and status
SELECT trigger_name, status, trigger_type, triggering_event, table_name
FROM user_triggers
WHERE table_name IN ('SALE', 'BUYER', 'ARTIST');

-- Check trigger definitions
SELECT trigger_name, trigger_body
FROM user_triggers
WHERE table_name IN ('SALE', 'BUYER', 'ARTIST');

-- Check for any locks
SELECT blocking_session, sid, serial#, wait_class, event, seconds_in_wait
FROM v$session
WHERE state = 'WAITING' AND wait_class != 'Idle'; 