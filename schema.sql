-- Class intake survey schema
-- Source: class_dataset.csv (34 rows, 1 submission per netid)
-- Target: PostgreSQL. Normalized to 3NF: repeating multi-value fields
-- (tools, availability) become lookup + junction tables.

BEGIN;

CREATE TYPE school_year_t AS ENUM ('Sophomore', 'Junior', 'Senior');
CREATE TYPE intro_programming_t AS ENUM ('took_it', 'equivalent', 'neither');
CREATE TYPE day_group_t AS ENUM ('Weekday', 'Weekend');
CREATE TYPE time_of_day_t AS ENUM ('mornings', 'afternoons', 'evenings');

-- One student per NYU netid. Names are not unique (two rows share
-- "Dawid Litwiniec" with different netids).
CREATE TABLE students (
    netid               VARCHAR(16) PRIMARY KEY,
    full_name           VARCHAR(120) NOT NULL,
    school_year         school_year_t NOT NULL,
    intro_programming   intro_programming_t NOT NULL,
    skill_programming   SMALLINT NOT NULL
                        CHECK (skill_programming BETWEEN 1 AND 5),
    skill_data_stats    SMALLINT NOT NULL
                        CHECK (skill_data_stats BETWEEN 1 AND 5),
    skill_frontend_design SMALLINT NOT NULL
                        CHECK (skill_frontend_design BETWEEN 1 AND 5),
    skill_business_pitch SMALLINT NOT NULL
                        CHECK (skill_business_pitch BETWEEN 1 AND 5),
    working_style       TEXT NOT NULL,
    interests           TEXT NOT NULL,
    semester_goal       TEXT NOT NULL,
    submitted_at        TIMESTAMPTZ NOT NULL
);

CREATE INDEX students_school_year_idx ON students (school_year);
CREATE INDEX students_submitted_at_idx ON students (submitted_at);

-- Closed list of tools observed in the file:
-- Python, SQL, JavaScript, Excel, R.
-- "none yet" is not a tool; it means the student has zero tool rows.
CREATE TABLE tools (
    tool_id     SMALLSERIAL PRIMARY KEY,
    tool_name   VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE student_tools (
    netid       VARCHAR(16) NOT NULL
                REFERENCES students (netid) ON DELETE CASCADE,
    tool_id     SMALLINT NOT NULL
                REFERENCES tools (tool_id) ON DELETE RESTRICT,
    PRIMARY KEY (netid, tool_id)
);

CREATE INDEX student_tools_tool_id_idx ON student_tools (tool_id);

-- Six closed availability windows from the form.
CREATE TABLE availability_slots (
    slot_id         SMALLSERIAL PRIMARY KEY,
    day_group       day_group_t NOT NULL,
    time_of_day     time_of_day_t NOT NULL,
    UNIQUE (day_group, time_of_day)
);

CREATE TABLE student_availability (
    netid       VARCHAR(16) NOT NULL
                REFERENCES students (netid) ON DELETE CASCADE,
    slot_id     SMALLINT NOT NULL
                REFERENCES availability_slots (slot_id) ON DELETE RESTRICT,
    PRIMARY KEY (netid, slot_id)
);

CREATE INDEX student_availability_slot_id_idx ON student_availability (slot_id);

INSERT INTO tools (tool_name) VALUES
    ('Python'),
    ('SQL'),
    ('JavaScript'),
    ('Excel'),
    ('R');

INSERT INTO availability_slots (day_group, time_of_day) VALUES
    ('Weekday', 'mornings'),
    ('Weekday', 'afternoons'),
    ('Weekday', 'evenings'),
    ('Weekend', 'mornings'),
    ('Weekend', 'afternoons'),
    ('Weekend', 'evenings');

COMMIT;
