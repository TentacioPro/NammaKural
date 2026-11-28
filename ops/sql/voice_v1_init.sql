-- Voice v1 storage initialization. Apply explicitly after review; runtime/migration
-- execution and database credentials are not wired by this scaffold.
BEGIN;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS voice_v1;

CREATE TABLE IF NOT EXISTS voice_v1.wards (
    ward_id text PRIMARY KEY CHECK (length(btrim(ward_id)) BETWEEN 1 AND 80),
    display_name text NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 160),
    boundary geometry(MultiPolygon, 4326) NOT NULL,
    active boolean NOT NULL DEFAULT true,
    CHECK (ST_IsValid(boundary))
);
CREATE INDEX IF NOT EXISTS wards_boundary_gix ON voice_v1.wards USING gist (boundary);

CREATE TABLE IF NOT EXISTS voice_v1.landmarks (
    landmark_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
    category text NOT NULL CHECK (length(btrim(category)) BETWEEN 1 AND 80),
    location geography(Point, 4326) NOT NULL,
    ward_id text REFERENCES voice_v1.wards(ward_id) ON DELETE SET NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS landmarks_location_gix ON voice_v1.landmarks USING gist (location);
CREATE INDEX IF NOT EXISTS landmarks_ward_idx ON voice_v1.landmarks (ward_id) WHERE active;

CREATE TABLE IF NOT EXISTS voice_v1.cases (
    case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status text NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','CONFIRMED','QUEUED_FOR_SUBMISSION','SUBMITTED')),
    version integer NOT NULL DEFAULT 0 CHECK (version >= 0),
    category text CHECK (category IS NULL OR length(category) <= 100),
    description text CHECK (description IS NULL OR length(description) <= 4000),
    location geography(Point, 4326),
    ward_id text REFERENCES voice_v1.wards(ward_id) ON DELETE SET NULL,
    landmark_id uuid REFERENCES voice_v1.landmarks(landmark_id) ON DELETE SET NULL,
    receipt_reference text,
    receipt_verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((receipt_reference IS NULL) = (receipt_verified_at IS NULL)),
    CHECK ((status = 'SUBMITTED') = (receipt_reference IS NOT NULL AND receipt_verified_at IS NOT NULL)),
    CHECK (receipt_reference IS NULL OR length(btrim(receipt_reference)) BETWEEN 1 AND 200)
);
CREATE INDEX IF NOT EXISTS cases_location_time_gix ON voice_v1.cases USING gist (location);
CREATE INDEX IF NOT EXISTS cases_created_status_idx ON voice_v1.cases (created_at, status);
CREATE INDEX IF NOT EXISTS cases_ward_created_idx ON voice_v1.cases (ward_id, created_at);

CREATE TABLE IF NOT EXISTS voice_v1.idempotency_keys (
    idempotency_key text PRIMARY KEY CHECK (length(btrim(idempotency_key)) BETWEEN 1 AND 200),
    operation text NOT NULL CHECK (length(operation) BETWEEN 1 AND 100),
    request_fingerprint bytea NOT NULL CHECK (octet_length(request_fingerprint) = 32),
    case_id uuid REFERENCES voice_v1.cases(case_id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz
);
CREATE INDEX IF NOT EXISTS idempotency_expiry_idx ON voice_v1.idempotency_keys (expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS voice_v1.outbox (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id uuid NOT NULL REFERENCES voice_v1.cases(case_id) ON DELETE CASCADE,
    event_type text NOT NULL CHECK (length(event_type) BETWEEN 1 AND 120),
    idempotency_key text NOT NULL UNIQUE CHECK (length(btrim(idempotency_key)) BETWEEN 1 AND 200),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    available_at timestamptz NOT NULL DEFAULT now(),
    delivered_at timestamptz,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error_code text CHECK (last_error_code IS NULL OR length(last_error_code) <= 100)
);
CREATE INDEX IF NOT EXISTS outbox_pending_idx ON voice_v1.outbox (available_at, created_at) WHERE delivered_at IS NULL;

CREATE TABLE IF NOT EXISTS voice_v1.memories (
    memory_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_kind text NOT NULL CHECK (scope_kind IN ('session','user','case')),
    scope_owner_id text NOT NULL CHECK (length(btrim(scope_owner_id)) BETWEEN 1 AND 200),
    memory_key text NOT NULL CHECK (length(btrim(memory_key)) BETWEEN 1 AND 120),
    value jsonb NOT NULL CHECK (jsonb_typeof(value) IN ('object','array','string','number','boolean','null')),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    deleted_at timestamptz,
    CHECK (expires_at IS NULL OR expires_at > created_at),
    UNIQUE (scope_kind, scope_owner_id, memory_key)
);
CREATE INDEX IF NOT EXISTS memories_active_scope_idx ON voice_v1.memories (scope_kind, scope_owner_id, memory_key) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS memories_expiry_idx ON voice_v1.memories (expires_at) WHERE expires_at IS NOT NULL AND deleted_at IS NULL;

-- Deterministic location resolver: returns all ward matches; callers must preserve
-- ambiguity rather than arbitrarily assigning a ward when boundaries overlap.
CREATE OR REPLACE FUNCTION voice_v1.resolve_location(p_location geography, p_landmark_radius_m double precision DEFAULT 500)
RETURNS TABLE (ward_id text, landmark_id uuid, landmark_name text, distance_m double precision)
LANGUAGE sql STABLE PARALLEL SAFE AS $$
    WITH ward_matches AS (
        SELECT w.ward_id FROM voice_v1.wards w
        WHERE w.active AND ST_Covers(w.boundary, p_location::geometry)
    ), nearest AS (
        SELECT l.landmark_id, l.name, ST_Distance(l.location, p_location) AS distance_m
        FROM voice_v1.landmarks l WHERE l.active
          AND ST_DWithin(l.location, p_location, greatest(0, p_landmark_radius_m))
    )
    SELECT wm.ward_id, n.landmark_id, n.name, n.distance_m
    FROM (SELECT ward_id FROM ward_matches UNION ALL SELECT NULL::text WHERE NOT EXISTS (SELECT 1 FROM ward_matches)) wm
    LEFT JOIN nearest n ON true
    ORDER BY n.distance_m NULLS LAST, wm.ward_id NULLS LAST
$$;

-- Guard direct SQL writes as well as application writes. Receipt values are
-- accepted only on the queued-to-submitted edge; no external submission occurs.
CREATE OR REPLACE FUNCTION voice_v1.enforce_case_lifecycle()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        IF NOT ((OLD.status = 'DRAFT' AND NEW.status = 'CONFIRMED') OR
                (OLD.status = 'CONFIRMED' AND NEW.status = 'QUEUED_FOR_SUBMISSION') OR
                (OLD.status = 'QUEUED_FOR_SUBMISSION' AND NEW.status = 'SUBMITTED')) THEN
            RAISE EXCEPTION 'invalid voice case transition: % -> %', OLD.status, NEW.status
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW.status = 'SUBMITTED' AND
           (NEW.receipt_reference IS NULL OR btrim(NEW.receipt_reference) = '' OR
            NEW.receipt_verified_at IS NULL) THEN
            RAISE EXCEPTION 'SUBMITTED requires a verified receipt'
                USING ERRCODE = 'check_violation';
        END IF;
        NEW.version := OLD.version + 1;
        NEW.updated_at := now();
    END IF;
    IF OLD.status = 'SUBMITTED' AND
       (NEW.receipt_reference IS DISTINCT FROM OLD.receipt_reference OR
        NEW.receipt_verified_at IS DISTINCT FROM OLD.receipt_verified_at) THEN
        RAISE EXCEPTION 'submitted receipt is immutable' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
DROP TRIGGER IF EXISTS cases_lifecycle_guard ON voice_v1.cases;
CREATE TRIGGER cases_lifecycle_guard BEFORE UPDATE ON voice_v1.cases
FOR EACH ROW EXECUTE FUNCTION voice_v1.enforce_case_lifecycle();

-- The outbox insert shares the case transition transaction. Payload intentionally
-- excludes complaint description, location, phone numbers, and all user-provided text.
CREATE OR REPLACE FUNCTION voice_v1.enqueue_case_transition()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO voice_v1.outbox (
            aggregate_id, event_type, idempotency_key, payload
        ) VALUES (
            NEW.case_id,
            'case.' || lower(NEW.status),
            'case:' || NEW.case_id::text || ':v' || NEW.version::text || ':' || NEW.status,
            jsonb_build_object('case_id', NEW.case_id, 'status', NEW.status, 'version', NEW.version)
        ) ON CONFLICT (idempotency_key) DO NOTHING;
    END IF;
    RETURN NEW;
END
$$;
DROP TRIGGER IF EXISTS cases_outbox_transition ON voice_v1.cases;
CREATE TRIGGER cases_outbox_transition AFTER UPDATE ON voice_v1.cases
FOR EACH ROW EXECUTE FUNCTION voice_v1.enqueue_case_transition();

-- Similarity candidates are suggestions only; no case is merged or changed.
CREATE OR REPLACE FUNCTION voice_v1.advisory_duplicate_candidates(
    p_case_id uuid, p_radius_m double precision DEFAULT 100,
    p_window interval DEFAULT interval '7 days', p_limit integer DEFAULT 20
) RETURNS TABLE (candidate_case_id uuid, distance_m double precision, time_delta interval)
LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT other.case_id, ST_Distance(other.location, subject.location),
           abs(other.created_at - subject.created_at)
    FROM voice_v1.cases subject
    JOIN voice_v1.cases other ON other.case_id <> subject.case_id
      AND subject.location IS NOT NULL AND other.location IS NOT NULL
      AND ST_DWithin(other.location, subject.location, greatest(0, p_radius_m))
      AND abs(other.created_at - subject.created_at) <= greatest(interval '0', p_window)
    WHERE subject.case_id = p_case_id
    ORDER BY ST_Distance(other.location, subject.location), abs(other.created_at - subject.created_at), other.case_id
    LIMIT greatest(0, least(p_limit, 100))
$$;

COMMIT;
