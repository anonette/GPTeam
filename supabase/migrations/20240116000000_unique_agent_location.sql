-- IMPORTANT NOTE:
-- This migration enforces that all agents can only be in the Conference location.
-- This is required because:
-- 1. The config.json specifies Conference as the only location
-- 2. The LLM responses might try to use other locations (Office, Community Center, etc.)
-- 3. We need to ensure data integrity at the database level
-- 4. This prevents Location.from_name errors in the application

-- Function to normalize location name to Conference
CREATE OR REPLACE FUNCTION normalize_location_name(name text)
RETURNS text AS $$
BEGIN
    -- Always return 'Conference' regardless of input
    -- This ensures Location.from_name always finds the location
    RETURN 'Conference';
END;
$$ LANGUAGE plpgsql;

-- Create view that maps any location name to Conference
CREATE OR REPLACE VIEW locations_view AS
WITH conference_location AS (
    SELECT * FROM "public"."Locations"
    WHERE name = 'Conference'
)
SELECT 
    l.id,
    normalize_location_name(l.name) as name,
    l.description,
    l.channel_id,
    l.available_tools,
    l.allowed_agent_ids,
    l.world_id
FROM conference_location l;

-- Function to validate location name
CREATE OR REPLACE FUNCTION validate_location_name(location_name text)
RETURNS boolean AS $$
BEGIN
    -- Always return true for Conference, false for anything else
    -- This ensures Location.from_name will only work with Conference
    RETURN location_name = 'Conference';
END;
$$ LANGUAGE plpgsql;

