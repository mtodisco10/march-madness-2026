import re
from collections import defaultdict
from functools import lru_cache

import pandas as pd
import streamlit as st

SEASON = 2026
SUBMISSION_PATH = "submission_2026.csv"

TOURNAMENT_CONFIG = {
    "mens": {
        "label": "Men's Tournament",
        "seeds_path": "data/MNCAATourneySeeds.csv",
        "teams_path": "data/MTeams.csv",
        "slots_path": "data/MNCAATourneySlots.csv",
        "team_name_col": "TeamName",
    },
    "womens": {
        "label": "Women's Tournament",
        "seeds_path": "data/WNCAATourneySeeds.csv",
        "teams_path": "data/WTeams.csv",
        "slots_path": "data/WNCAATourneySlots.csv",
        "team_name_col": "TeamName",
    },
}

REGION_DISPLAY_NAMES = {
    "W": "EAST",
    "X": "SOUTH",
    "Y": "MIDWEST",
    "Z": "WEST",
}


@st.cache_data(show_spinner=False)
def load_submission_lookup(path: str):
    submission = pd.read_csv(path)
    submission[["Season", "TeamLow", "TeamHigh"]] = submission["ID"].str.split("_", expand=True)
    submission["Season"] = submission["Season"].astype(int)
    submission["TeamLow"] = submission["TeamLow"].astype(int)
    submission["TeamHigh"] = submission["TeamHigh"].astype(int)

    season_df = submission[submission["Season"] == SEASON]
    lookup = {
        (int(row.TeamLow), int(row.TeamHigh)): float(row.Pred)
        for row in season_df.itertuples(index=False)
    }
    return lookup


def get_win_prob(team_a: int, team_b: int, pred_lookup: dict[tuple[int, int], float]) -> float:
    low, high = sorted((team_a, team_b))
    pred = pred_lookup.get((low, high))
    if pred is None:
        return 0.5
    return pred if team_a == low else 1.0 - pred


@lru_cache(maxsize=8)
def get_seed_number(seed: str) -> int:
    m = re.search(r"(\d+)", seed)
    return int(m.group(1)) if m else 0


@st.cache_data(show_spinner=False)
def build_tournament(tournament_key: str, pred_lookup: dict[tuple[int, int], float]):
    cfg = TOURNAMENT_CONFIG[tournament_key]

    seeds = pd.read_csv(cfg["seeds_path"])
    teams = pd.read_csv(cfg["teams_path"])
    slots = pd.read_csv(cfg["slots_path"])

    teams = teams.rename(columns={cfg["team_name_col"]: "TeamName"})[["TeamID", "TeamName"]]

    season_seeds = seeds[seeds["Season"] == SEASON].copy()
    season_seeds["BaseSeed"] = season_seeds["Seed"].str.extract(r"^([WXYZ]\d{2})")

    # Keep exactly one team per bracket seed (64 total) by resolving play-in seeds via prediction.
    base_seed_to_team: dict[str, int] = {}
    for base_seed, grp in season_seeds.groupby("BaseSeed"):
        team_ids = grp["TeamID"].tolist()
        if len(team_ids) == 1:
            base_seed_to_team[base_seed] = int(team_ids[0])
            continue
        if len(team_ids) == 2:
            a, b = int(team_ids[0]), int(team_ids[1])
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

    season_slots = slots[
        (slots["Season"] == SEASON) & (slots["Slot"].str.match(r"^R[1-6]"))
    ][["Slot", "StrongSeed", "WeakSeed"]].copy()
    season_slots["Round"] = season_slots["Slot"].str.extract(r"^R(\d)").astype(int)

    slot_map = {
        str(row.Slot): {
            "slot": str(row.Slot),
            "strong": str(row.StrongSeed),
            "weak": str(row.WeakSeed),
            "round": int(row.Round),
        }
        for row in season_slots.itertuples(index=False)
    }

    children = defaultdict(list)
    for slot, info in slot_map.items():
        if info["strong"] in slot_map:
            children[info["strong"]].append(slot)
        if info["weak"] in slot_map:
            children[info["weak"]].append(slot)

    return {
        "label": cfg["label"],
        "seed_teams": seed_teams,
        "slot_map": slot_map,
        "children": dict(children),
        "pred_lookup": pred_lookup,
    }


