"""Customer repository implementations for Redis and Postgres storage."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import asyncpg
import redis.asyncio as redis

from ..models.customer import CustomerProfile, SalesStage


class CustomerRepository(ABC):
    """Abstract base class for customer profile repositories."""

    @abstractmethod
    async def create(self, customer: CustomerProfile) -> CustomerProfile:
        """Create a new customer profile."""
        pass

    @abstractmethod
    async def get(self, customer_id: str) -> Optional[CustomerProfile]:
        """Retrieve a customer profile by ID."""
        pass

    @abstractmethod
    async def update(self, customer: CustomerProfile) -> CustomerProfile:
        """Update an existing customer profile."""
        pass

    @abstractmethod
    async def delete(self, customer_id: str) -> bool:
        """Delete a customer profile. Returns True if deleted."""
        pass

    @abstractmethod
    async def list_by_stage(self, stage: SalesStage) -> list[CustomerProfile]:
        """List all customers in a specific sales stage."""
        pass

    @abstractmethod
    async def search_by_email(self, email: str) -> Optional[CustomerProfile]:
        """Find a customer by email address."""
        pass


class RedisCustomerRepository(CustomerRepository):
    """Redis-based customer repository for caching."""

    KEY_PREFIX = "customer:"
    EMAIL_INDEX_KEY = "customer:email_index"
    STAGE_INDEX_PREFIX = "customer:stage:"

    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        """
        Initialize Redis customer repository.

        Args:
            redis_client: Redis client instance
            ttl: Time-to-live in seconds for cached entries (default 1 hour)
        """
        self.redis = redis_client
        self.ttl = ttl

    def _customer_key(self, customer_id: str) -> str:
        """Generate Redis key for customer profile."""
        return f"{self.KEY_PREFIX}{customer_id}"

    def _stage_key(self, stage: SalesStage) -> str:
        """Generate Redis key for stage index."""
        return f"{self.STAGE_INDEX_PREFIX}{stage.value}"

    async def create(self, customer: CustomerProfile) -> CustomerProfile:
        """Create a new customer profile in Redis."""
        key = self._customer_key(customer.id)
        data = json.dumps(customer.to_dict())

        # Store customer data
        await self.redis.setex(key, self.ttl, data)

        # Update email index
        await self.redis.hset(self.EMAIL_INDEX_KEY, customer.email, customer.id)

        # Update stage index
        await self.redis.sadd(self._stage_key(customer.stage), customer.id)

        return customer

    async def get(self, customer_id: str) -> Optional[CustomerProfile]:
        """Retrieve a customer profile from Redis."""
        key = self._customer_key(customer_id)
        data = await self.redis.get(key)

        if data is None:
            return None

        return CustomerProfile.from_dict(json.loads(data))

    async def update(self, customer: CustomerProfile) -> CustomerProfile:
        """Update an existing customer profile in Redis."""
        customer.updated_at = datetime.utcnow()
        key = self._customer_key(customer.id)
        data = json.dumps(customer.to_dict())

        # Get existing customer to check stage change
        existing = await self.get(customer.id)
        if existing and existing.stage != customer.stage:
            # Update stage index
            await self.redis.srem(self._stage_key(existing.stage), customer.id)
            await self.redis.sadd(self._stage_key(customer.stage), customer.id)

        # Update customer data
        await self.redis.setex(key, self.ttl, data)

        return customer

    async def delete(self, customer_id: str) -> bool:
        """Delete a customer profile from Redis."""
        customer = await self.get(customer_id)
        if customer is None:
            return False

        key = self._customer_key(customer_id)

        # Remove from indexes
        await self.redis.hdel(self.EMAIL_INDEX_KEY, customer.email)
        await self.redis.srem(self._stage_key(customer.stage), customer_id)

        # Delete customer data
        result = await self.redis.delete(key)
        return result > 0

    async def list_by_stage(self, stage: SalesStage) -> list[CustomerProfile]:
        """List all customers in a specific sales stage from Redis."""
        stage_key = self._stage_key(stage)
        customer_ids = await self.redis.smembers(stage_key)

        customers = []
        for cid in customer_ids:
            customer_id = cid.decode() if isinstance(cid, bytes) else cid
            customer = await self.get(customer_id)
            if customer:
                customers.append(customer)

        return customers

    async def search_by_email(self, email: str) -> Optional[CustomerProfile]:
        """Find a customer by email address from Redis."""
        customer_id = await self.redis.hget(self.EMAIL_INDEX_KEY, email)
        if customer_id is None:
            return None

        customer_id = customer_id.decode() if isinstance(customer_id, bytes) else customer_id
        return await self.get(customer_id)


class PostgresCustomerRepository(CustomerRepository):
    """Postgres-based customer repository for persistent storage."""

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS customers (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        company VARCHAR(255),
        stage VARCHAR(50) NOT NULL DEFAULT 'new_contact',
        bant JSONB DEFAULT '{}',
        pain_points TEXT[] DEFAULT '{}',
        competitors TEXT[] DEFAULT '{}',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
    CREATE INDEX IF NOT EXISTS idx_customers_stage ON customers(stage);
    """

    def __init__(self, pool: asyncpg.Pool):
        """Initialize Postgres customer repository."""
        self.pool = pool

    async def init_schema(self) -> None:
        """Initialize database schema."""
        async with self.pool.acquire() as conn:
            await conn.execute(self.CREATE_TABLE_SQL)

    async def create(self, customer: CustomerProfile) -> CustomerProfile:
        """Create a new customer profile in Postgres."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO customers 
                (id, name, email, company, stage, bant, pain_points, competitors, notes, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                customer.id,
                customer.name,
                customer.email,
                customer.company,
                customer.stage.value,
                json.dumps(customer.bant.__dict__)
                if hasattr(customer.bant, "__dict__")
                else customer.bant,
                customer.pain_points,
                customer.competitors,
                customer.notes,
                customer.created_at,
                customer.updated_at,
            )
        return customer

    async def get(self, customer_id: str) -> Optional[CustomerProfile]:
        """Retrieve a customer profile from Postgres."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM customers WHERE id = $1",
                customer_id,
            )

        if row is None:
            return None

        return self._row_to_customer(row)

    async def update(self, customer: CustomerProfile) -> CustomerProfile:
        """Update an existing customer profile in Postgres."""
        customer.updated_at = datetime.utcnow()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE customers 
                SET name = $2, email = $3, company = $4, stage = $5, 
                    bant = $6, pain_points = $7, competitors = $8, 
                    notes = $9, updated_at = $10
                WHERE id = $1
                """,
                customer.id,
                customer.name,
                customer.email,
                customer.company,
                customer.stage.value,
                json.dumps(customer.bant.__dict__)
                if hasattr(customer.bant, "__dict__")
                else customer.bant,
                customer.pain_points,
                customer.competitors,
                customer.notes,
                customer.updated_at,
            )

        return customer

    async def delete(self, customer_id: str) -> bool:
        """Delete a customer profile from Postgres."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM customers WHERE id = $1",
                customer_id,
            )
        return result == "DELETE 1"

    async def list_by_stage(self, stage: SalesStage) -> list[CustomerProfile]:
        """List all customers in a specific sales stage from Postgres."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM customers WHERE stage = $1 ORDER BY updated_at DESC",
                stage.value,
            )

        return [self._row_to_customer(row) for row in rows]

    async def search_by_email(self, email: str) -> Optional[CustomerProfile]:
        """Find a customer by email address from Postgres."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM customers WHERE email = $1",
                email,
            )

        if row is None:
            return None

        return self._row_to_customer(row)

    def _row_to_customer(self, row: asyncpg.Record) -> CustomerProfile:
        """Convert a database row to a CustomerProfile."""
        from ..models.customer import BANTProfile

        bant_data = row["bant"] or {}
        bant = BANTProfile(
            budget=bant_data.get("budget"),
            budget_confirmed=bant_data.get("budget_confirmed", False),
            authority=bant_data.get("authority"),
            authority_level=bant_data.get("authority_level"),
            need=bant_data.get("need"),
            need_urgency=bant_data.get("need_urgency"),
            timeline=bant_data.get("timeline"),
            timeline_confirmed=bant_data.get("timeline_confirmed", False),
        )

        return CustomerProfile(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            company=row["company"] or "",
            stage=SalesStage(row["stage"]),
            bant=bant,
            pain_points=list(row["pain_points"]) if row["pain_points"] else [],
            competitors=list(row["competitors"]) if row["competitors"] else [],
            notes=row["notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class HybridCustomerRepository(CustomerRepository):
    """
    Hybrid repository using Redis for caching and Postgres for persistence.

    Read operations check cache first, then fall back to database.
    Write operations persist to database and update cache.
    """

    def __init__(
        self,
        redis_repo: RedisCustomerRepository,
        postgres_repo: PostgresCustomerRepository,
    ):
        """Initialize hybrid repository with Redis and Postgres repos."""
        self.redis_repo = redis_repo
        self.postgres_repo = postgres_repo

    async def create(self, customer: CustomerProfile) -> CustomerProfile:
        """Create customer in Postgres and cache in Redis."""
        # Persist to database first
        created = await self.postgres_repo.create(customer)
        # Cache in Redis
        await self.redis_repo.create(created)
        return created

    async def get(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer from cache first, then database."""
        # Try cache first
        customer = await self.redis_repo.get(customer_id)
        if customer:
            return customer

        # Fall back to database
        customer = await self.postgres_repo.get(customer_id)
        if customer:
            # Cache the result
            await self.redis_repo.create(customer)

        return customer

    async def update(self, customer: CustomerProfile) -> CustomerProfile:
        """Update customer in Postgres and refresh cache."""
        # Update database first
        updated = await self.postgres_repo.update(customer)
        # Update cache
        await self.redis_repo.update(updated)
        return updated

    async def delete(self, customer_id: str) -> bool:
        """Delete customer from both Postgres and Redis."""
        # Delete from cache first
        await self.redis_repo.delete(customer_id)
        # Delete from database
        return await self.postgres_repo.delete(customer_id)

    async def list_by_stage(self, stage: SalesStage) -> list[CustomerProfile]:
        """List customers by stage from database (not cached)."""
        return await self.postgres_repo.list_by_stage(stage)

    async def search_by_email(self, email: str) -> Optional[CustomerProfile]:
        """Search by email from cache first, then database."""
        # Try cache first
        customer = await self.redis_repo.search_by_email(email)
        if customer:
            return customer

        # Fall back to database
        customer = await self.postgres_repo.search_by_email(email)
        if customer:
            # Cache the result
            await self.redis_repo.create(customer)

        return customer

    async def invalidate_cache(self, customer_id: str) -> bool:
        """Invalidate cache for a specific customer."""
        return await self.redis_repo.delete(customer_id)

    async def refresh_cache(self, customer_id: str) -> Optional[CustomerProfile]:
        """Refresh cache for a customer from database."""
        customer = await self.postgres_repo.get(customer_id)
        if customer:
            await self.redis_repo.create(customer)
        return customer
