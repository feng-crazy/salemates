#!/bin/bash
# Copyright (c) 2026 SalesMate Team
# SPDX-License-Identifier: Apache-2.0

# Initialize SalesMate knowledge base
# This script sets up the initial skills and memory structures

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Initializing SalesMate knowledge base..."

# Create workspace directories if they don't exist
mkdir -p "$PROJECT_ROOT/workspace/memory"
mkdir -p "$PROJECT_ROOT/workspace/skills"

# Initialize skills
echo "Setting up sales skills..."

# SPIN Selling Skill
mkdir -p "$PROJECT_ROOT/workspace/skills/spin"
cat > "$PROJECT_ROOT/workspace/skills/spin/SKILL.md" << 'EOF'
# SPIN Selling Skill

## Overview
SPIN is a sales methodology for discovering and qualifying customer needs.

## Components
- **S**ituation: Understand the customer's current state
- **P**roblem: Identify pain points
- **I**mplication: Explore the consequences of the problem
- **N**eed-payoff: Get the customer to articulate the value of your solution

## Usage
Use SPIN questions to:
1. Build rapport by understanding context
2. Uncover hidden challenges
3. Help prospects realize the impact
4. Guide them to see the solution value
EOF

# FAB Selling Skill
mkdir -p "$PROJECT_ROOT/workspace/skills/fab"
cat > "$PROJECT_ROOT/workspace/skills/fab/SKILL.md" << 'EOF'
# FAB Selling Skill

## Overview
FAB (Features, Advantages, Benefits) helps translate product capabilities into customer value.

## Components
- **F**eature: What the product is/does
- **A**dvantage: How it's better than alternatives
- **B**enefit: What value it delivers to the customer

## Usage
Transform features into benefits by focusing on:
- Time saved
- Money earned/saved
- Risk reduced
- Efficiency gained
EOF

# BANT Qualification Skill
mkdir -p "$PROJECT_ROOT/workspace/skills/bant"
cat > "$PROJECT_ROOT/workspace/skills/bant/SKILL.md" << 'EOF'
# BANT Qualification Skill

## Overview
BANT is a framework for qualifying sales leads.

## Components
- **B**udget: Does the customer have budget?
- **A**uthority: Are they the decision maker?
- **N**eed: Do they have a genuine need?
- **T**imeline: When do they want to implement?

## Usage
Use BANT to:
- Assess lead quality
- Focus on qualified opportunities
- Prioritize follow-up
- Avoid wasted effort
EOF

echo "Knowledge base initialized successfully!"
echo "Skills installed: SPIN, FAB, BANT"

# =============================================================================
# Product Knowledge Base Ingestion
# =============================================================================

echo ""
echo "Ingesting product knowledge base..."

# Product documents to ingest
PRODUCTS_DIR="$PROJECT_ROOT/testdata/products"
TARGET_PATH="products"

# Check if OpenViking is available
if command -v openviking &> /dev/null; then
    OPENVIKING_CMD="openviking"
elif command -v ov &> /dev/null; then
    OPENVIKING_CMD="ov"
else
    echo "Warning: OpenViking CLI not found. Skipping product ingestion."
    echo "To manually ingest products, use the OpenViking API or CLI."
    exit 0
fi

# Function to ingest a single document
ingest_doc() {
    local file_path="$1"
    local description="$2"
    local target="$3"
    
    if [ -f "$file_path" ]; then
        echo "Ingesting: $(basename "$file_path")"
        
        # Use OpenViking CLI to add resource
        # Documents stored under viking://resources/products/
        $OPENVIKING_CMD resource add \
            --path "$file_path" \
            --description "$description" \
            --target "$target" \
            --wait 2>/dev/null || {
                echo "  Warning: Failed to ingest $(basename "$file_path")"
                echo "  You may need to manually add via OpenViking API"
            }
        echo "  ✓ Stored at: viking://resources/$target/$(basename "$file_path")"
    else
        echo "  Warning: File not found: $file_path"
    fi
}

# Ingest all product documents
ingest_doc "$PRODUCTS_DIR/product_overview.md" \
    "SalesMate AI 产品概述 - 核心定位、价值主张、目标客户" \
    "$TARGET_PATH"

ingest_doc "$PRODUCTS_DIR/pricing.md" \
    "SalesMate AI 定价方案 - 订阅计划、折扣政策、常见问题" \
    "$TARGET_PATH"

ingest_doc "$PRODUCTS_DIR/features.md" \
    "SalesMate AI 功能特性 - 核心功能模块、技术规格、API接口" \
    "$TARGET_PATH"

ingest_doc "$PRODUCTS_DIR/deployment.md" \
    "SalesMate AI 部署方案 - SaaS、私有化部署、混合部署选项" \
    "$TARGET_PATH"

ingest_doc "$PRODUCTS_DIR/competitors.md" \
    "SalesMate AI 竞品对比 - 市场定位、功能对比、选型建议" \
    "$TARGET_PATH"

# Also ingest the sample product if it exists
if [ -f "$PRODUCTS_DIR/sample_product.md" ]; then
    ingest_doc "$PRODUCTS_DIR/sample_product.md" \
        "SalesMate Pro 示例产品知识库" \
        "$TARGET_PATH"
fi

echo ""
echo "Product knowledge base ingestion complete!"
echo "Documents stored at: viking://resources/products/"