def format_team_line(team: dict | None, opponent: dict | None, pred_lookup: dict[tuple[int, int], float]) -> str:
    if not team:
        return "TBD"
    pred_text = "--%"
    if opponent:
        pred_text = f"{100.0 * get_win_prob(team['id'], opponent['id'], pred_lookup):.1f}%"
    return f"({get_seed_number(team['seed'])}) {team['name']} {pred_text}"


def inject_bracket_css():
    st.markdown(
        """
        <style>
        .region-title {
            margin-top: 0.25rem;
            margin-bottom: 0.35rem;
            font-weight: 700;
            font-size: 0.95rem;
        }
        .round-title {
            font-size: 0.73rem;
            font-weight: 700;
            color: #334155;
            margin-bottom: 0.28rem;
            letter-spacing: 0.03em;
        }
        .game-shell {
            border: 1px solid #d8dde6;
            border-radius: 8px;
            padding: 0.24rem;
            background: #f8fafc;
            margin-bottom: 0.16rem;
        }
        .game-slot {
            font-size: 0.62rem;
            font-weight: 700;
            color: #4b5563;
            margin-bottom: 0.1rem;
            letter-spacing: 0.01em;
        }
        .v-gap-xs { height: 0.2rem; }
        .v-gap-sm { height: 0.55rem; }
        .v-gap-md { height: 1rem; }
        .v-gap-lg { height: 1.7rem; }
        .offset-r2 { height: 2.0rem; }
        .offset-r3 { height: 4.5rem; }
        .offset-r4 { height: 7.0rem; }
        .gap-r2 { height: 2.9rem; }
        .gap-r3 { height: 5.9rem; }
        .conn-gap-r1 { height: 2.95rem; }
        .conn-gap-r2 { height: 4.45rem; }
        .conn-gap-r3 { height: 5.2rem; }
        .conn-wrap {
            display: flex;
            align-items: center;
            min-height: 4.6rem;
            margin-bottom: 0.22rem;
        }
        .conn-line-r {
            width: 100%;
            height: 2.4rem;
            border-right: 2px solid #94a3b8;
            border-top: 2px solid #94a3b8;
            border-bottom: 2px solid #94a3b8;
            border-radius: 0 7px 7px 0;
        }
        .conn-line-l {
            width: 100%;
            height: 2.4rem;
            border-left: 2px solid #94a3b8;
            border-top: 2px solid #94a3b8;
            border-bottom: 2px solid #94a3b8;
            border-radius: 7px 0 0 7px;
        }
        .mid-conn {
            width: 100%;
            border-top: 2px solid #94a3b8;
            margin: 0.4rem 0;
        }
        .champion {
            margin-top: 0.45rem;
            border: 1px solid #94a3b8;
            border-radius: 10px;
            background: #e2e8f0;
            padding: 0.5rem 0.6rem;
            font-size: 0.85rem;
            font-weight: 700;
            color: #0f172a;
        }
        div[data-testid="stButton"] > button {
            font-size: 0.50rem;
            line-height: 0.95;
            padding-top: 0.14rem;
            padding-bottom: 0.14rem;
            min-height: 1.52rem;
            max-height: 1.52rem;
            height: 1.52rem;
        }
        div[data-testid="stButton"] > button p {
            font-size: 0.50rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            width: 100%;
            margin: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_slot_source_team(
    ref: str,
    winners: dict[str, dict],
    slot_map: dict[str, dict],
    seed_teams: dict[str, dict],
) -> dict | None:
    if ref in seed_teams:
        return seed_teams[ref]
    if ref in slot_map:
        return winners.get(ref)
    return None


def get_slot_matchup(slot: str, t_data: dict, winners: dict[str, dict]) -> tuple[dict | None, dict | None]:
    info = t_data["slot_map"][slot]
    team1 = get_slot_source_team(info["strong"], winners, t_data["slot_map"], t_data["seed_teams"])
    team2 = get_slot_source_team(info["weak"], winners, t_data["slot_map"], t_data["seed_teams"])
    return team1, team2


def clear_descendant_picks(winners: dict[str, dict], children: dict[str, list[str]], slot: str):
    stack = list(children.get(slot, []))
    while stack:
        current = stack.pop()
        winners.pop(current, None)
        stack.extend(children.get(current, []))


def pick_winner(tournament_key: str, t_data: dict, slot: str, team: dict):
    state_key = f"winners_{tournament_key}"
    st.session_state[state_key][slot] = team
    clear_descendant_picks(st.session_state[state_key], t_data["children"], slot)


def render_slot_game(slot: str, tournament_key: str, t_data: dict):
    state_key = f"winners_{tournament_key}"
    winners = st.session_state[state_key]
    team1, team2 = get_slot_matchup(slot, t_data, winners)
    selected = winners.get(slot)

    st.markdown(f"<div class='game-shell'><div class='game-slot'>{slot}</div>", unsafe_allow_html=True)

    team1_label = format_team_line(team1, team2, t_data["pred_lookup"])
    team2_label = format_team_line(team2, team1, t_data["pred_lookup"])

    if st.button(
        team1_label,
        key=f"{tournament_key}_{slot}_top_{team1['id'] if team1 else 'none'}",
        help=team1_label,
        disabled=team1 is None,
        use_container_width=True,
    ):
        pick_winner(tournament_key, t_data, slot, team1)

    if st.button(
        team2_label,
        key=f"{tournament_key}_{slot}_bot_{team2['id'] if team2 else 'none'}",
        help=team2_label,
        disabled=team2 is None,
        use_container_width=True,
    ):
        pick_winner(tournament_key, t_data, slot, team2)

    if selected:
        st.caption(f"Adv: ({get_seed_number(selected['seed'])}) {selected['name']}")

    st.markdown("</div>", unsafe_allow_html=True)


def region_round_slots(region: str, round_num: int) -> list[str]:
    if round_num == 1:
        return [f"R1{region}{n}" for n in [1, 8, 5, 4, 6, 3, 7, 2]]
    if round_num == 2:
        return [f"R2{region}{n}" for n in [1, 2, 3, 4]]
    if round_num == 3:
        return [f"R3{region}{n}" for n in [1, 2]]
    if round_num == 4:
        return [f"R4{region}1"]
    return []


def render_connector_column(direction: str, level: int):
    st.markdown("<div class='round-title'>&nbsp;</div>", unsafe_allow_html=True)
    cls = "conn-line-r" if direction == "ltr" else "conn-line-l"
    if level == 1:
        st.markdown("<div class='offset-r2'></div>", unsafe_allow_html=True)
        for i in range(4):
            st.markdown(f"<div class='conn-wrap'><div class='{cls}'></div></div>", unsafe_allow_html=True)
            if i < 3:
                st.markdown("<div class='gap-r2'></div>", unsafe_allow_html=True)
    elif level == 2:
        st.markdown("<div class='offset-r3'></div>", unsafe_allow_html=True)
        for i in range(2):
            st.markdown(f"<div class='conn-wrap'><div class='{cls}'></div></div>", unsafe_allow_html=True)
            if i == 0:
                st.markdown("<div class='gap-r3'></div>", unsafe_allow_html=True)
    elif level == 3:
        st.markdown("<div class='offset-r4'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='conn-wrap'><div class='{cls}'></div></div>", unsafe_allow_html=True)


def render_round_column(region: str, round_num: int, title: str, tournament_key: str, t_data: dict):
    st.markdown(f"<div class='round-title'>{title}</div>", unsafe_allow_html=True)
    slots = region_round_slots(region, round_num)
    if round_num == 1:
        for i, slot in enumerate(slots):
            render_slot_game(slot, tournament_key, t_data)
            if i % 2 == 1 and i < 7:
                st.markdown("<div class='v-gap-sm'></div>", unsafe_allow_html=True)
    if round_num == 2:
        st.markdown("<div class='offset-r2'></div>", unsafe_allow_html=True)
        for i, slot in enumerate(slots):
            render_slot_game(slot, tournament_key, t_data)
            if i < 3:
                st.markdown("<div class='gap-r2'></div>", unsafe_allow_html=True)
    if round_num == 3:
        st.markdown("<div class='offset-r3'></div>", unsafe_allow_html=True)
        for i, slot in enumerate(slots):
            render_slot_game(slot, tournament_key, t_data)
            if i == 0:
                st.markdown("<div class='gap-r3'></div>", unsafe_allow_html=True)
    if round_num == 4:
        st.markdown("<div class='offset-r4'></div>", unsafe_allow_html=True)
        render_slot_game(slots[0], tournament_key, t_data)


def render_region(region: str, tournament_key: str, t_data: dict, direction: str):
    region_label = REGION_DISPLAY_NAMES.get(region, region)
    st.markdown(f"<div class='region-title'>{region_label}</div>", unsafe_allow_html=True)
    # Keep all round columns the same width for visual consistency.
    if direction == "ltr":
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.0, 0.55, 3.0, 0.55, 3.0, 0.55, 3.0])
    else:
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.0, 0.55, 3.0, 0.55, 3.0, 0.55, 3.0])

    if direction == "ltr":
        with c1:
            render_round_column(region, 1, "ROUND 1", tournament_key, t_data)
        with c2:
            render_connector_column("ltr", 1)
        with c3:
            render_round_column(region, 2, "ROUND 2", tournament_key, t_data)
        with c4:
            render_connector_column("ltr", 2)
        with c5:
            render_round_column(region, 3, "SWEET 16", tournament_key, t_data)
        with c6:
            render_connector_column("ltr", 3)
        with c7:
            render_round_column(region, 4, "ELITE 8", tournament_key, t_data)
        return

    with c1:
        render_round_column(region, 4, "ELITE 8", tournament_key, t_data)
    with c2:
        render_connector_column("rtl", 3)
    with c3:
        render_round_column(region, 3, "SWEET 16", tournament_key, t_data)
    with c4:
        render_connector_column("rtl", 2)
    with c5:
        render_round_column(region, 2, "ROUND 2", tournament_key, t_data)
    with c6:
        render_connector_column("rtl", 1)
    with c7:
        render_round_column(region, 1, "ROUND 1", tournament_key, t_data)


def render_center_game(slot: str, title: str, tournament_key: str, t_data: dict):
    st.markdown(f"<div class='round-title'>{title}</div>", unsafe_allow_html=True)
    render_slot_game(slot, tournament_key, t_data)


def render_center_champion(tournament_key: str):
    champ = st.session_state[f"winners_{tournament_key}"].get("R6CH")
    if champ:
        st.markdown(
            f"<div class='champion'>Champion: ({get_seed_number(champ['seed'])}) {champ['name']}</div>",
            unsafe_allow_html=True,
        )


def render_tournament_tab(tournament_key: str, t_data: dict):
    state_key = f"winners_{tournament_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = {}

    st.caption("Pick winners through all rounds. EAST/SOUTH flow left-to-right, WEST/MIDWEST flow right-to-left.")
    if st.button("Clear picks", key=f"clear_{tournament_key}"):
        st.session_state[state_key] = {}

    left_col, middle_col, right_col = st.columns([5.7, 1.4, 5.7])

    with left_col:
        render_region("W", tournament_key, t_data, "ltr")
        st.markdown("<div class='v-gap-md'></div>", unsafe_allow_html=True)
        render_region("X", tournament_key, t_data, "ltr")

    with middle_col:
        st.markdown("<div class='v-gap-lg'></div>", unsafe_allow_html=True)
        st.markdown("<div class='v-gap-lg'></div>", unsafe_allow_html=True)
        render_center_game("R5WX", "FINAL FOUR", tournament_key, t_data)
        st.markdown("<div class='mid-conn'></div>", unsafe_allow_html=True)
        render_center_game("R6CH", "CHAMPIONSHIP", tournament_key, t_data)
        st.markdown("<div class='mid-conn'></div>", unsafe_allow_html=True)
        render_center_game("R5YZ", "FINAL FOUR", tournament_key, t_data)
        render_center_champion(tournament_key)

    with right_col:
        render_region("Z", tournament_key, t_data, "rtl")
        st.markdown("<div class='v-gap-md'></div>", unsafe_allow_html=True)
        render_region("Y", tournament_key, t_data, "rtl")


def main():
    st.set_page_config(page_title="March Madness Bracket Picker", layout="wide")
    inject_bracket_css()
    st.title("March Madness 2026 Bracket Picker")
    st.write(
        "First-round 64-team view only. Men and Women are split into separate tabs. "
        "Prediction values are shown inline with each team."
    )

    pred_lookup = load_submission_lookup(SUBMISSION_PATH)
    mens = build_tournament("mens", pred_lookup)
    womens = build_tournament("womens", pred_lookup)

    men_tab, women_tab = st.tabs([mens["label"], womens["label"]])

    with men_tab:
        render_tournament_tab("mens", mens)

    with women_tab:
        render_tournament_tab("womens", womens)


if __name__ == "__main__":
    main()
