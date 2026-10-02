"""Run fights from the command line.

    python -m clockwork.run --deck starter --enemy dummy --fights 1000
    python -m clockwork.run --deck copy_loop --enemy saboteur --seed 3 --trace
"""
import argparse
import statistics

from .agents.greedy_agent import GreedyAgent
from .agents.mcts_agent import MCTSAgent
from .agents.random_agent import RandomAgent
from .decks import ALL_DECKS, DECKS
from .enemies import ENEMIES
from .engine import apply, legal_actions, new_fight, summary

AGENTS = {"random": RandomAgent, "greedy": GreedyAgent, "mcts": MCTSAgent}


def make_agent(spec, seed):
    """'random', 'greedy', 'mcts' or 'mcts@<budget>'."""
    name, _, budget = spec.partition("@")
    if budget:
        return AGENTS[name](seed=seed, budget=int(budget))
    return AGENTS[name](seed=seed)


def play(deck, enemy, seed, agent, trace=False, rules=None):
    kwargs = {} if rules is None else {"rules": rules}
    s = new_fight(ALL_DECKS[deck], enemy, seed=seed, trace=trace, **kwargs)
    while s.result is None:
        apply(s, agent.act(s, legal_actions(s)))
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default="starter", choices=sorted(ALL_DECKS))
    ap.add_argument("--enemy", default="dummy", choices=sorted(ENEMIES))
    ap.add_argument("--agent", default="random", help="random, greedy, mcts or mcts@<budget>")
    ap.add_argument("--fights", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0, help="first fight seed; fight i uses seed+i")
    ap.add_argument("--trace", action="store_true", help="print the full log (single fight)")
    args = ap.parse_args(argv)

    results = []
    for i in range(args.fights):
        agent = make_agent(args.agent, args.seed + i)
        s = play(args.deck, args.enemy, args.seed + i, agent, trace=args.trace and args.fights == 1)
        if s.log is not None:
            print("\n".join(s.log))
        results.append(summary(s))

    wins = sum(r["result"] == "win" for r in results)
    print(f"{args.agent} | {args.deck} vs {args.enemy} | {args.fights} fights | "
          f"win rate {wins / len(results):.1%}")
    for key in ("turns", "total_damage", "max_damage_turn", "max_triggers_turn",
                "overheats", "runaway_turns", "turns_over_turn_cap", "turns_over_part_cap", "hp"):
        vals = [r[key] for r in results]
        print(f"  {key:22s} mean {statistics.mean(vals):7.2f}  max {max(vals)}")


if __name__ == "__main__":
    main()
