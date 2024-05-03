--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2 (Debian 16.2-1.pgdg120+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: rootUser
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO "rootUser";

--
-- Name: job_status; Type: TYPE; Schema: public; Owner: backend
--

CREATE TYPE public.job_status AS ENUM (
    'pending',
    'in_progress',
    'success',
    'error',
    'retry'
);


ALTER TYPE public.job_status OWNER TO backend;

--
-- Name: token_purpose; Type: TYPE; Schema: public; Owner: backend
--

CREATE TYPE public.token_purpose AS ENUM (
    'ACCESS',
    'REFRESH'
);


ALTER TYPE public.token_purpose OWNER TO backend;

--
-- Name: user_pin_role; Type: TYPE; Schema: public; Owner: backend
--

CREATE TYPE public.user_pin_role AS ENUM (
    'manager',
    'respondent'
);


ALTER TYPE public.user_pin_role OWNER TO backend;

--
-- Name: decrypt_internal(text, bytea); Type: FUNCTION; Schema: public; Owner: backend
--

CREATE FUNCTION public.decrypt_internal(text, bytea) RETURNS text
    LANGUAGE plpgsql
    AS $_$
        declare
            res text;
            key_digest bytea;
        BEGIN
            key_digest = digest($2, 'sha256');
            select
                convert_from(
                    rtrim(
                        decrypt_iv(
                            decode($1, 'base64'),
                            key_digest,
                            substring(key_digest, 1, 16),
                            'aes-cbc/pad:none'
                        ),
                        '*'::bytea
                    ),
                    'UTF8'
                )
            into res;
        
            return res;
        end;
        $_$;


ALTER FUNCTION public.decrypt_internal(text, bytea) OWNER TO backend;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activities; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.activities (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    name character varying(100),
    description jsonb,
    splash_screen text,
    image text,
    show_all_at_once boolean,
    is_skippable boolean,
    is_reviewable boolean,
    response_is_editable boolean,
    "order" real,
    id uuid NOT NULL,
    applet_id uuid NOT NULL,
    is_hidden boolean,
    scores_and_reports jsonb,
    subscale_setting jsonb,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    report_included_item_name text,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    performance_task_type character varying(255)
);


ALTER TABLE public.activities OWNER TO backend;

--
-- Name: activity_events; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.activity_events (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    id uuid NOT NULL,
    activity_id uuid NOT NULL,
    event_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.activity_events OWNER TO backend;

--
-- Name: activity_histories; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.activity_histories (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    name character varying(100),
    description jsonb,
    splash_screen text,
    image text,
    show_all_at_once boolean,
    is_skippable boolean,
    is_reviewable boolean,
    response_is_editable boolean,
    "order" real,
    id_version character varying NOT NULL,
    applet_id character varying NOT NULL,
    id uuid,
    is_hidden boolean,
    scores_and_reports jsonb,
    subscale_setting jsonb,
    report_included_item_name text,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    performance_task_type character varying(255)
);


ALTER TABLE public.activity_histories OWNER TO backend;

--
-- Name: activity_item_histories; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.activity_item_histories (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    question jsonb,
    response_type text,
    "order" real,
    id_version character varying NOT NULL,
    activity_id character varying NOT NULL,
    id uuid,
    config jsonb,
    name text NOT NULL,
    response_values jsonb,
    is_hidden boolean,
    conditional_logic jsonb,
    allow_edit boolean,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.activity_item_histories OWNER TO backend;

--
-- Name: activity_items; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.activity_items (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    question jsonb,
    response_type text,
    "order" real,
    id uuid NOT NULL,
    activity_id uuid NOT NULL,
    config jsonb,
    name text NOT NULL,
    response_values jsonb,
    is_hidden boolean,
    conditional_logic jsonb,
    allow_edit boolean,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.activity_items OWNER TO backend;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO backend;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.alerts (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    respondent_id uuid,
    is_watched boolean NOT NULL,
    applet_id uuid NOT NULL,
    alert_message character varying NOT NULL,
    user_id uuid NOT NULL,
    version character varying,
    activity_id uuid,
    activity_item_id uuid,
    answer_id uuid,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    subject_id uuid
);


ALTER TABLE public.alerts OWNER TO backend;

--
-- Name: answer_notes; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.answer_notes (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    answer_id uuid,
    note character varying,
    user_id uuid,
    activity_id uuid,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.answer_notes OWNER TO backend;

--
-- Name: answers; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.answers (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    applet_id uuid,
    respondent_id uuid,
    version text,
    submit_id uuid,
    applet_history_id character varying NOT NULL,
    flow_history_id character varying,
    activity_history_id character varying NOT NULL,
    client jsonb,
    is_flow_completed boolean,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    migrated_data jsonb,
    target_subject_id uuid,
    source_subject_id uuid,
    relation character varying(20)
);


ALTER TABLE public.answers OWNER TO backend;

--
-- Name: answers_items; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.answers_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    is_deleted boolean,
    answer_id uuid,
    answer text,
    item_ids jsonb,
    events text,
    respondent_id uuid,
    identifier text,
    user_public_key text,
    scheduled_datetime timestamp without time zone,
    start_datetime timestamp without time zone NOT NULL,
    end_datetime timestamp without time zone NOT NULL,
    is_assessment boolean,
    scheduled_event_id text,
    local_end_date date,
    local_end_time time without time zone,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    migrated_data jsonb,
    assessment_activity_id text,
    tz_offset integer
);


ALTER TABLE public.answers_items OWNER TO backend;

--
-- Name: COLUMN answers_items.tz_offset; Type: COMMENT; Schema: public; Owner: backend
--

COMMENT ON COLUMN public.answers_items.tz_offset IS 'Local timezone offset in minutes';


--
-- Name: applet_histories; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.applet_histories (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    description jsonb,
    about jsonb,
    image character varying(255),
    watermark character varying(255),
    version character varying(255),
    report_server_ip text,
    report_public_key text,
    report_recipients jsonb,
    report_include_user_id boolean,
    report_include_case_id boolean,
    report_email_body text,
    id_version character varying NOT NULL,
    display_name character varying(100),
    id uuid,
    theme_id uuid,
    user_id uuid NOT NULL,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    stream_enabled boolean,
    stream_ip_address character varying(50),
    stream_port integer
);


ALTER TABLE public.applet_histories OWNER TO backend;

--
-- Name: applets; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.applets (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    display_name character varying(100),
    description jsonb,
    about jsonb,
    image character varying(255),
    watermark character varying(255),
    version character varying(255),
    report_server_ip text,
    report_public_key text,
    report_recipients jsonb,
    report_include_user_id boolean,
    report_include_case_id boolean,
    report_email_body text,
    link uuid,
    require_login boolean,
    pinned_at timestamp without time zone,
    id uuid NOT NULL,
    theme_id uuid,
    retention_period integer,
    retention_type character varying(20),
    encryption jsonb,
    is_published boolean,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    stream_enabled boolean,
    creator_id uuid,
    stream_ip_address character varying(50),
    stream_port integer
);


ALTER TABLE public.applets OWNER TO backend;

--
-- Name: cart; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.cart (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    is_deleted boolean,
    user_id uuid NOT NULL,
    cart_items jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.cart OWNER TO backend;

--
-- Name: events; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.events (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    start_time time without time zone,
    end_time time without time zone,
    access_before_schedule boolean,
    one_time_completion boolean,
    timer interval,
    timer_type character varying(10) NOT NULL,
    id uuid NOT NULL,
    periodicity_id uuid NOT NULL,
    applet_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.events OWNER TO backend;

--
-- Name: flow_events; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.flow_events (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    id uuid NOT NULL,
    flow_id uuid NOT NULL,
    event_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.flow_events OWNER TO backend;

--
-- Name: flow_histories; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.flow_histories (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    name text,
    description jsonb,
    is_single_report boolean,
    hide_badge boolean,
    "order" real,
    id_version character varying NOT NULL,
    applet_id character varying,
    id uuid,
    is_hidden boolean,
    report_included_activity_name text,
    report_included_item_name text,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.flow_histories OWNER TO backend;

--
-- Name: flow_item_histories; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.flow_item_histories (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    "order" real,
    id_version character varying NOT NULL,
    activity_flow_id character varying,
    activity_id character varying,
    id uuid,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.flow_item_histories OWNER TO backend;

--
-- Name: flow_items; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.flow_items (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    "order" real,
    id uuid NOT NULL,
    activity_flow_id uuid,
    activity_id uuid,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.flow_items OWNER TO backend;

--
-- Name: flows; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.flows (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    name text,
    description jsonb,
    is_single_report boolean,
    hide_badge boolean,
    "order" real,
    id uuid NOT NULL,
    applet_id uuid,
    is_hidden boolean,
    extra_fields jsonb DEFAULT '{}'::jsonb,
    report_included_activity_name text,
    report_included_item_name text,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.flows OWNER TO backend;

--
-- Name: folder_applets; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.folder_applets (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    folder_id uuid NOT NULL,
    applet_id uuid NOT NULL,
    pinned_at timestamp without time zone,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.folder_applets OWNER TO backend;

--
-- Name: folders; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.folders (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    name character varying(255),
    id uuid NOT NULL,
    creator_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.folders OWNER TO backend;

--
-- Name: invitations; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.invitations (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    email character varying,
    role character varying,
    key uuid,
    status character varying,
    id uuid NOT NULL,
    applet_id uuid NOT NULL,
    invitor_id uuid NOT NULL,
    meta jsonb,
    first_name character varying,
    last_name character varying,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    nickname character varying,
    user_id uuid
);


ALTER TABLE public.invitations OWNER TO backend;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    is_deleted boolean,
    name text NOT NULL,
    creator_id uuid NOT NULL,
    status public.job_status NOT NULL,
    details jsonb
);


ALTER TABLE public.jobs OWNER TO backend;

--
-- Name: library; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.library (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    is_deleted boolean,
    applet_id_version character varying NOT NULL,
    keywords character varying[],
    search_keywords character varying[],
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.library OWNER TO backend;

--
-- Name: notification_logs; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.notification_logs (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    user_id character varying NOT NULL,
    device_id character varying NOT NULL,
    action_type character varying NOT NULL,
    notification_descriptions jsonb,
    notification_in_queue jsonb,
    scheduled_notifications jsonb,
    notification_descriptions_updated boolean NOT NULL,
    notifications_in_queue_updated boolean NOT NULL,
    scheduled_notifications_updated boolean NOT NULL,
    id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.notification_logs OWNER TO backend;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.notifications (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    event_id uuid NOT NULL,
    from_time time without time zone,
    to_time time without time zone,
    at_time time without time zone,
    trigger_type character varying(10) NOT NULL,
    "order" integer,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.notifications OWNER TO backend;

--
-- Name: periodicity; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.periodicity (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    type character varying(10) NOT NULL,
    start_date date,
    end_date date,
    id uuid NOT NULL,
    selected_date date,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.periodicity OWNER TO backend;

--
-- Name: reminders; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.reminders (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    event_id uuid NOT NULL,
    activity_incomplete integer NOT NULL,
    reminder_time time without time zone NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.reminders OWNER TO backend;

--
-- Name: reusable_item_choices; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.reusable_item_choices (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    token_name character varying(100) NOT NULL,
    token_value integer NOT NULL,
    input_type character varying(20) NOT NULL,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.reusable_item_choices OWNER TO backend;

--
-- Name: subject_relations; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.subject_relations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    is_deleted boolean,
    source_subject_id uuid NOT NULL,
    target_subject_id uuid NOT NULL,
    relation character varying(20) NOT NULL
);


ALTER TABLE public.subject_relations OWNER TO backend;

--
-- Name: subjects; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.subjects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    is_deleted boolean,
    applet_id uuid NOT NULL,
    creator_id uuid NOT NULL,
    user_id uuid,
    language character varying(20),
    email character varying,
    nickname character varying,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    secret_user_id character varying NOT NULL
);


ALTER TABLE public.subjects OWNER TO backend;

--
-- Name: themes; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.themes (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    name character varying(100) NOT NULL,
    logo text,
    background_image text,
    primary_color character varying(100),
    secondary_color character varying(100),
    tertiary_color character varying(100),
    public boolean,
    allow_rename boolean,
    id uuid NOT NULL,
    creator_id uuid,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    small_logo text,
    is_default boolean DEFAULT false NOT NULL
);


ALTER TABLE public.themes OWNER TO backend;

--
-- Name: token_blacklist; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.token_blacklist (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    is_deleted boolean,
    jti text NOT NULL,
    user_id uuid NOT NULL,
    exp timestamp without time zone NOT NULL,
    type public.token_purpose NOT NULL,
    rjti text
);


ALTER TABLE public.token_blacklist OWNER TO backend;

--
-- Name: transfer_ownership; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.transfer_ownership (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    email character varying,
    key uuid,
    id uuid NOT NULL,
    applet_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    status character varying DEFAULT 'pending'::character varying,
    from_user_id uuid,
    to_user_id uuid
);


ALTER TABLE public.transfer_ownership OWNER TO backend;

--
-- Name: user_applet_accesses; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.user_applet_accesses (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    role character varying(20) NOT NULL,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    applet_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    invitor_id uuid NOT NULL,
    meta jsonb,
    is_pinned boolean,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    nickname character varying
);


ALTER TABLE public.user_applet_accesses OWNER TO backend;

--
-- Name: user_devices; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.user_devices (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    user_id uuid,
    device_id character varying(255),
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.user_devices OWNER TO backend;

--
-- Name: user_events; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.user_events (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    event_id uuid NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone
);


ALTER TABLE public.user_events OWNER TO backend;

--
-- Name: user_pins; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.user_pins (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, now()),
    is_deleted boolean,
    user_id uuid NOT NULL,
    pinned_user_id uuid,
    owner_id uuid NOT NULL,
    role public.user_pin_role NOT NULL,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    pinned_subject_id uuid
);


ALTER TABLE public.user_pins OWNER TO backend;

--
-- Name: users; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.users (
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    email character varying(100),
    hashed_password character varying(100),
    id uuid NOT NULL,
    first_name character varying,
    last_name character varying,
    last_seen_at timestamp without time zone,
    is_super_admin boolean DEFAULT false,
    is_anonymous_respondent boolean DEFAULT false,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    email_encrypted character varying,
    is_legacy_deleted_respondent boolean DEFAULT false
);


ALTER TABLE public.users OWNER TO backend;

--
-- Name: users_workspaces; Type: TABLE; Schema: public; Owner: backend
--

CREATE TABLE public.users_workspaces (
    id uuid NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_deleted boolean,
    user_id uuid NOT NULL,
    workspace_name character varying NOT NULL,
    is_modified boolean,
    migrated_date timestamp without time zone,
    migrated_updated timestamp without time zone,
    database_uri character varying,
    storage_type character varying,
    storage_access_key character varying,
    storage_secret_key character varying,
    storage_region character varying,
    storage_url character varying,
    storage_bucket character varying,
    use_arbitrary boolean
);


ALTER TABLE public.users_workspaces OWNER TO backend;

--
-- Data for Name: activities; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.activities (created_at, updated_at, is_deleted, name, description, splash_screen, image, show_all_at_once, is_skippable, is_reviewable, response_is_editable, "order", id, applet_id, is_hidden, scores_and_reports, subscale_setting, extra_fields, report_included_item_name, migrated_date, migrated_updated, performance_task_type) FROM stdin;
\.


--
-- Data for Name: activity_events; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.activity_events (created_at, updated_at, is_deleted, id, activity_id, event_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: activity_histories; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.activity_histories (created_at, updated_at, is_deleted, name, description, splash_screen, image, show_all_at_once, is_skippable, is_reviewable, response_is_editable, "order", id_version, applet_id, id, is_hidden, scores_and_reports, subscale_setting, report_included_item_name, extra_fields, migrated_date, migrated_updated, performance_task_type) FROM stdin;
\.


--
-- Data for Name: activity_item_histories; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.activity_item_histories (created_at, updated_at, is_deleted, question, response_type, "order", id_version, activity_id, id, config, name, response_values, is_hidden, conditional_logic, allow_edit, extra_fields, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: activity_items; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.activity_items (created_at, updated_at, is_deleted, question, response_type, "order", id, activity_id, config, name, response_values, is_hidden, conditional_logic, allow_edit, extra_fields, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.alembic_version (version_num) FROM stdin;
01115b529336
\.


--
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.alerts (id, created_at, updated_at, is_deleted, respondent_id, is_watched, applet_id, alert_message, user_id, version, activity_id, activity_item_id, answer_id, migrated_date, migrated_updated, subject_id) FROM stdin;
\.


--
-- Data for Name: answer_notes; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.answer_notes (id, created_at, updated_at, is_deleted, answer_id, note, user_id, activity_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: answers; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.answers (id, created_at, updated_at, is_deleted, applet_id, respondent_id, version, submit_id, applet_history_id, flow_history_id, activity_history_id, client, is_flow_completed, migrated_date, migrated_updated, migrated_data, target_subject_id, source_subject_id, relation) FROM stdin;
\.


--
-- Data for Name: answers_items; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.answers_items (id, created_at, updated_at, is_deleted, answer_id, answer, item_ids, events, respondent_id, identifier, user_public_key, scheduled_datetime, start_datetime, end_datetime, is_assessment, scheduled_event_id, local_end_date, local_end_time, migrated_date, migrated_updated, migrated_data, assessment_activity_id, tz_offset) FROM stdin;
\.


--
-- Data for Name: applet_histories; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.applet_histories (created_at, updated_at, is_deleted, description, about, image, watermark, version, report_server_ip, report_public_key, report_recipients, report_include_user_id, report_include_case_id, report_email_body, id_version, display_name, id, theme_id, user_id, extra_fields, migrated_date, migrated_updated, stream_enabled, stream_ip_address, stream_port) FROM stdin;
\.


--
-- Data for Name: applets; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.applets (created_at, updated_at, is_deleted, display_name, description, about, image, watermark, version, report_server_ip, report_public_key, report_recipients, report_include_user_id, report_include_case_id, report_email_body, link, require_login, pinned_at, id, theme_id, retention_period, retention_type, encryption, is_published, extra_fields, migrated_date, migrated_updated, stream_enabled, creator_id, stream_ip_address, stream_port) FROM stdin;
\.


--
-- Data for Name: cart; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.cart (id, created_at, updated_at, is_deleted, user_id, cart_items, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.events (created_at, updated_at, is_deleted, start_time, end_time, access_before_schedule, one_time_completion, timer, timer_type, id, periodicity_id, applet_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: flow_events; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.flow_events (created_at, updated_at, is_deleted, id, flow_id, event_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: flow_histories; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.flow_histories (created_at, updated_at, is_deleted, name, description, is_single_report, hide_badge, "order", id_version, applet_id, id, is_hidden, report_included_activity_name, report_included_item_name, extra_fields, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: flow_item_histories; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.flow_item_histories (created_at, updated_at, is_deleted, "order", id_version, activity_flow_id, activity_id, id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: flow_items; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.flow_items (created_at, updated_at, is_deleted, "order", id, activity_flow_id, activity_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: flows; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.flows (created_at, updated_at, is_deleted, name, description, is_single_report, hide_badge, "order", id, applet_id, is_hidden, extra_fields, report_included_activity_name, report_included_item_name, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: folder_applets; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.folder_applets (id, created_at, updated_at, is_deleted, folder_id, applet_id, pinned_at, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: folders; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.folders (created_at, updated_at, is_deleted, name, id, creator_id, workspace_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: invitations; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.invitations (created_at, updated_at, is_deleted, email, role, key, status, id, applet_id, invitor_id, meta, first_name, last_name, migrated_date, migrated_updated, nickname, user_id) FROM stdin;
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.jobs (id, created_at, updated_at, migrated_date, migrated_updated, is_deleted, name, creator_id, status, details) FROM stdin;
\.


--
-- Data for Name: library; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.library (id, created_at, updated_at, is_deleted, applet_id_version, keywords, search_keywords, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: notification_logs; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.notification_logs (created_at, updated_at, is_deleted, user_id, device_id, action_type, notification_descriptions, notification_in_queue, scheduled_notifications, notification_descriptions_updated, notifications_in_queue_updated, scheduled_notifications_updated, id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.notifications (id, created_at, updated_at, is_deleted, event_id, from_time, to_time, at_time, trigger_type, "order", migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: periodicity; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.periodicity (created_at, updated_at, is_deleted, type, start_date, end_date, id, selected_date, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: reminders; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.reminders (id, created_at, updated_at, is_deleted, event_id, activity_incomplete, reminder_time, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: reusable_item_choices; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.reusable_item_choices (created_at, updated_at, is_deleted, token_name, token_value, input_type, id, user_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: subject_relations; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.subject_relations (id, created_at, updated_at, migrated_date, migrated_updated, is_deleted, source_subject_id, target_subject_id, relation) FROM stdin;
\.


--
-- Data for Name: subjects; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.subjects (id, created_at, updated_at, migrated_date, migrated_updated, is_deleted, applet_id, creator_id, user_id, language, email, nickname, first_name, last_name, secret_user_id) FROM stdin;
\.


--
-- Data for Name: themes; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.themes (created_at, updated_at, is_deleted, name, logo, background_image, primary_color, secondary_color, tertiary_color, public, allow_rename, id, creator_id, migrated_date, migrated_updated, small_logo, is_default) FROM stdin;
\N	\N	\N	First default theme	\N	\N	#FFFFFF	#000000	#AAAAAA	t	t	06c1d898-9ae2-42c7-b926-93e6e0ac7eb8	\N	\N	\N	\N	t
\.


--
-- Data for Name: token_blacklist; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.token_blacklist (id, created_at, updated_at, migrated_date, migrated_updated, is_deleted, jti, user_id, exp, type, rjti) FROM stdin;
\.


--
-- Data for Name: transfer_ownership; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.transfer_ownership (created_at, updated_at, is_deleted, email, key, id, applet_id, migrated_date, migrated_updated, status, from_user_id, to_user_id) FROM stdin;
\.


--
-- Data for Name: user_applet_accesses; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.user_applet_accesses (created_at, updated_at, is_deleted, role, id, user_id, applet_id, owner_id, invitor_id, meta, is_pinned, migrated_date, migrated_updated, nickname) FROM stdin;
\.


--
-- Data for Name: user_devices; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.user_devices (id, created_at, updated_at, is_deleted, user_id, device_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: user_events; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.user_events (created_at, updated_at, is_deleted, id, user_id, event_id, migrated_date, migrated_updated) FROM stdin;
\.


--
-- Data for Name: user_pins; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.user_pins (id, created_at, updated_at, is_deleted, user_id, pinned_user_id, owner_id, role, migrated_date, migrated_updated, pinned_subject_id) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.users (created_at, updated_at, is_deleted, email, hashed_password, id, first_name, last_name, last_seen_at, is_super_admin, is_anonymous_respondent, migrated_date, migrated_updated, email_encrypted, is_legacy_deleted_respondent) FROM stdin;
\.


--
-- Data for Name: users_workspaces; Type: TABLE DATA; Schema: public; Owner: backend
--

COPY public.users_workspaces (id, created_at, updated_at, is_deleted, user_id, workspace_name, is_modified, migrated_date, migrated_updated, database_uri, storage_type, storage_access_key, storage_secret_key, storage_region, storage_url, storage_bucket, use_arbitrary) FROM stdin;
\.


--
-- Name: activity_events _unique_activity_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_events
    ADD CONSTRAINT _unique_activity_events UNIQUE (activity_id, event_id, is_deleted);


--
-- Name: flow_events _unique_flow_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_events
    ADD CONSTRAINT _unique_flow_events UNIQUE (flow_id, event_id, is_deleted);


--
-- Name: reusable_item_choices _unique_item_choices; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.reusable_item_choices
    ADD CONSTRAINT _unique_item_choices UNIQUE (user_id, token_name, token_value, input_type);


--
-- Name: user_events _unique_user_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_events
    ADD CONSTRAINT _unique_user_events UNIQUE (user_id, event_id, is_deleted);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: activities pk_activities; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT pk_activities PRIMARY KEY (id);


--
-- Name: activity_events pk_activity_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_events
    ADD CONSTRAINT pk_activity_events PRIMARY KEY (id);


--
-- Name: activity_histories pk_activity_histories; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_histories
    ADD CONSTRAINT pk_activity_histories PRIMARY KEY (id_version);


--
-- Name: activity_item_histories pk_activity_item_histories; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_item_histories
    ADD CONSTRAINT pk_activity_item_histories PRIMARY KEY (id_version);


--
-- Name: activity_items pk_activity_items; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_items
    ADD CONSTRAINT pk_activity_items PRIMARY KEY (id);


--
-- Name: alerts pk_alerts; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT pk_alerts PRIMARY KEY (id);


--
-- Name: answer_notes pk_answer_notes; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.answer_notes
    ADD CONSTRAINT pk_answer_notes PRIMARY KEY (id);


--
-- Name: answers pk_answers; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT pk_answers PRIMARY KEY (id);


--
-- Name: answers_items pk_answers_items; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.answers_items
    ADD CONSTRAINT pk_answers_items PRIMARY KEY (id);


--
-- Name: applet_histories pk_applet_histories; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.applet_histories
    ADD CONSTRAINT pk_applet_histories PRIMARY KEY (id_version);


--
-- Name: applets pk_applets; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.applets
    ADD CONSTRAINT pk_applets PRIMARY KEY (id);


--
-- Name: cart pk_cart; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT pk_cart PRIMARY KEY (id);


--
-- Name: events pk_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT pk_events PRIMARY KEY (id);


--
-- Name: flow_events pk_flow_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_events
    ADD CONSTRAINT pk_flow_events PRIMARY KEY (id);


--
-- Name: flow_histories pk_flow_histories; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_histories
    ADD CONSTRAINT pk_flow_histories PRIMARY KEY (id_version);


--
-- Name: flow_item_histories pk_flow_item_histories; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_item_histories
    ADD CONSTRAINT pk_flow_item_histories PRIMARY KEY (id_version);


--
-- Name: flow_items pk_flow_items; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_items
    ADD CONSTRAINT pk_flow_items PRIMARY KEY (id);


--
-- Name: flows pk_flows; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flows
    ADD CONSTRAINT pk_flows PRIMARY KEY (id);


--
-- Name: folder_applets pk_folder_applets; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.folder_applets
    ADD CONSTRAINT pk_folder_applets PRIMARY KEY (id);


--
-- Name: folders pk_folders; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.folders
    ADD CONSTRAINT pk_folders PRIMARY KEY (id);


--
-- Name: invitations pk_invitations; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT pk_invitations PRIMARY KEY (id);


--
-- Name: jobs pk_jobs; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT pk_jobs PRIMARY KEY (id);


--
-- Name: library pk_library; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.library
    ADD CONSTRAINT pk_library PRIMARY KEY (id);


--
-- Name: notification_logs pk_notification_logs; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.notification_logs
    ADD CONSTRAINT pk_notification_logs PRIMARY KEY (id);


--
-- Name: notifications pk_notifications; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT pk_notifications PRIMARY KEY (id);


--
-- Name: periodicity pk_periodicity; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.periodicity
    ADD CONSTRAINT pk_periodicity PRIMARY KEY (id);


--
-- Name: reminders pk_reminders; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT pk_reminders PRIMARY KEY (id);


--
-- Name: reusable_item_choices pk_reusable_item_choices; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.reusable_item_choices
    ADD CONSTRAINT pk_reusable_item_choices PRIMARY KEY (id);


--
-- Name: subject_relations pk_subject_relations; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subject_relations
    ADD CONSTRAINT pk_subject_relations PRIMARY KEY (id);


--
-- Name: subjects pk_subjects; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT pk_subjects PRIMARY KEY (id);


--
-- Name: themes pk_themes; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.themes
    ADD CONSTRAINT pk_themes PRIMARY KEY (id);


--
-- Name: token_blacklist pk_token_blacklist; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.token_blacklist
    ADD CONSTRAINT pk_token_blacklist PRIMARY KEY (id);


--
-- Name: transfer_ownership pk_transfer_ownership; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.transfer_ownership
    ADD CONSTRAINT pk_transfer_ownership PRIMARY KEY (id);


--
-- Name: user_applet_accesses pk_user_applet_accesses; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_applet_accesses
    ADD CONSTRAINT pk_user_applet_accesses PRIMARY KEY (id);


--
-- Name: user_devices pk_user_devices; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_devices
    ADD CONSTRAINT pk_user_devices PRIMARY KEY (id);


--
-- Name: user_events pk_user_events; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_events
    ADD CONSTRAINT pk_user_events PRIMARY KEY (id);


--
-- Name: user_pins pk_user_pins; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_pins
    ADD CONSTRAINT pk_user_pins PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: users_workspaces pk_users_workspaces; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.users_workspaces
    ADD CONSTRAINT pk_users_workspaces PRIMARY KEY (id);


--
-- Name: applets uq_applets_link; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.applets
    ADD CONSTRAINT uq_applets_link UNIQUE (link);


--
-- Name: cart uq_cart_user_id; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT uq_cart_user_id UNIQUE (user_id);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: user_pins user_pins_uq; Type: CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_pins
    ADD CONSTRAINT user_pins_uq UNIQUE (user_id, pinned_user_id, owner_id, role);


--
-- Name: ix_answer_notes_answer_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answer_notes_answer_id ON public.answer_notes USING btree (answer_id);


--
-- Name: ix_answer_notes_user_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answer_notes_user_id ON public.answer_notes USING btree (user_id);


--
-- Name: ix_answers_activity_history_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_activity_history_id ON public.answers USING btree (activity_history_id);


--
-- Name: ix_answers_applet_history_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_applet_history_id ON public.answers USING btree (applet_history_id);


--
-- Name: ix_answers_applet_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_applet_id ON public.answers USING btree (applet_id);


--
-- Name: ix_answers_flow_history_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_flow_history_id ON public.answers USING btree (flow_history_id);


--
-- Name: ix_answers_items_assessment_activity_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_items_assessment_activity_id ON public.answers_items USING btree (assessment_activity_id);


--
-- Name: ix_answers_items_local_end_date; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_items_local_end_date ON public.answers_items USING btree (local_end_date);


--
-- Name: ix_answers_items_respondent_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_items_respondent_id ON public.answers_items USING btree (respondent_id);


--
-- Name: ix_answers_respondent_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_respondent_id ON public.answers USING btree (respondent_id);


--
-- Name: ix_answers_source_subject_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_source_subject_id ON public.answers USING btree (source_subject_id);


--
-- Name: ix_answers_target_subject_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_answers_target_subject_id ON public.answers USING btree (target_subject_id);


--
-- Name: ix_subject_relations_source_subject_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_subject_relations_source_subject_id ON public.subject_relations USING btree (source_subject_id);


--
-- Name: ix_subject_relations_target_subject_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_subject_relations_target_subject_id ON public.subject_relations USING btree (target_subject_id);


--
-- Name: ix_subjects_user_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE UNIQUE INDEX ix_subjects_user_id ON public.subjects USING btree (user_id, applet_id);


--
-- Name: ix_token_blacklist_exp; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_token_blacklist_exp ON public.token_blacklist USING btree (exp);


--
-- Name: ix_token_blacklist_jti; Type: INDEX; Schema: public; Owner: backend
--

CREATE UNIQUE INDEX ix_token_blacklist_jti ON public.token_blacklist USING btree (jti);


--
-- Name: ix_token_blacklist_rjti; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_token_blacklist_rjti ON public.token_blacklist USING btree (rjti);


--
-- Name: ix_user_applet_accesses_applet_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_user_applet_accesses_applet_id ON public.user_applet_accesses USING btree (applet_id);


--
-- Name: ix_user_applet_accesses_role; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_user_applet_accesses_role ON public.user_applet_accesses USING btree (role);


--
-- Name: ix_user_applet_accesses_user_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_user_applet_accesses_user_id ON public.user_applet_accesses USING btree (user_id);


--
-- Name: ix_users_workspaces_user_id; Type: INDEX; Schema: public; Owner: backend
--

CREATE UNIQUE INDEX ix_users_workspaces_user_id ON public.users_workspaces USING btree (user_id);


--
-- Name: ix_users_workspaces_workspace_name; Type: INDEX; Schema: public; Owner: backend
--

CREATE INDEX ix_users_workspaces_workspace_name ON public.users_workspaces USING btree (workspace_name);


--
-- Name: unique_user_applet_role; Type: INDEX; Schema: public; Owner: backend
--

CREATE UNIQUE INDEX unique_user_applet_role ON public.user_applet_accesses USING btree (user_id, applet_id, role);


--
-- Name: unique_user_job_name; Type: INDEX; Schema: public; Owner: backend
--

CREATE UNIQUE INDEX unique_user_job_name ON public.jobs USING btree (creator_id, name);


--
-- Name: uq_subject_relations_source_target; Type: INDEX; Schema: public; Owner: backend
--

CREATE UNIQUE INDEX uq_subject_relations_source_target ON public.subject_relations USING btree (source_subject_id, target_subject_id);


--
-- Name: activities fk_activities_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT fk_activities_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: activity_events fk_activity_events_event_id_events; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_events
    ADD CONSTRAINT fk_activity_events_event_id_events FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: activity_histories fk_activity_histories_applet_id_applet_histories; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_histories
    ADD CONSTRAINT fk_activity_histories_applet_id_applet_histories FOREIGN KEY (applet_id) REFERENCES public.applet_histories(id_version) ON DELETE RESTRICT;


--
-- Name: activity_item_histories fk_activity_item_histories_activity_id_activity_histories; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_item_histories
    ADD CONSTRAINT fk_activity_item_histories_activity_id_activity_histories FOREIGN KEY (activity_id) REFERENCES public.activity_histories(id_version) ON DELETE CASCADE;


--
-- Name: activity_items fk_activity_items_activity_id_activities; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.activity_items
    ADD CONSTRAINT fk_activity_items_activity_id_activities FOREIGN KEY (activity_id) REFERENCES public.activities(id) ON DELETE CASCADE;


--
-- Name: alerts fk_alerts_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: alerts fk_alerts_respondent_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_respondent_id_users FOREIGN KEY (respondent_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: alerts fk_alerts_subject_id_subjects; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_subject_id_subjects FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE RESTRICT;


--
-- Name: alerts fk_alerts_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT fk_alerts_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: answers_items fk_answers_items_answer_id_answers; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.answers_items
    ADD CONSTRAINT fk_answers_items_answer_id_answers FOREIGN KEY (answer_id) REFERENCES public.answers(id) ON DELETE CASCADE;


--
-- Name: applet_histories fk_applet_histories_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.applet_histories
    ADD CONSTRAINT fk_applet_histories_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: applets fk_applets_creator_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.applets
    ADD CONSTRAINT fk_applets_creator_id_users FOREIGN KEY (creator_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: cart fk_cart_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT fk_cart_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: events fk_events_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT fk_events_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE CASCADE;


--
-- Name: events fk_events_periodicity_id_periodicity; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT fk_events_periodicity_id_periodicity FOREIGN KEY (periodicity_id) REFERENCES public.periodicity(id) ON DELETE RESTRICT;


--
-- Name: flow_events fk_flow_events_event_id_events; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_events
    ADD CONSTRAINT fk_flow_events_event_id_events FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: flow_histories fk_flow_histories_applet_id_applet_histories; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_histories
    ADD CONSTRAINT fk_flow_histories_applet_id_applet_histories FOREIGN KEY (applet_id) REFERENCES public.applet_histories(id_version) ON DELETE RESTRICT;


--
-- Name: flow_item_histories fk_flow_item_histories_activity_flow_id_flow_histories; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_item_histories
    ADD CONSTRAINT fk_flow_item_histories_activity_flow_id_flow_histories FOREIGN KEY (activity_flow_id) REFERENCES public.flow_histories(id_version) ON DELETE RESTRICT;


--
-- Name: flow_item_histories fk_flow_item_histories_activity_id_activity_histories; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_item_histories
    ADD CONSTRAINT fk_flow_item_histories_activity_id_activity_histories FOREIGN KEY (activity_id) REFERENCES public.activity_histories(id_version) ON DELETE RESTRICT;


--
-- Name: flow_items fk_flow_items_activity_flow_id_flows; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_items
    ADD CONSTRAINT fk_flow_items_activity_flow_id_flows FOREIGN KEY (activity_flow_id) REFERENCES public.flows(id) ON DELETE RESTRICT;


--
-- Name: flow_items fk_flow_items_activity_id_activities; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flow_items
    ADD CONSTRAINT fk_flow_items_activity_id_activities FOREIGN KEY (activity_id) REFERENCES public.activities(id) ON DELETE RESTRICT;


--
-- Name: flows fk_flows_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.flows
    ADD CONSTRAINT fk_flows_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: folder_applets fk_folder_applets_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.folder_applets
    ADD CONSTRAINT fk_folder_applets_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE CASCADE;


--
-- Name: folder_applets fk_folder_applets_folder_id_folders; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.folder_applets
    ADD CONSTRAINT fk_folder_applets_folder_id_folders FOREIGN KEY (folder_id) REFERENCES public.folders(id) ON DELETE CASCADE;


--
-- Name: folders fk_folders_creator_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.folders
    ADD CONSTRAINT fk_folders_creator_id_users FOREIGN KEY (creator_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: folders fk_folders_workspace_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.folders
    ADD CONSTRAINT fk_folders_workspace_id_users FOREIGN KEY (workspace_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: invitations fk_invitations_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT fk_invitations_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: invitations fk_invitations_invitor_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT fk_invitations_invitor_id_users FOREIGN KEY (invitor_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: invitations fk_invitations_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT fk_invitations_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: jobs fk_jobs_creator_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT fk_jobs_creator_id_users FOREIGN KEY (creator_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: library fk_library_applet_id_version_applet_histories; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.library
    ADD CONSTRAINT fk_library_applet_id_version_applet_histories FOREIGN KEY (applet_id_version) REFERENCES public.applet_histories(id_version) ON DELETE RESTRICT;


--
-- Name: notifications fk_notifications_event_id_events; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT fk_notifications_event_id_events FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: reminders fk_reminders_event_id_events; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT fk_reminders_event_id_events FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: reusable_item_choices fk_reusable_item_choices_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.reusable_item_choices
    ADD CONSTRAINT fk_reusable_item_choices_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: subject_relations fk_subject_relations_source_subject_id_subjects; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subject_relations
    ADD CONSTRAINT fk_subject_relations_source_subject_id_subjects FOREIGN KEY (source_subject_id) REFERENCES public.subjects(id) ON DELETE RESTRICT;


--
-- Name: subject_relations fk_subject_relations_target_subject_id_subjects; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subject_relations
    ADD CONSTRAINT fk_subject_relations_target_subject_id_subjects FOREIGN KEY (target_subject_id) REFERENCES public.subjects(id) ON DELETE RESTRICT;


--
-- Name: subjects fk_subjects_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT fk_subjects_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: subjects fk_subjects_creator_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT fk_subjects_creator_id_users FOREIGN KEY (creator_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: subjects fk_subjects_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT fk_subjects_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: themes fk_themes_creator_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.themes
    ADD CONSTRAINT fk_themes_creator_id_users FOREIGN KEY (creator_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: transfer_ownership fk_transfer_ownership_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.transfer_ownership
    ADD CONSTRAINT fk_transfer_ownership_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: transfer_ownership fk_transfer_ownership_from_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.transfer_ownership
    ADD CONSTRAINT fk_transfer_ownership_from_user_id_users FOREIGN KEY (from_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: transfer_ownership fk_transfer_ownership_to_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.transfer_ownership
    ADD CONSTRAINT fk_transfer_ownership_to_user_id_users FOREIGN KEY (to_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: user_applet_accesses fk_user_applet_accesses_applet_id_applets; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_applet_accesses
    ADD CONSTRAINT fk_user_applet_accesses_applet_id_applets FOREIGN KEY (applet_id) REFERENCES public.applets(id) ON DELETE RESTRICT;


--
-- Name: user_applet_accesses fk_user_applet_accesses_invitor_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_applet_accesses
    ADD CONSTRAINT fk_user_applet_accesses_invitor_id_users FOREIGN KEY (invitor_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: user_applet_accesses fk_user_applet_accesses_owner_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_applet_accesses
    ADD CONSTRAINT fk_user_applet_accesses_owner_id_users FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: user_applet_accesses fk_user_applet_accesses_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_applet_accesses
    ADD CONSTRAINT fk_user_applet_accesses_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: user_devices fk_user_devices_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_devices
    ADD CONSTRAINT fk_user_devices_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_events fk_user_events_event_id_events; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_events
    ADD CONSTRAINT fk_user_events_event_id_events FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: user_events fk_user_events_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_events
    ADD CONSTRAINT fk_user_events_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: user_pins fk_user_pins_owner_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_pins
    ADD CONSTRAINT fk_user_pins_owner_id_users FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_pins fk_user_pins_pinned_subject_id_subjects; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_pins
    ADD CONSTRAINT fk_user_pins_pinned_subject_id_subjects FOREIGN KEY (pinned_subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: user_pins fk_user_pins_pinned_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_pins
    ADD CONSTRAINT fk_user_pins_pinned_user_id_users FOREIGN KEY (pinned_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_pins fk_user_pins_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.user_pins
    ADD CONSTRAINT fk_user_pins_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users_workspaces fk_users_workspaces_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: backend
--

ALTER TABLE ONLY public.users_workspaces
    ADD CONSTRAINT fk_users_workspaces_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: rootUser
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

