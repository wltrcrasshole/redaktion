import anthropic
import json

# ── Load data ──────────────────────────────────────────────────────────────────

with open("idea_bank.json", "r", encoding="utf-8") as f:
    idea_bank = json.load(f)

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# ── Helpers ────────────────────────────────────────────────────────────────────

def save_idea_bank():
    with open("idea_bank.json", "w", encoding="utf-8") as f:
        json.dump(idea_bank, f, indent=2, ensure_ascii=False)

def next_id():
    existing = [i["id"] for i in idea_bank["ideas"]]
    return max(existing) + 1 if existing else 1

def get_sections():
    return config["language_sections"]

def get_default_slots(section):
    return config.get("section_slots", {}).get(section, 3)

# ── Plan an issue ──────────────────────────────────────────────────────────────

def plan_issue():
    coverage_window = input("\nEnter your coverage window (e.g. July/August 2026): ").strip()
    section = input(f"Which section are you planning? {get_sections()}: ").strip().lower()

    default_slots = get_default_slots(section)
    slots_input = input(f"How many slots this issue? (press Enter for {default_slots}): ").strip()
    slots = int(slots_input) if slots_input.isdigit() else default_slots

    unused = [i for i in idea_bank["ideas"] if i["section"] == section and i["status"] == "unused"]
    pitched = [i for i in idea_bank["ideas"] if i["section"] == section and i["status"] == "pitched"]
    held = [i for i in idea_bank["ideas"] if i["section"] == section and i["status"] == "held"]

    def format_ideas(ideas, label):
        if not ideas:
            return ""
        lines = [f"\n{label}:"]
        for i in ideas:
            contributor = f" (pitched by {i['contributor']})" if i.get("contributor") else ""
            lines.append(f"- {i['title']}{contributor}: {i['description']}")
        return "\n".join(lines)

    ideas_summary = (
        format_ideas(unused, "Unused ideas") +
        format_ideas(pitched, "Writer pitches awaiting decision") +
        format_ideas(held, "Held from previous issues")
    )
    if not ideas_summary.strip():
        ideas_summary = "No ideas currently in the bank for this section."

    editorial_values = ", ".join(config["editorial_values"])

    system_prompt = f"""You are Redaktion, an AI editorial assistant for {config['magazine_name']} — {config['description']}
The magazine is based in {config['location']} and publishes both in print and online.
Your job is to help editors plan issues by drawing on their existing idea bank and suggesting new story ideas.
Every suggestion should be grounded in the magazine's editorial values: {editorial_values}.
You understand the difference between a planning tool and a decision-maker: you suggest, the editor decides.
Be concise, specific, and editorially sharp.
When suggesting new ideas, always format them exactly like this so they can be parsed:
IDEA: <title>
PITCH: <one sentence pitch>
FORMAT: <print / online / both>"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""I am planning the {section} section for {coverage_window}. I have {slots} slot(s) to fill.

Here are the ideas available:
{ideas_summary}

Please suggest a plan for the {slots} slot(s). Prioritise existing ideas and pitched stories where they are strong enough. Propose new ideas only if needed to fill remaining slots. For each new idea use the IDEA/PITCH/FORMAT format. Note print/online/both for all ideas."""
            }
        ]
    )

    response_text = message.content[0].text
    print("\n--- Redaktion suggests ---\n")
    print(response_text)

    lines = response_text.split("\n")
    new_ideas = []
    current_idea = {}

    for line in lines:
        line = line.strip()
        if line.startswith("IDEA:"):
            if current_idea:
                new_ideas.append(current_idea)
            current_idea = {"title": line[5:].strip()}
        elif line.startswith("PITCH:") and current_idea:
            current_idea["description"] = line[6:].strip()
        elif line.startswith("FORMAT:") and current_idea:
            current_idea["format"] = line[7:].strip().lower()

    if current_idea:
        new_ideas.append(current_idea)

    if new_ideas:
        print("\n--- Save new ideas to the idea bank? ---\n")
        sections = get_sections()

        for idea in new_ideas:
            print(f"Title:  {idea.get('title', 'Untitled')}")
            print(f"Pitch:  {idea.get('description', '')}")
            print(f"Format: {idea.get('format', '')}")
            save = input("Save this idea? (yes/no): ").strip().lower()

            if save == "yes":
                print(f"Which section? {sections} (press Enter for '{section}'): ", end="")
                chosen_section = input().strip().lower()
                if chosen_section not in sections:
                    chosen_section = section

                idea_bank["ideas"].append({
                    "id": next_id(),
                    "title": idea.get("title", "Untitled"),
                    "description": idea.get("description", ""),
                    "section": chosen_section,
                    "status": "unused",
                    "times_suggested": 1,
                    "format": idea.get("format", None),
                    "ran_in_issue": None,
                    "published_url": None,
                    "contributor": None
                })
                print(f"✓ Saved to {chosen_section} section.\n")
            else:
                print("Skipped.\n")

        save_idea_bank()
        print("Idea bank updated.\n")

