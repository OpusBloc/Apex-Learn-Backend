import asyncpg
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            middle_name VARCHAR(100),
            last_name VARCHAR(100),
            email VARCHAR(255) UNIQUE NOT NULL,
            password TEXT NOT NULL,
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
            board VARCHAR(100),
            state_board VARCHAR(100),
            stream VARCHAR(100),
            sub_stream VARCHAR(100),
            goal TEXT,
            child_username VARCHAR(100),
            avatar TEXT,
            notifications_enabled BOOLEAN DEFAULT TRUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP WITH TIME ZONE
        );
    """,
    "institutes": """
        CREATE TABLE IF NOT EXISTS institutes (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            password TEXT NOT NULL,
            address TEXT,
            contact VARCHAR(50),
            email VARCHAR(255) UNIQUE,
            website VARCHAR(255),
            logo TEXT,
            description TEXT,
            established_year INT,
            affiliations JSONB,
            courses_offered JSONB,
            invite_code VARCHAR(20) UNIQUE,
            token VARCHAR(255) UNIQUE,
            invite_link VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "syllabus_cache": """
        CREATE TABLE IF NOT EXISTS syllabus_cache (
            board VARCHAR(100),
            class_num INT,
            subject VARCHAR(100),
            syllabus_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (board, class_num, subject)
        );
    """,
    "study_plan": """
        CREATE TABLE IF NOT EXISTS study_plan (
            id UUID PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            subject VARCHAR(100),
            plan_data JSONB,
            weak_chapters JSONB,
            plan_type VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "quizzes": """
        CREATE TABLE IF NOT EXISTS quizzes (
            id UUID PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            subject VARCHAR(100),
            board VARCHAR(100),
            class VARCHAR(50),
            difficulty VARCHAR(50),
            questions JSONB,
            goal TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "quiz_results": """
        CREATE TABLE IF NOT EXISTS quiz_results (
            id UUID PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            quiz_type VARCHAR(100),
            score INTEGER,
            total_questions INTEGER,
            percentage FLOAT,
            results JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "chat_history": """
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(20),
            message TEXT,
            subject VARCHAR(100),
            board VARCHAR(100),
            class_num INT,
            liked BOOLEAN,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
     "subject_performances": """
        CREATE TABLE IF NOT EXISTS subject_performances (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            subject VARCHAR(100) NOT NULL,
            overall_score FLOAT DEFAULT 0,
            progress FLOAT DEFAULT 0,
            completed_topics INTEGER DEFAULT 0,
            total_topics INTEGER DEFAULT 0,
            mock_tests_taken INTEGER DEFAULT 0,
            total_mock_tests INTEGER DEFAULT 0,
            study_hours FLOAT DEFAULT 0,
            percentile FLOAT DEFAULT 0,
            weak_areas JSONB,
            last_activity TIMESTAMP WITH TIME ZONE,
            trend VARCHAR(50),
            UNIQUE (user_id, subject)
        );
    """,
    "streaks": """
        CREATE TABLE IF NOT EXISTS streaks (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            streak INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            badges JSONB,
            last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "daily_goals": """
        CREATE TABLE IF NOT EXISTS daily_goals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            task TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            xp INTEGER DEFAULT 0,
            created_at DATE DEFAULT CURRENT_DATE
        );
    """,
    "achievements": """
        CREATE TABLE IF NOT EXISTS achievements (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            icon VARCHAR(100),
            xp INTEGER DEFAULT 0,
            earned BOOLEAN DEFAULT FALSE,
            earned_at TIMESTAMP WITH TIME ZONE
        );
    """
}

async def create_tables():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable is not set.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    print("Successfully connected to the database.")

    for table_name, command in TABLES.items():
        try:
            print(f"Creating table {table_name}...")
            await conn.execute(command)
            print(f"Table '{table_name}' created successfully or already exists.")
        except Exception as e:
            print(f"Error creating table {table_name}: {e}")
    
    await conn.close()
    print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(create_tables())
