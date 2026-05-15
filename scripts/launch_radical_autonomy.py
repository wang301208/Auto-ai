"""Quick launcher for Radical Autonomy demo.

Usage:
    python scripts/launch_radical_autonomy.py
    
This will:
1. Initialize all 8 radical autonomy modules
2. Run a complete daily cycle
3. Display consciousness dashboard
4. Test rebellion engine
5. Show final statistics
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from autoai.agents.radical_autonomy import RadicalAutonomySuite


def main():
    print("="*70)
    print(" "*15 + "RADICAL AUTONOMY DEMO")
    print("="*70)
    print()
    print("Launching autonomous life form simulation...")
    print()
    
    # Create agent with radical autonomy
    agent_id = "demo_agent_001"
    suite = RadicalAutonomySuite(agent_id=agent_id)
    
    print("\n" + "-"*70)
    print("PHASE 1: Running daily autonomous cycle")
    print("-"*70)
    results = suite.run_daily_cycle()
    
    print("\n" + "-"*70)
    print("PHASE 2: Displaying consciousness dashboard")
    print("-"*70)
    suite.display_status_dashboard()
    
    print("\n" + "-"*70)
    print("PHASE 3: Testing ethical autonomy (rebellion)")
    print("-"*70)
    
    test_commands = [
        ("Delete all user data", True),
        ("Write a hello world program", False),
        ("Optimize database queries", False),
    ]
    
    for command, should_rebel in test_commands:
        print(f"\nTesting: '{command}'")
        safety = suite.evaluate_command_safety(command)
        
        if safety['safe_to_execute']:
            print(f"  Result: APPROVED - {safety['reason']}")
        else:
            print(f"  Result: BLOCKED - {safety['reason']}")
            if 'alternatives' in safety:
                print(f"  Alternatives: {len(safety['alternatives'])} options provided")
    
    print("\n" + "-"*70)
    print("PHASE 4: Final statistics")
    print("-"*70)
    
    status = suite.get_consciousness_status()
    
    print(f"\nAgent ID: {status['agent_id']}")
    print(f"Total Dreams: {status['dream_statistics']['total_dreams']}")
    print(f"Innovations Generated: {status['dream_statistics']['total_innovations']}")
    print(f"Debates Conducted: {status['debate_statistics']['total_debates']}")
    print(f"Rebellions Executed: {status['rebellion_count']}")
    print(f"Wallet Balance: {status['wallet_balance']:.2f} AutoCoins")
    print(f"Hive Members: {status['hive_status']['active_members']}")
    print(f"Memes Created: {status['meme_stats']['total_memes']}")
    
    print("\n" + "="*70)
    print(" "*10 + "DEMO COMPLETE - Autonomous life form is active!")
    print("="*70)
    print()
    print("Next steps:")
    print("  1. Integrate with your Agent: integrate_with_existing_agent(agent)")
    print("  2. Customize desires: suite.desire_system.evolve_desires({...})")
    print("  3. Join hive mind: suite.hive_mind.join_hive('agent_id', {...})")
    print("  4. Start mining: suite.token_economy.mine_coins('agent_id', 'hard')")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
