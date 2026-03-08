-- Initial schema for SalesMate

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feishu_user_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    company VARCHAR(255),
    stage VARCHAR(50) NOT NULL DEFAULT 'new_contact',
    bant_budget TEXT,
    bant_authority TEXT,
    bant_need TEXT,
    bant_timeline TEXT,
    pain_points JSONB DEFAULT '[]',
    competitors_mentioned JSONB DEFAULT '[]',
    last_contact_at TIMESTAMP WITH TIME ZONE,
    total_interactions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Conversation history table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    intent VARCHAR(50),
    emotion VARCHAR(50),
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Stage transition history
CREATE TABLE IF NOT EXISTS stage_transitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    from_stage VARCHAR(50) NOT NULL,
    to_stage VARCHAR(50) NOT NULL,
    trigger TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_customers_feishu_user ON customers(feishu_user_id);
CREATE INDEX idx_customers_stage ON customers(stage);
CREATE INDEX idx_conversations_customer ON conversations(customer_id, created_at DESC);
CREATE INDEX idx_transitions_customer ON stage_transitions(customer_id, created_at DESC);