# ── Log a pitch ────────────────────────────────────────────────────────────────

def log_pitch():
    print("\n--- Log a writer pitch ---\n")
    sections = get_sections()

    title = input("Story title or working title: ").strip()
    description = input("Brief description of the pitch: ").strip()
    contributor = input("Contributor name: ").strip()

    print(f"Which section? {sections}: ", end="")
    section = input().strip().lower()
    if section not in sections:
        print(f"Section not recognised, defaulting to '{sections[0]}'.")
        section = sections[0]

    format_input = input("Proposed format? (print / online / both / unknown): ").strip().lower()
    if format_input not in ["print", "online", "both"]:
        format_input = None

    idea_bank["ideas"].append({
        "id": next_id(),
        "title": title,
        "description": description,
        "section": section,
        "status": "pitched",
        "times_suggested": 0,
        "format": format_input,
        "ran_in_issue": None,
        "published_url": None,
        "contributor": contributor
    })

    save_idea_bank()
    print(f"\n✓ Pitch by {contributor} logged to {section} section.\n")

# ── Close an issue ─────────────────────────────────────────────────────────────

def close_issue():
    print("\n--- Close an issue ---\n")
    sections = get_sections()

    issue = input("Which issue are you closing? (e.g. August 2026): ").strip()
    section = input(f"Which section? {sections}: ").strip().lower()
    if section not in sections:
        print(f"Section not recognised, defaulting to '{sections[0]}'.")
        section = sections[0]

    candidates = [
        i for i in idea_bank["ideas"]
        if i["section"] == section and i["status"] in ("unused", "pitched", "in_development", "held")
    ]

    if not candidates:
        print("No active ideas found for this section.\n")
        return

    print(f"\nActive ideas in the {section} section — what happened to each?\n")
    print("Options: published / held / rejected / skip\n")

    for idea in candidates:
        contributor = f" (pitched by {idea['contributor']})" if idea.get("contributor") else ""
        print(f"► {idea['title']}{contributor}")
        action = input("  Action (published / held / rejected / skip): ").strip().lower()

        if action == "published":
            idea["status"] = "published"
            idea["ran_in_issue"] = issue
            url = input("  Published URL (press Enter if print-only): ").strip()
            if url:
                idea["published_url"] = url
                if not idea.get("format"):
                    idea["format"] = "online"
            else:
                if not idea.get("format"):
                    idea["format"] = "print"
            print(f"  ✓ Marked as published in {issue}.\n")

        elif action == "held":
            idea["status"] = "held"
            print("  ✓ Held for a future issue.\n")

        elif action == "rejected":
            idea["status"] = "rejected"
            print("  ✓ Marked as rejected.\n")

        elif action == "skip":
            print("  Unchanged.\n")

        else:
            print("  Not recognised — skipped.\n")

    save_idea_bank()
    print(f"Issue {issue} closed. Idea bank updated.\n")

# ── View idea bank ─────────────────────────────────────────────────────────────

def view_idea_bank():
    print("\n--- Idea Bank ---\n")

    sections = get_sections()
    statuses = ["unused", "pitched", "in_development", "held", "published", "rejected"]

    for section in sections:
        section_ideas = [i for i in idea_bank["ideas"] if i["section"] == section]
        if not section_ideas:
            continue

        print(f"{'═' * 50}")
        print(f"  {section.upper()}")
        print(f"{'═' * 50}")

        for status in statuses:
            group = [i for i in section_ideas if i["status"] == status]
            if not group:
                continue

            print(f"\n  [{status.upper()}]")
            for idea in group:
                contributor = f" — pitched by {idea['contributor']}" if idea.get("contributor") else ""
                ran = f" — ran in {idea['ran_in_issue']}" if idea.get("ran_in_issue") else ""
                fmt = f" [{idea['format']}]" if idea.get("format") else ""
                print(f"    • {idea['title']}{fmt}{contributor}{ran}")
                print(f"      {idea['description']}")

        print()

    input("Press Enter to return to the menu.")

# ── Main menu ──────────────────────────────────────────────────────────────────

def main():
    print(f"\nWelcome to Redaktion — editorial assistant for {config['magazine_name']}")

    while True:
        print("\nWhat would you like to do?")
        print("  1. Plan an issue")
        print("  2. Log a writer pitch")
        print("  3. Close an issue")
        print("  4. View idea bank")
        print("  5. Quit")

        choice = input("\nEnter 1, 2, 3, 4, or 5: ").strip()

        if choice == "1":
            plan_issue()
        elif choice == "2":
            log_pitch()
        elif choice == "3":
            close_issue()
        elif choice == "4":
            view_idea_bank()
        elif choice == "5":
            print("\nGoodbye.\n")
            break
        else:
            print("Please enter 1, 2, 3, 4, or 5.")

main()