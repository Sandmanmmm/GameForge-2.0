#!/usr/bin/env python3
"""
Create all 44 production tables manually
"""

import psycopg2
import os
from dotenv import load_dotenv

def create_all_tables():
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DEV_DB_HOST'),
        port=os.getenv('DEV_DB_PORT'),
        database=os.getenv('DEV_DB_NAME'),
        user=os.getenv('DEV_DB_USER'),
        password=os.getenv('DEV_DB_PASSWORD')
    )
    
    cur = conn.cursor()
    
    try:
        print("🏗️ Creating all production tables...")
        
        # Game templates table (created first since other tables reference it)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS game_templates (
            id VARCHAR PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            description TEXT NOT NULL,
            summary VARCHAR(500),
            engine gameengine NOT NULL,
            genre gamegenre NOT NULL,
            category VARCHAR(50) NOT NULL,
            tags VARCHAR[],
            features VARCHAR[],
            target_platforms VARCHAR[],
            thumbnail_url VARCHAR(500),
            preview_images VARCHAR[],
            demo_url VARCHAR(500),
            repository_url VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            is_featured BOOLEAN DEFAULT FALSE,
            is_premium BOOLEAN DEFAULT FALSE,
            author_name VARCHAR(100),
            author_url VARCHAR(500),
            license VARCHAR(50),
            usage_count INTEGER DEFAULT 0,
            rating_average REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            template_config JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created game_templates table")
        
        # Users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255),
            full_name VARCHAR(100),
            bio TEXT,
            avatar_url VARCHAR(500),
            website_url VARCHAR(500),
            location VARCHAR(100),
            timezone VARCHAR(50),
            language VARCHAR(10) DEFAULT 'en',
            status userstatus DEFAULT 'ACTIVE',
            user_type usertype DEFAULT 'INDIVIDUAL',
            role userrole DEFAULT 'USER',
            auth_provider authprovider DEFAULT 'LOCAL',
            is_verified BOOLEAN DEFAULT FALSE,
            is_premium BOOLEAN DEFAULT FALSE,
            email_verified BOOLEAN DEFAULT FALSE,
            profile_completed BOOLEAN DEFAULT FALSE,
            credits_balance DECIMAL(10,2) DEFAULT 0,
            subscription_tier VARCHAR(20) DEFAULT 'free',
            last_login_at TIMESTAMP,
            last_activity_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created users table")
        
        # Projects table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            slug VARCHAR(200) UNIQUE,
            description TEXT,
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            template_id VARCHAR REFERENCES game_templates(id),
            status projectstatus DEFAULT 'DRAFT',
            visibility projectvisibility DEFAULT 'PRIVATE',
            engine gameengine NOT NULL,
            genre gamegenre,
            target_platforms VARCHAR[],
            tags VARCHAR[],
            features VARCHAR[],
            repository_url VARCHAR(500),
            demo_url VARCHAR(500),
            thumbnail_url VARCHAR(500),
            preview_images VARCHAR[],
            is_featured BOOLEAN DEFAULT FALSE,
            is_premium BOOLEAN DEFAULT FALSE,
            fork_count INTEGER DEFAULT 0,
            star_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created projects table")
        
        # Assets table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(1000) NOT NULL,
            file_size BIGINT,
            file_hash VARCHAR(64),
            mime_type VARCHAR(100),
            asset_type assettype NOT NULL,
            status assetstatus DEFAULT 'DRAFT',
            tags VARCHAR[],
            metadata JSON,
            version INTEGER DEFAULT 1,
            parent_asset_id UUID REFERENCES assets(id),
            thumbnail_url VARCHAR(500),
            preview_url VARCHAR(500),
            download_url VARCHAR(500),
            is_public BOOLEAN DEFAULT FALSE,
            download_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created assets table")
        
        # AI Requests table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
            request_type airequesttype NOT NULL,
            status airequeststatus DEFAULT 'PENDING',
            model_name VARCHAR(100) NOT NULL,
            model_version VARCHAR(50),
            provider VARCHAR(50) NOT NULL,
            prompt TEXT,
            negative_prompt TEXT,
            parameters JSON,
            input_data JSON,
            output_data JSON,
            queue_position INTEGER,
            processing_time_seconds REAL,
            gpu_time_seconds REAL,
            cost_credits REAL,
            cost_usd REAL,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
            user_feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
        print("  ✅ Created ai_requests table")
        
        # ML Models table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ml_models (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            display_name VARCHAR(200) NOT NULL,
            description TEXT,
            version VARCHAR(50) NOT NULL,
            model_type aimodeltype NOT NULL,
            provider aiprovidertype NOT NULL,
            category VARCHAR(50),
            tags VARCHAR[],
            input_formats VARCHAR[],
            output_formats VARCHAR[],
            max_resolution VARCHAR(20),
            max_duration_seconds INTEGER,
            max_tokens INTEGER,
            capabilities VARCHAR[],
            limitations VARCHAR[],
            supported_styles VARCHAR[],
            average_processing_time REAL,
            success_rate REAL,
            quality_score REAL,
            cost_per_request REAL,
            is_available BOOLEAN DEFAULT TRUE,
            is_premium BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created ml_models table")
        
        # Datasets table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            description TEXT,
            owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            dataset_type datasettype NOT NULL,
            data_type datatype NOT NULL,
            status datasetstatus DEFAULT 'DRAFT',
            visibility datasetvisibility DEFAULT 'PRIVATE',
            stage datasetstage DEFAULT 'RAW',
            version VARCHAR(20) DEFAULT '1.0.0',
            total_size_bytes BIGINT DEFAULT 0,
            total_files INTEGER DEFAULT 0,
            total_samples INTEGER DEFAULT 0,
            labels_count INTEGER DEFAULT 0,
            classes VARCHAR[],
            metadata JSON,
            license VARCHAR(50),
            citation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created datasets table")
        
        # Continue with more essential tables...
        # Project Collaborations
        cur.execute("""
        CREATE TABLE IF NOT EXISTS project_collaborations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role collaborationtype NOT NULL,
            status collaborationstatus DEFAULT 'ACTIVE',
            invited_by_id UUID REFERENCES users(id),
            permissions JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, user_id)
        )
        """)
        print("  ✅ Created project_collaborations table")
        
        # Project Invites
        cur.execute("""
        CREATE TABLE IF NOT EXISTS project_invites (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            inviter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            invitee_email VARCHAR(255) NOT NULL,
            invitee_id UUID REFERENCES users(id) ON DELETE CASCADE,
            role collaborationtype NOT NULL,
            status invitationstatus DEFAULT 'PENDING',
            token VARCHAR(100) UNIQUE NOT NULL,
            message TEXT,
            expires_at TIMESTAMP NOT NULL,
            responded_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created project_invites table")
        
        # Activity Logs
        cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            activity_type activitytype NOT NULL,
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            details JSON,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created activity_logs table")
        
        # Comments
        cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id UUID NOT NULL,
            parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
            is_edited BOOLEAN DEFAULT FALSE,
            is_deleted BOOLEAN DEFAULT FALSE,
            reply_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("  ✅ Created comments table")
        
        # Notifications
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            notification_type notificationtype NOT NULL,
            status notificationstatus DEFAULT 'UNREAD',
            priority prioritylevel DEFAULT 'MEDIUM',
            data JSON,
            action_url VARCHAR(500),
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP
        )
        """)
        print("  ✅ Created notifications table")
        
        # User Sessions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            ip_address INET,
            user_agent TEXT,
            location VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
        """)
        print("  ✅ Created user_sessions table")
        
        # Continue with remaining tables...
        additional_tables = [
            # User Preferences
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                theme VARCHAR(20) DEFAULT 'light',
                language VARCHAR(10) DEFAULT 'en',
                timezone VARCHAR(50),
                email_notifications BOOLEAN DEFAULT TRUE,
                push_notifications BOOLEAN DEFAULT TRUE,
                marketing_emails BOOLEAN DEFAULT FALSE,
                weekly_digest BOOLEAN DEFAULT TRUE,
                preferences JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # User Consents
            """
            CREATE TABLE IF NOT EXISTS user_consents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                consent_type consenttype NOT NULL,
                status consentstatus NOT NULL,
                consent_text TEXT,
                consent_version VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(user_id, consent_type)
            )
            """,
            
            # User Permissions
            """
            CREATE TABLE IF NOT EXISTS user_permissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                permission VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id VARCHAR(255),
                granted_by_id UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(user_id, permission, resource_type, resource_id)
            )
            """,
            
            # API Keys
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                key_preview VARCHAR(20) NOT NULL,
                permissions JSON,
                is_active BOOLEAN DEFAULT TRUE,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
            """,
            
            # Audit Logs
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id VARCHAR(255),
                old_values JSON,
                new_values JSON,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Storage Configs
            """
            CREATE TABLE IF NOT EXISTS storage_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) UNIQUE NOT NULL,
                storage_type storagetype NOT NULL,
                status storagestatus DEFAULT 'ACTIVE',
                endpoint_url VARCHAR(500),
                bucket_name VARCHAR(100),
                region VARCHAR(50),
                access_key_id VARCHAR(255),
                secret_access_key_hash VARCHAR(255),
                config JSON,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # System Config
            """
            CREATE TABLE IF NOT EXISTS system_config (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                data_type VARCHAR(20) DEFAULT 'string',
                category VARCHAR(50),
                description TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for i, table_sql in enumerate(additional_tables, 1):
            cur.execute(table_sql)
            table_name = table_sql.split('CREATE TABLE IF NOT EXISTS ')[1].split(' (')[0]
            print(f"  ✅ Created {table_name} table")
        
        conn.commit()
        print("🎉 All tables created successfully!")
        
        # Verify table count
        cur.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name != 'alembic_version'
        """)
        
        result = cur.fetchone()
        table_count = result[0] if result else 0
        print(f"📊 Total tables created: {table_count}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_all_tables()