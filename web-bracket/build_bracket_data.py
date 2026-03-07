import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

SEASON = 2025
ROOT = Path(__file__).resolve().parents[1]

TOURNAMENTS = {
    "mens": {
        "label": "Men's Tournament",
        "seeds_path": ROOT / "data" / "MNCAATourneySeeds.csv",
        "teams_path": ROOT / "data" / "MTeams.csv",
        "slots_path": ROOT / "data" / "MNCAATourneySlots.csv",
    },
    "womens": {
        "label": "Women's Tournament",
        "seeds_path": ROOT / "data" / "WNCAATourneySeeds.csv",
        "teams_path": ROOT / "data" / "WTeams.csv",
        "slots_path": ROOT / "data" / "WNCAATourneySlots.csv",
    },
}


def build_visual_slot_map():
    slot_map = {}
    regions = ["W", "X", "Y", "Z"]
    r1_order = [1, 8, 5, 4, 6, 3, 7, 2]

    for region in regions:
        for n in range(1, 9):
            slot_map[f"R1{region}{n}"] = {
                "slot": f"R1{region}{n}",
                "strong": f"{region}{n:02d}",
                "weak": f"{region}{17 - n:02d}",
                "round": 1,
            }

        r1_slots_in_display_order = [f"R1{region}{n}" for n in r1_order]
        r2_slots = [f"R2{region}{n}" for n in [1, 2, 3, 4]]
        for i, r2_slot in enumerate(r2_slots):
            slot_map[r2_slot] = {
                "slot": r2_slot,
                "strong": r1_slots_in_display_order[2 * i],
                "weak": r1_slots_in_display_order[2 * i + 1],
                "round": 2,
            }

        slot_map[f"R3{region}1"] = {
            "slot": f"R3{region}1",
            "strong": f"R2{region}1",
            "weak": f"R2{region}2",
            "round": 3,
        }
        slot_map[f"R3{region}2"] = {
            "slot": f"R3{region}2",
            "strong": f"R2{region}4",
            "weak": f"R2{region}3",
            "round": 3,
        }
        slot_map[f"R4{region}1"] = {
            "slot": f"R4{region}1",
            "strong": f"R3{region}1",
            "weak": f"R3{region}2",
            "round": 4,
        }

    slot_map["R5WX"] = {"slot": "R5WX", "strong": "R4W1", "weak": "R4X1", "round": 5}
    slot_map["R5YZ"] = {"slot": "R5YZ", "strong": "R4Y1", "weak": "R4Z1", "round": 5}
    slot_map["R6CH"] = {"slot": "R6CH", "strong": "R5WX", "weak": "R5YZ", "round": 6}
    return slot_map


def load_submission_lookup():
    submission = pd.read_csv(ROOT / "submission_2025.csv")
    parts = submission["ID"].str.split("_", expand=True)
    submission["Season"] = parts[0].astype(int)
    submission["TeamLow"] = parts[1].astype(int)
    submission["TeamHigh"] = parts[2].astype(int)

    season_df = submission[submission["Season"] == SEASON]
    return {
        (int(row.TeamLow), int(row.TeamHigh)): float(row.Pred)
        for row in season_df.itertuples(index=False)
    }


def get_win_prob(team_a, team_b, pred_lookup):
    low, high = sorted((int(team_a), int(team_b)))
    pred = pred_lookup.get((low, high), 0.5)
    return pred if low == int(team_a) else 1.0 - pred


def build_tournament(config, pred_lookup):
    seeds = pd.read_csv(config["seeds_path"])
    teams = pd.read_csv(config["teams_path"])[["TeamID", "TeamName"]]

    season_seeds = seeds[seeds["Season"] == SEASON].copy()
    season_seeds["BaseSeed"] = season_seeds["Seed"].str.extract(r"^([WXYZ]\d{2})")

    base_seed_to_team = {}
    for base_seed, grp in season_seeds.groupby("BaseSeed"):
        team_ids = [int(x) for x in grp["TeamID"].tolist()]
        if len(team_ids) == 1:
            base_seed_to_team[base_seed] = team_ids[0]
        elif len(team_ids) == 2:
            a, b = team_ids
            base_seed_to_team[base_seed] = a if get_win_prob(a, b, pred_lookup) >= 0.5 else b

    seed_team_df = pd.DataFrame(
        [(seed, team_id) for seed, team_id in base_seed_to_team.items()],
        columns=["Seed", "TeamID"],
    ).merge(teams, on="TeamID", how="left")

    seed_teams = {
        str(row.Seed): {
            "id": int(row.TeamID),
            "seed": str(row.Seed),
            "name": str(row.TeamName),
        }
        for row in seed_team_df.itertuples(index=False)
    }

    slot_map = build_visual_slot_map()

    children = defaultdict(list)
    for slot, info in slot_map.items():
        if info["strong"] in slot_map:
            children[info["strong"]].append(slot)
        if info["weak"] in slot_map:
            children[info["weak"]].append(slot)

    team_ids = sorted({v["id"] for v in seed_teams.values()})
    probabilities = {}
    for i, a in enumerate(team_ids):
        for b in team_ids[i + 1 :]:
            key = f"{a}_{b}"
            probabilities[key] = round(get_win_prob(a, b, pred_lookup), 6)

    return {
        "label": config["label"],
        "seedTeams": seed_teams,
        "slotMap": slot_map,
        "children": dict(children),
        "probabilities": probabilities,
    }


def main():
    pred_lookup = load_submission_lookup()

    payload = {"season": SEASON, "tournaments": {}}
    for key, cfg in TOURNAMENTS.items():
        payload["tournaments"][key] = build_tournament(cfg, pred_lookup)

    out_path = Path(__file__).resolve().parent / "bracket_data_2025.json"
    out_path.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
