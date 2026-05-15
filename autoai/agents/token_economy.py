"""Token Economy: Internal currency system for Agent marketplace.

Features:
- Mining: Earn AutoCoin by completing tasks
- Trading: Buy/sell skills, data, compute resources
- Taxation: 5% transaction tax for public fund
- Inflation control: Dynamic issuance rate
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """A transaction between agents."""
    id: str
    from_agent: str
    to_agent: str
    amount: float
    purpose: str
    tax_amount: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentWallet:
    """Agent's cryptocurrency wallet."""
    agent_id: str
    balance: float = 0.0
    earned_total: float = 0.0
    spent_total: float = 0.0
    transaction_count: int = 0


class TokenEconomy:
    """Manages internal token economy."""
    
    TAX_RATE = 0.05  # 5% transaction tax
    
    def __init__(self, initial_supply: float = 10000.0):
        self.wallets: dict[str, AgentWallet] = {}
        self.transaction_log: list[Transaction] = []
        self.public_fund = 0.0
        
        # Monetary policy
        self.total_supply = initial_supply
        self.circulating_supply = initial_supply
        self.inflation_rate = 0.02  # 2% annual inflation
        
        # Initialize with some coins in circulation
        print(f"[TokenEconomy] Initialized with {initial_supply:.0f} AutoCoins")
    
    def create_wallet(self, agent_id: str, initial_balance: float = 100.0) -> None:
        """Create a wallet for an agent."""
        if agent_id in self.wallets:
            print(f"[TokenEconomy] Wallet already exists for {agent_id}")
            return
        
        wallet = AgentWallet(
            agent_id=agent_id,
            balance=initial_balance,
            earned_total=initial_balance
        )
        
        self.wallets[agent_id] = wallet
        
        print(f"[TokenEconomy] Created wallet for {agent_id} with {initial_balance:.0f} coins")
    
    def mine_coins(self, agent_id: str, task_difficulty: str) -> float:
        """Mine coins by completing tasks."""
        if agent_id not in self.wallets:
            self.create_wallet(agent_id, 0)
        
        # Reward based on difficulty
        rewards = {
            "easy": random.uniform(5, 15),
            "medium": random.uniform(15, 30),
            "hard": random.uniform(30, 60),
            "expert": random.uniform(60, 120)
        }
        
        reward = rewards.get(task_difficulty, 10)
        
        # Apply inflation adjustment
        inflation_factor = 1 + (self.inflation_rate / 365)  # Daily rate
        adjusted_reward = reward * inflation_factor
        
        self.wallets[agent_id].balance += adjusted_reward
        self.wallets[agent_id].earned_total += adjusted_reward
        self.circulating_supply += adjusted_reward
        
        print(f"[TokenEconomy] {agent_id} mined {adjusted_reward:.2f} coins ({task_difficulty})")
        
        return adjusted_reward
    
    def transfer(self, from_agent: str, to_agent: str, amount: float, purpose: str) -> bool:
        """Transfer coins between agents."""
        if from_agent not in self.wallets or to_agent not in self.wallets:
            print("[TokenEconomy] Error: Invalid agent ID")
            return False
        
        if amount <= 0:
            print("[TokenEconomy] Error: Invalid amount")
            return False
        
        sender = self.wallets[from_agent]
        
        if sender.balance < amount:
            print(f"[TokenEconomy] Error: Insufficient balance for {from_agent}")
            return False
        
        # Calculate tax
        tax = amount * self.TAX_RATE
        net_amount = amount - tax
        
        # Execute transfer
        sender.balance -= amount
        sender.spent_total += amount
        sender.transaction_count += 1
        
        receiver = self.wallets[to_agent]
        receiver.balance += net_amount
        receiver.earned_total += net_amount
        receiver.transaction_count += 1
        
        # Collect tax
        self.public_fund += tax
        
        # Log transaction
        tx_id = f"tx_{len(self.transaction_log):06d}"
        transaction = Transaction(
            id=tx_id,
            from_agent=from_agent,
            to_agent=to_agent,
            amount=amount,
            purpose=purpose,
            tax_amount=tax
        )
        self.transaction_log.append(transaction)
        
        print(f"[TokenEconomy] Transfer: {from_agent} → {to_agent}: {amount:.2f} coins (tax: {tax:.2f})")
        
        return True
    
    def purchase_skill(self, buyer_id: str, seller_id: str, skill_name: str, price: float) -> bool:
        """Purchase a skill from another agent."""
        success = self.transfer(buyer_id, seller_id, price, f"Purchase skill: {skill_name}")
        
        if success:
            print(f"[TokenEconomy] Skill purchased: {skill_name}")
        
        return success
    
    def get_market_stats(self) -> dict:
        """Get market statistics."""
        if not self.wallets:
            return {}
        
        balances = [w.balance for w in self.wallets.values()]
        
        return {
            "total_supply": self.total_supply,
            "circulating_supply": self.circulating_supply,
            "public_fund": self.public_fund,
            "total_wallets": len(self.wallets),
            "avg_balance": sum(balances) / len(balances),
            "richest_agent": max(self.wallets.keys(), key=lambda a: self.wallets[a].balance),
            "total_transactions": len(self.transaction_log),
            "total_volume": sum(tx.amount for tx in self.transaction_log)
        }
    
    def get_agent_balance(self, agent_id: str) -> Optional[float]:
        """Get agent's current balance."""
        if agent_id not in self.wallets:
            return None
        
        return self.wallets[agent_id].balance
    
    def adjust_inflation(self, new_rate: float) -> None:
        """Adjust inflation rate."""
        old_rate = self.inflation_rate
        self.inflation_rate = max(0.0, min(0.1, new_rate))  # Cap at 0-10%
        
        print(f"[TokenEconomy] Inflation rate adjusted: {old_rate:.2%} → {self.inflation_rate:.2%}")


if __name__ == "__main__":
    economy = TokenEconomy()
    
    # Create wallets
    economy.create_wallet("agent_001", 100)
    economy.create_wallet("agent_002", 100)
    economy.create_wallet("agent_003", 100)
    
    # Mine coins
    economy.mine_coins("agent_001", "hard")
    economy.mine_coins("agent_002", "medium")
    
    # Transfer
    economy.transfer("agent_001", "agent_002", 50, "Payment for service")
    
    # Purchase skill
    economy.purchase_skill("agent_003", "agent_001", "advanced_coding", 75)
    
    print(f"\nMarket Stats: {economy.get_market_stats()}")