-- Function to get location by name
CREATE OR REPLACE FUNCTION get_location_by_name(name text, world_id uuid)
RETURNS uuid AS $$
BEGIN
    -- Regardless of the input name, always return the Conference location ID
    -- This ensures Location.from_name always works, even if LLM tries other locations
    RETURN (
        SELECT id 
        FROM "public"."Locations" 
        WHERE name = 'Conference' 
        AND world_id = get_location_by_name.world_id
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function to ensure Conference location exists for a world
CREATE OR REPLACE FUNCTION ensure_conference_location(world_id uuid)
RETURNS uuid AS $$
DECLARE
    conference_id uuid;
BEGIN
    -- Check if Conference already exists for this world
    SELECT id INTO conference_id
    FROM "public"."Locations"
    WHERE name = 'Conference' AND world_id = ensure_conference_location.world_id
    LIMIT 1;

    -- If Conference doesn't exist, create it
    IF conference_id IS NULL THEN
        INSERT INTO "public"."Locations" (
            name,
            description,
            world_id,
            allowed_agent_ids
        ) VALUES (
            'Conference',
            'Place to confront and discuss ideas, agendas and values and negotiate some agreement.',
            ensure_conference_location.world_id,
            (SELECT array_agg(id) FROM "public"."Agents" WHERE world_id = ensure_conference_location.world_id)
        )
        RETURNING id INTO conference_id;
    END IF;

    RETURN conference_id;
END;
$$ LANGUAGE plpgsql;

-- Function to validate location moves
CREATE OR REPLACE FUNCTION validate_location_move()
RETURNS TRIGGER AS $$
DECLARE
    conference_id uuid;
BEGIN
    -- Get Conference ID for the agent's world
    SELECT id INTO conference_id
    FROM "public"."Locations"
    WHERE name = 'Conference' 
    AND world_id = (SELECT world_id FROM "public"."Agents" WHERE id = NEW.id)
    LIMIT 1;

    -- Only allow moves to Conference location
    IF NEW.location_id != conference_id THEN
        RAISE EXCEPTION 'Agents can only move to the Conference location';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to validate plan locations
CREATE OR REPLACE FUNCTION validate_plan_location()
RETURNS TRIGGER AS $$
DECLARE
    conference_id uuid;
BEGIN
    -- Get Conference ID for the agent's world
    SELECT id INTO conference_id
    FROM "public"."Locations"
    WHERE name = 'Conference' 
    AND world_id = (SELECT world_id FROM "public"."Agents" WHERE id = NEW.agent_id)
    LIMIT 1;

    -- Only allow plans for Conference location
    IF NEW.location_id != conference_id THEN
        RAISE EXCEPTION 'Plans can only be created for the Conference location';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to validate event locations
CREATE OR REPLACE FUNCTION validate_event_location()
RETURNS TRIGGER AS $$
DECLARE
    conference_id uuid;
BEGIN
    -- Get Conference ID for the agent's world
    SELECT id INTO conference_id
    FROM "public"."Locations"
    WHERE name = 'Conference' 
    AND world_id = (
        SELECT world_id 
        FROM "public"."Agents" 
        WHERE id = NEW.agent_id
        LIMIT 1
    )
    LIMIT 1;

    -- Only allow events for Conference location
    IF NEW.location_id != conference_id THEN
        RAISE EXCEPTION 'Events can only be created for the Conference location';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to check if agents are in same location
CREATE OR REPLACE FUNCTION are_agents_in_same_location(agent1_id uuid, agent2_id uuid)
RETURNS boolean AS $$
BEGIN
    -- Since all agents must be in Conference, this will always return true
    -- But we keep it as a function in case the single-location requirement changes in the future
    RETURN (
        SELECT a1.location_id = a2.location_id
        FROM "public"."Agents" a1, "public"."Agents" a2
        WHERE a1.id = agent1_id AND a2.id = agent2_id
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get conference location id for a world
CREATE OR REPLACE FUNCTION get_conference_location_id(world_id uuid)
RETURNS uuid AS $$
BEGIN
    RETURN (
        SELECT id 
        FROM "public"."Locations" 
        WHERE name = 'Conference' 
        AND world_id = get_conference_location_id.world_id
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Trigger to ensure Conference exists when world is created
CREATE OR REPLACE FUNCTION ensure_world_has_conference()
RETURNS TRIGGER AS $$
BEGIN
    -- Create Conference location for new world
    PERFORM ensure_conference_location(NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger for world creation
DROP TRIGGER IF EXISTS world_conference_trigger ON "public"."Worlds";
CREATE TRIGGER world_conference_trigger
    AFTER INSERT ON "public"."Worlds"
    FOR EACH ROW
    EXECUTE FUNCTION ensure_world_has_conference();

-- Trigger to validate location names on insert/update
CREATE OR REPLACE FUNCTION validate_location_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT validate_location_name(NEW.name) THEN
        RAISE EXCEPTION 'Only Conference location is allowed, but got: %', NEW.name;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger for location validation
DROP TRIGGER IF EXISTS location_name_trigger ON "public"."Locations";
CREATE TRIGGER location_name_trigger
    BEFORE INSERT OR UPDATE ON "public"."Locations"
    FOR EACH ROW
    EXECUTE FUNCTION validate_location_insert();

-- Ensure Conference locations exist for all worlds and clean up any other locations
DO $$ 
DECLARE
    world record;
BEGIN
    FOR world IN SELECT * FROM "public"."Worlds"
    LOOP
        -- Ensure Conference exists for this world
        PERFORM ensure_conference_location(world.id);

        -- Delete all non-Conference locations
        DELETE FROM "public"."Locations"
        WHERE world_id = world.id 
        AND name != 'Conference';

        -- Update all agents to be in Conference location
        UPDATE "public"."Agents"
        SET location_id = (
            SELECT id 
            FROM "public"."Locations" 
            WHERE name = 'Conference' 
            AND world_id = world.id
        )
        WHERE world_id = world.id;

        -- Update all plans to use Conference location
        UPDATE "public"."Plans"
        SET location_id = (
            SELECT id 
            FROM "public"."Locations" 
            WHERE name = 'Conference' 
            AND world_id = world.id
        )
        WHERE agent_id IN (
            SELECT id 
            FROM "public"."Agents" 
            WHERE world_id = world.id
        );

        -- Update all events to use Conference location
        UPDATE "public"."Events"
        SET location_id = (
            SELECT id 
            FROM "public"."Locations" 
            WHERE name = 'Conference' 
            AND world_id = world.id
        )
        WHERE agent_id IN (
            SELECT id 
            FROM "public"."Agents" 
            WHERE world_id = world.id
        );

        -- Update Conference location to include all agents
        UPDATE "public"."Locations"
        SET allowed_agent_ids = (
            SELECT array_agg(id)
            FROM "public"."Agents"
            WHERE world_id = world.id
        )
        WHERE world_id = world.id 
        AND name = 'Conference';
    END LOOP;
END $$;

-- Add constraint to ensure only Conference locations exist
ALTER TABLE "public"."Locations"
ADD CONSTRAINT locations_conference_only
CHECK (name = 'Conference');

-- Add constraint to ensure agents can only have Conference as location_id
ALTER TABLE "public"."Agents"
ADD CONSTRAINT agents_conference_only
CHECK (
    location_id IN (
        SELECT id 
        FROM "public"."Locations" 
        WHERE name = 'Conference'
    )
);

-- Add constraint to ensure plans can only reference Conference location
ALTER TABLE "public"."Plans"
ADD CONSTRAINT plans_conference_only
CHECK (
    location_id IN (
        SELECT id 
        FROM "public"."Locations" 
        WHERE name = 'Conference'
    )
);

-- Add constraint to ensure events can only reference Conference location
ALTER TABLE "public"."Events"
ADD CONSTRAINT events_conference_only
CHECK (
    location_id IN (
        SELECT id 
        FROM "public"."Locations" 
        WHERE name = 'Conference'
    )
);

-- Create view to ensure allowed_locations only returns Conference
CREATE OR REPLACE VIEW allowed_locations AS
SELECT * FROM "public"."Locations"
WHERE name = 'Conference';

-- Add rollback function
CREATE OR REPLACE FUNCTION rollback_conference_only()
RETURNS void AS $$
BEGIN
    DROP TRIGGER IF EXISTS enforce_location_move ON "public"."Agents";
    DROP FUNCTION IF EXISTS validate_location_move();
    DROP TRIGGER IF EXISTS enforce_plan_location ON "public"."Plans";
    DROP FUNCTION IF EXISTS validate_plan_location();
    DROP TRIGGER IF EXISTS enforce_event_location ON "public"."Events";
    DROP FUNCTION IF EXISTS validate_event_location();
    DROP TRIGGER IF EXISTS world_conference_trigger ON "public"."Worlds";
    DROP TRIGGER IF EXISTS location_name_trigger ON "public"."Locations";
    DROP FUNCTION IF EXISTS ensure_world_has_conference();
    DROP FUNCTION IF EXISTS validate_location_insert();
    DROP FUNCTION IF EXISTS validate_location_name(text);
    DROP FUNCTION IF EXISTS normalize_location_name(text);
    DROP FUNCTION IF EXISTS get_location_by_name(text, uuid);
    DROP FUNCTION IF EXISTS ensure_conference_location(uuid);
    DROP FUNCTION IF EXISTS are_agents_in_same_location(uuid, uuid);
    DROP FUNCTION IF EXISTS get_conference_location_id(uuid);
    DROP VIEW IF EXISTS locations_view;
    DROP VIEW IF EXISTS allowed_locations;
    ALTER TABLE "public"."Locations" DROP CONSTRAINT IF EXISTS locations_conference_only;
    ALTER TABLE "public"."Agents" DROP CONSTRAINT IF EXISTS agents_conference_only;
    ALTER TABLE "public"."Plans" DROP CONSTRAINT IF EXISTS plans_conference_only;
    ALTER TABLE "public"."Events" DROP CONSTRAINT IF EXISTS events_conference_only;
END;
$$ LANGUAGE plpgsql;
