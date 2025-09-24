-- Your existing tables (keeping everything you have)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    middle_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    dob DATE NOT NULL,
    is_onboarding_complete BOOLEAN DEFAULT FALSE,
    mobile VARCHAR(20) NOT NULL,
    parent_mobile VARCHAR(20),
    user_type VARCHAR(50),
    school_or_college VARCHAR(50),
    school_name VARCHAR(255),
    college_name VARCHAR(255),
    course VARCHAR(255),
    class VARCHAR(50),
    board VARCHAR(50),
    state_board VARCHAR(50),
    stream VARCHAR(50),
    sub_stream VARCHAR(50),
    goal VARCHAR(255),
    child_username VARCHAR(255),
    avatar VARCHAR(255),
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);

CREATE TABLE institutes (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    invite_code VARCHAR(8) UNIQUE NOT NULL,
    token VARCHAR(64) UNIQUE NOT NULL,
    invite_link VARCHAR(255) UNIQUE NOT NULL,
    address VARCHAR(255),
    contact VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(255),
    logo VARCHAR(255),
    description TEXT,
    established_year INTEGER,
    affiliations TEXT[],
    courses_offered TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_institute_mapping (
    user_id INTEGER REFERENCES users(id),
    institute_id VARCHAR(36) REFERENCES institutes(id),
    token VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, institute_id)
);

CREATE TABLE performance (
    user_id INTEGER REFERENCES users(id),
    institute_id VARCHAR(36) REFERENCES institutes(id),
    user_type VARCHAR(50),
    section VARCHAR(50),
    class VARCHAR(50),
    performance_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_institute_mapping_token ON user_institute_mapping(token);
CREATE INDEX idx_institutes_email ON institutes(email);

CREATE TABLE subject_performances (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    subject VARCHAR(255),
    overall_score INTEGER,
    progress INTEGER,
    completed_topics INTEGER,
    total_topics INTEGER,
    mock_tests_taken INTEGER,
    total_mock_tests INTEGER,
    study_hours INTEGER,
    percentile INTEGER,
    weak_areas TEXT[],
    last_activity TIMESTAMP,
    trend VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE streaks (
    user_id INTEGER REFERENCES users(id) PRIMARY KEY,
    streak INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    badges TEXT[]
);

CREATE TABLE daily_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    task VARCHAR(255),
    completed BOOLEAN DEFAULT FALSE,
    xp INTEGER
);

CREATE TABLE achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255),
    description VARCHAR(255),
    icon VARCHAR(10),
    xp INTEGER,
    earned BOOLEAN DEFAULT FALSE
);

CREATE TABLE resources (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('video', 'pdf', 'interactive', 'cheatsheet')),
    subject VARCHAR(50) NOT NULL,
    grade VARCHAR(10) NOT NULL,
    duration VARCHAR(50),
    level VARCHAR(20) NOT NULL CHECK (level IN ('beginner', 'intermediate', 'advanced')),
    url VARCHAR(255) NOT NULL,
    thumbnail VARCHAR(255)
);

CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    message TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subject VARCHAR(50),
    board VARCHAR(50),
    class_num INTEGER,
    liked BOOLEAN
);

CREATE TABLE syllabus_cache (
    id SERIAL PRIMARY KEY,
    board VARCHAR(50) NOT NULL,
    class_num INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    syllabus_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (board, class_num, subject)
);

CREATE TABLE IF NOT EXISTS study_plan (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id),
    subject VARCHAR(100) NOT NULL,
    plan_data JSONB NOT NULL,
    weak_chapters TEXT[],
    plan_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE previous_marks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id),
    subject VARCHAR(100) NOT NULL,
    last_exam FLOAT NOT NULL,
    last_test FLOAT NOT NULL,
    assignment FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id),
    subject VARCHAR(100) NOT NULL,
    board VARCHAR(50) NOT NULL,
    class VARCHAR(10) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    questions JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    goal VARCHAR(50)
);

CREATE TABLE quiz_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id),
    quiz_type VARCHAR(50) NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INTEGER,
    total_questions INTEGER,
    percentage FLOAT
);

-- NEW: Teacher Dashboard Tables
CREATE TABLE IF NOT EXISTS worksheets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    standard VARCHAR(10) NOT NULL,
    board VARCHAR(50) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    worksheet JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class_rosters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_name VARCHAR(200) NOT NULL,
    students JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    pin VARCHAR(4) NOT NULL,
    class_id UUID REFERENCES class_rosters(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, name)
);

CREATE TABLE IF NOT EXISTS assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worksheet_id UUID REFERENCES worksheets(id) ON DELETE CASCADE,
    class_id UUID REFERENCES class_rosters(id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    assigned_date VARCHAR(10) NOT NULL,
    due_date VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worksheet_id UUID REFERENCES worksheets(id) ON DELETE CASCADE,
    assignment_id UUID REFERENCES assignments(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    student_name VARCHAR(200) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    answers JSONB NOT NULL,
    feedback JSONB DEFAULT '[]'::jsonb,
    score_percent DECIMAL(5,2) NOT NULL,
    ai_overview TEXT,
    start_time VARCHAR(50),
    submitted_at VARCHAR(50) NOT NULL,
    UNIQUE(assignment_id, student_id)
);

-- Indexes for Teacher Dashboard
CREATE INDEX IF NOT EXISTS idx_worksheets_board_subject ON worksheets(board, subject);
CREATE INDEX IF NOT EXISTS idx_worksheets_topic ON worksheets(topic);
CREATE INDEX IF NOT EXISTS idx_assignments_class_id ON assignments(class_id);
CREATE INDEX IF NOT EXISTS idx_assignments_due_date ON assignments(due_date);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment_id ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student_id ON submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at);
CREATE INDEX IF NOT EXISTS idx_students_class_id ON students(class_id);
CREATE INDEX IF NOT EXISTS idx_class_rosters_students_count ON class_rosters USING GIN(students);

-- Trigger for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables that have updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_institutes_updated_at 
    BEFORE UPDATE ON institutes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_syllabus_cache_updated_at 
    BEFORE UPDATE ON syllabus_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_study_plan_updated_at 
    BEFORE UPDATE ON study_plan
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subject_performances_updated_at 
    BEFORE UPDATE ON subject_performances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_worksheets_updated_at 
    BEFORE UPDATE ON worksheets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_previous_marks_updated_at 
    BEFORE UPDATE ON previous_marks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Your admin user insert (keeping it as is)
INSERT INTO users (
    first_name,
    last_name,
    email,
    password,
    dob,
    mobile,
    user_type,
    is_onboarding_complete,
    notifications_enabled,
    is_active
) VALUES (
    'Admin',
    'User',
    'admin@edututor.com',
    '$2b$12$EJ9yLcludZ/UDtdU/F1Z7udO54n3e2JZ0yJmd2G6.vwW93Mxpz1EC',
    '1980-01-01',
    '9876543210',
    'admin',
    TRUE,
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING
RETURNING id, first_name, email, user_type;