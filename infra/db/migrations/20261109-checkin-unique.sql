-- Existing volumes only; new deployments get this constraint from init/01-schema.sql.
-- First inspect duplicates without changing data:
SELECT user_id, checkin_date, COUNT(*) AS duplicate_count
FROM checkin GROUP BY user_id, checkin_date HAVING COUNT(*) > 1;
-- Inspect SHOW INDEX FROM checkin as well. If uk_checkin_user_date exists, do not repeat ALTER.
-- Resolve any historical duplicates with the data owner before applying this statement.
-- This migration never deletes historical rows automatically.
ALTER TABLE checkin ADD UNIQUE KEY uk_checkin_user_date (user_id, checkin_date);
