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
) RETURNING id, first_name, email, user_type;


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