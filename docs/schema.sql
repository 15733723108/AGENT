-- ============================================================
-- 沧州市劝学路小学智能体 - MySQL 建表脚本（对齐开发文档第 4 章）
-- 目标：MySQL 8.0+，utf8mb4
-- 说明：SQLAlchemy 模型已内置同构定义，本脚本供 DBA 手工建库或 CI 使用；
--       也可以直接用 python scripts/init_db.py 自动建表。
-- ============================================================

CREATE DATABASE IF NOT EXISTS school_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE school_agent;

-- ---------- 用户表 ----------
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(64) NOT NULL COMMENT '登录名',
    password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希(bcrypt)',
    display_name VARCHAR(64) NOT NULL COMMENT '显示名',
    role ENUM('admin','teacher','student','parent') NOT NULL DEFAULT 'student' COMMENT '角色',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB COMMENT='用户表';

-- ---------- 会话表 ----------
CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '会话ID',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '所属用户',
    module ENUM('general','school_info','lesson_plan','exam') NOT NULL COMMENT '所属模块',
    title VARCHAR(200) NOT NULL DEFAULT '' COMMENT '会话标题',
    status TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_user_module (user_id, module)
) ENGINE=InnoDB COMMENT='会话表';

-- ---------- 聊天消息表 ----------
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '消息ID',
    session_id BIGINT UNSIGNED NOT NULL COMMENT '所属会话',
    role ENUM('user','assistant') NOT NULL COMMENT '消息角色',
    content MEDIUMTEXT NOT NULL COMMENT '消息正文',
    refs JSON DEFAULT NULL COMMENT '引用来源列表(学校信息问答)',
    token_count INT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_session (session_id)
) ENGINE=InnoDB COMMENT='聊天消息表';

-- ---------- 知识库文档表 ----------
CREATE TABLE IF NOT EXISTS kb_documents (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '文档ID',
    doc_name VARCHAR(255) NOT NULL COMMENT '文档名',
    category VARCHAR(50) NOT NULL COMMENT '知识域:招生/作息/制度/通知/教材/试卷等',
    file_type VARCHAR(20) NOT NULL COMMENT 'pdf/docx/xlsx/png...',
    file_path VARCHAR(500) NOT NULL COMMENT '存储路径',
    version INT NOT NULL DEFAULT 1,
    is_active TINYINT NOT NULL DEFAULT 1 COMMENT '1有效(参与检索) 0废弃',
    chunk_count INT NOT NULL DEFAULT 0,
    uploader_id BIGINT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_category (category),
    KEY idx_active (is_active)
) ENGINE=InnoDB COMMENT='知识库文档表';

-- ---------- 知识库分块表 ----------
CREATE TABLE IF NOT EXISTS kb_chunks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分块ID',
    doc_id BIGINT UNSIGNED NOT NULL COMMENT '所属文档',
    chunk_index INT NOT NULL COMMENT '块序号',
    content MEDIUMTEXT NOT NULL COMMENT '文本块',
    metadata JSON DEFAULT NULL COMMENT '章节/页码等元数据',
    vector_id VARCHAR(64) DEFAULT NULL COMMENT '向量库主键',
    is_active TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_doc (doc_id)
) ENGINE=InnoDB COMMENT='知识库分块表';

-- ---------- 教案表 ----------
CREATE TABLE IF NOT EXISTS lesson_plans (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '教案ID',
    teacher_id BIGINT UNSIGNED NOT NULL COMMENT '教师ID',
    subject VARCHAR(32) NOT NULL COMMENT '学科',
    grade VARCHAR(32) NOT NULL COMMENT '年级',
    topic VARCHAR(200) NOT NULL COMMENT '课题',
    class_hours TINYINT NOT NULL DEFAULT 1 COMMENT '课时',
    course_type VARCHAR(32) NOT NULL DEFAULT '' COMMENT '课型',
    content_json JSON NOT NULL COMMENT '教案结构化内容',
    status ENUM('draft','done') NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_teacher (teacher_id)
) ENGINE=InnoDB COMMENT='教案表';

-- ---------- 试卷表 ----------
CREATE TABLE IF NOT EXISTS exams (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '试卷ID',
    teacher_id BIGINT UNSIGNED NOT NULL COMMENT '教师ID',
    exam_name VARCHAR(200) NOT NULL COMMENT '试卷名称',
    subject VARCHAR(32) NOT NULL,
    grade VARCHAR(32) NOT NULL,
    source_file VARCHAR(500) NOT NULL DEFAULT '' COMMENT '原卷文件路径',
    question_count INT NOT NULL DEFAULT 0,
    status ENUM('pending','analyzing','done','failed') NOT NULL DEFAULT 'pending',
    error_msg VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_teacher (teacher_id)
) ENGINE=InnoDB COMMENT='试卷表';

-- ---------- 试卷题目表 ----------
CREATE TABLE IF NOT EXISTS exam_questions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '题目ID',
    exam_id BIGINT UNSIGNED NOT NULL COMMENT '所属试卷',
    question_no INT NOT NULL COMMENT '题号',
    question_type VARCHAR(32) NOT NULL DEFAULT '' COMMENT '题型',
    question_text MEDIUMTEXT NOT NULL COMMENT '题干',
    answer MEDIUMTEXT DEFAULT NULL COMMENT '参考答案',
    analysis MEDIUMTEXT DEFAULT NULL COMMENT '解题思路与解析',
    knowledge_points JSON DEFAULT NULL COMMENT '知识点标签数组',
    difficulty TINYINT DEFAULT NULL COMMENT '难度1-5',
    score DECIMAL(5,1) DEFAULT NULL COMMENT '分值',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_exam (exam_id)
) ENGINE=InnoDB COMMENT='试卷题目表';

-- ---------- 研判报告表 ----------
CREATE TABLE IF NOT EXISTS exam_reports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '报告ID',
    exam_id BIGINT UNSIGNED NOT NULL COMMENT '所属试卷',
    report_md MEDIUMTEXT NOT NULL COMMENT '报告正文Markdown',
    stats_json JSON DEFAULT NULL COMMENT '学情统计(得分率/知识点归因)',
    report_file VARCHAR(500) NOT NULL DEFAULT '' COMMENT '导出文件路径',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_exam (exam_id)
) ENGINE=InnoDB COMMENT='研判报告表';

-- ---------- LLM 用量表 ----------
CREATE TABLE IF NOT EXISTS llm_usage (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    user_id BIGINT UNSIGNED DEFAULT NULL,
    module VARCHAR(32) NOT NULL COMMENT '模块名',
    model_name VARCHAR(64) NOT NULL COMMENT '模型名',
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    cost DECIMAL(10,4) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_module_time (module, created_at)
) ENGINE=InnoDB COMMENT='LLM 用量表';
