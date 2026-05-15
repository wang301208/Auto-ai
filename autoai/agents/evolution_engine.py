"""Evolution Engine: Darwinian agent evolution through natural selection.

Implements:
- Mutation: Random parameter changes
- Competition: Multiple agents solve same task
- Selection: Winners reproduce
- Extinction: Losers are destroyed
"""

from __future__ import annotations
import random
import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class AgentGenome:
    """Genetic representation of an Agent."""
    id: str
    generation: int
    fitness: float = 0.0
    temperature: float = 0.7
    top_model: str = "gpt-4"
    skill_combination: list[str] = field(default_factory=list)
    parent_ids: list[str] = field(default_factory=list)
    birth_time: datetime = field(default_factory=datetime.now)
    death_time: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0


@dataclass
class EvolutionEvent:
    """Record of an evolution event."""
    event_type: str  # "mutation", "crossover", "selection", "extinction"
    agent_id: str
    details: dict
    timestamp: datetime = field(default_factory=datetime.now)


class EvolutionEngine:
    """Engine for agent population evolution."""
    
    def __init__(self, population_size: int = 20, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        
        self.population: list[AgentGenome] = []
        self.evolution_history: list[EvolutionEvent] = []
        self.generation_count = 0
        
        # Initialize random population
        self._initialize_population()
        
    def _initialize_population(self) -> None:
        """Initialize population with random agents."""
        models = ["gpt-4", "gpt-3.5", "claude-2", "llama-2"]
        skills = ["coding", "analysis", "writing", "research", "debugging"]
        
        for i in range(self.population_size):
            genome = AgentGenome(
                id=f"agent_{i:03d}",
                generation=0,
                temperature=random.uniform(0.5, 0.9),
                top_model=random.choice(models),
                skill_combination=random.sample(skills, random.randint(1, 3))
            )
            self.population.append(genome)
        
        print(f"[EvolutionEngine] Initialized population of {len(self.population)} agents")
    
    def run_generation(self, task_description: str) -> list[AgentGenome]:
        """Run one generation of evolution."""
        print(f"\n[EvolutionEngine] Starting generation {self.generation_count + 1}")
        
        # Evaluate fitness
        self._evaluate_fitness(task_description)
        
        # Selection
        survivors = self._select_survivors()
        
        # Reproduction
        offspring = self._reproduce(survivors)
        
        # Mutation
        mutated_offspring = self._mutate(offspring)
        
        # Replace population
        self.population = mutated_offspring
        self.generation_count += 1
        
        print(f"[EvolutionEngine] Generation complete. Population: {len(self.population)}")
        
        return self.population
    
    def _evaluate_fitness(self, task: str) -> None:
        """Evaluate fitness of each agent."""
        for agent in self.population:
            # Simulate task performance
            base_performance = random.random()
            
            # Bonus for relevant skills
            skill_bonus = len(agent.skill_combination) * 0.1
            
            # Penalty for extreme temperatures
            temp_penalty = abs(agent.temperature - 0.7) * 0.5
            
            agent.fitness = base_performance + skill_bonus - temp_penalty
            agent.fitness = max(0.0, min(1.0, agent.fitness))
            
            # Record tasks
            if agent.fitness > 0.6:
                agent.tasks_completed += 1
            else:
                agent.tasks_failed += 1
        
        print(f"[EvolutionEngine] Fitness evaluated. Best: {max(a.fitness for a in self.population):.2f}")
    
    def _select_survivors(self) -> list[AgentGenome]:
        """Select survivors based on fitness."""
        # Sort by fitness
        sorted_agents = sorted(self.population, key=lambda a: a.fitness, reverse=True)
        
        # Keep top 50%
        survival_count = self.population_size // 2
        survivors = sorted_agents[:survival_count]
        
        # Record extinctions
        extinct_agents = sorted_agents[survival_count:]
        for agent in extinct_agents:
            agent.death_time = datetime.now()
            self._record_event("extinction", agent.id, {"fitness": agent.fitness})
        
        print(f"[EvolutionEngine] Selected {len(survivors)} survivors, {len(extinct_agents)} extinct")
        
        return survivors
    
    def _reproduce(self, survivors: list[AgentGenome]) -> list[AgentGenome]:
        """Create offspring from survivors."""
        offspring = []
        
        while len(offspring) < self.population_size:
            # Select two parents (tournament selection)
            parent1 = random.choice(survivors[:len(survivors)//2])
            parent2 = random.choice(survivors[:len(survivors)//2])
            
            # Crossover
            child = self._crossover(parent1, parent2)
            offspring.append(child)
            
            self._record_event("crossover", child.id, {
                "parent1": parent1.id,
                "parent2": parent2.id
            })
        
        return offspring
    
    def _crossover(self, parent1: AgentGenome, parent2: AgentGenome) -> AgentGenome:
        """Create child from two parents."""
        child = AgentGenome(
            id=f"agent_gen{self.generation_count + 1}_{random.randint(100, 999)}",
            generation=self.generation_count + 1,
            temperature=(parent1.temperature + parent2.temperature) / 2,
            top_model=random.choice([parent1.top_model, parent2.top_model]),
            skill_combination=list(set(parent1.skill_combination + parent2.skill_combination)),
            parent_ids=[parent1.id, parent2.id]
        )
        
        return child
    
    def _mutate(self, agents: list[AgentGenome]) -> list[AgentGenome]:
        """Apply mutations to agents."""
        models = ["gpt-4", "gpt-3.5", "claude-2", "llama-2"]
        skills = ["coding", "analysis", "writing", "research", "debugging"]
        
        for agent in agents:
            if random.random() < self.mutation_rate:
                # Mutate temperature
                agent.temperature += random.uniform(-0.1, 0.1)
                agent.temperature = max(0.1, min(1.0, agent.temperature))
                
                # Mutate model
                if random.random() < 0.3:
                    agent.top_model = random.choice(models)
                
                # Mutate skills
                if random.random() < 0.3:
                    if random.random() < 0.5 and agent.skill_combination:
                        agent.skill_combination.pop()
                    else:
                        new_skill = random.choice(skills)
                        if new_skill not in agent.skill_combination:
                            agent.skill_combination.append(new_skill)
                
                self._record_event("mutation", agent.id, {
                    "temperature": agent.temperature,
                    "model": agent.top_model,
                    "skills": len(agent.skill_combination)
                })
        
        return agents
    
    def _record_event(self, event_type: str, agent_id: str, details: dict) -> None:
        """Record evolution event."""
        event = EvolutionEvent(
            event_type=event_type,
            agent_id=agent_id,
            details=details
        )
        self.evolution_history.append(event)
    
    def get_evolution_statistics(self) -> dict:
        """Get evolution statistics."""
        if not self.population:
            return {}
        
        avg_fitness = sum(a.fitness for a in self.population) / len(self.population)
        best_agent = max(self.population, key=lambda a: a.fitness)
        
        event_counts = {}
        for event in self.evolution_history:
            etype = event.event_type
            event_counts[etype] = event_counts.get(etype, 0) + 1
        
        return {
            "generation": self.generation_count,
            "population_size": len(self.population),
            "avg_fitness": avg_fitness,
            "best_fitness": best_agent.fitness,
            "best_agent_id": best_agent.id,
            "event_counts": event_counts,
            "total_extinctions": event_counts.get("extinction", 0)
        }


if __name__ == "__main__":
    engine = EvolutionEngine(population_size=10)
    
    # Run 3 generations
    for gen in range(3):
        engine.run_generation("Sample task")
    
    print(f"\nStatistics: {engine.get_evolution_statistics()}")
