-- Migration: Audit Change Notification Trigger
-- Enables WebSocket push via Postgres LISTEN/NOTIFY for real-time audit status updates

CREATE FUNCTION notify_audit_change()
RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('audit_changes', json_build_object(
    'id', NEW.id,
    'user_id', NEW.user_id,
    'status', NEW.status,
    'completed_at', NEW.completed_at,
    'page_count', NEW.page_count,
    'credits_used', NEW.credits_used,
    'error_message', NEW.error_message
  )::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_changed AFTER UPDATE ON audits
FOR EACH ROW EXECUTE FUNCTION notify_audit_change();
