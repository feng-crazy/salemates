"""Customer repositories for SaleMates agent."""

from .customer_repo import (
    CustomerRepository,
    HybridCustomerRepository,
    PostgresCustomerRepository,
    RedisCustomerRepository,
)

__all__ = [
    "CustomerRepository",
    "HybridCustomerRepository",
    "PostgresCustomerRepository",
    "RedisCustomerRepository",
]
