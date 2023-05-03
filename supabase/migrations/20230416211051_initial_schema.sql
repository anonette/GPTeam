CREATE extension if not exists "pgcrypto" with schema "extensions";
create extension if not exists "vector" with schema "extensions";

create type "public"."memory_type" as enum ('reflection', 'observation');
create type "public"."event_type" as enum ('non_message', 'message');
create type "public"."plan_status" as enum ('in_progress', 'todo', 'done');
create type "public"."plan_type" as enum ('default', 'response');

CREATE TABLE "public"."Agents" (
    "id" uuid DEFAULT uuid_generate_v4() NOT NULL,
    "full_name" text,
    "private_bio" text,
    "public_bio" text,
    "authorized_tools" text[],
    "directives" text[],
    "world_id" uuid,
    "last_checked_events" timestamp with time zone default now(),
    "ordered_plan_ids" uuid[],
    "location_id" uuid,
    "discord_bot_token" text,
    PRIMARY KEY ("id")
);


create table "public"."Memories" (
    "id" uuid DEFAULT uuid_generate_v4() not null,
    "created_at" timestamp with time zone default now(),
    "agent_id" uuid,
    "type" memory_type,
    "description" text,
    "related_memory_ids" uuid[],
    "embedding" vector(1536),
    "importance" smallint,
    "last_accessed" timestamp with time zone,
    PRIMARY KEY ("id")
);

create table "public"."Plans" (
    "id" uuid DEFAULT uuid_generate_v4() not null,
    "created_at" timestamp with time zone default now(),
    "agent_id" uuid,
    "description" text,
    "location_id" uuid,
    "max_duration_hrs" real,
    "stop_condition" text,
    "completed_at" timestamp with time zone,
    "scratchpad" jsonb,
    "status" plan_status not null default 'todo'::plan_status,
    "type" plan_type not null default 'default'::plan_type,
    "related_event_id" uuid,
    PRIMARY KEY ("id")
);

create table "public"."Events" (
    "id" uuid DEFAULT uuid_generate_v4() not null,
    "timestamp" timestamp with time zone default now(),
    "type" event_type,
    "description" text,
    "agent_id" uuid,
    "location_id" uuid,
    "witness_ids" uuid[],
    PRIMARY KEY ("id")
);

create table "public"."Locations" (
    "id" uuid DEFAULT uuid_generate_v4() not null,
    "world_id" uuid,
    "name" text,
    "available_tools" text[],
    "description" text,
    "channel_id" bigint,
    "allowed_agent_ids" uuid[],
    PRIMARY KEY ("id")
);

create table "public"."Worlds" (
    "id" uuid DEFAULT uuid_generate_v4() not null,
    "name" text,
    PRIMARY KEY ("id")
);

alter table "public"."Agents" add constraint "Agents_location_fkey" FOREIGN KEY (location_id) REFERENCES "Locations"(id) not valid;

alter table "public"."Agents" validate constraint "Agents_location_fkey";

alter table "public"."Agents" add constraint "Agents_world_id_fkey" FOREIGN KEY (world_id) REFERENCES "Worlds"(id) ON DELETE CASCADE not valid;

alter table "public"."Agents" validate constraint "Agents_world_id_fkey";

alter table "public"."Events" add constraint "Events_location_id_fkey" FOREIGN KEY (location_id) REFERENCES "Locations"(id) ON DELETE CASCADE not valid;

alter table "public"."Events" validate constraint "Events_location_id_fkey";

alter table "public"."Events" add constraint "Events_agent_id_fkey" FOREIGN KEY (agent_id) REFERENCES "Agents"(id) ON DELETE CASCADE not valid;

alter table "public"."Events" validate constraint "Events_agent_id_fkey";