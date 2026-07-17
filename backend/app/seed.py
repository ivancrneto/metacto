"""Load demo data: run with `invoke seed` (or `python -m app.seed`).

Idempotent — does nothing if feature requests already exist.
"""

import asyncio

from sqlalchemy import func, select

from .db import SessionLocal
from .models import FeatureRequest, User, Vote

USERS = ["ada", "linus", "grace", "alan", "margaret"]

# (title, description, author, [voters]) — voters never include the author.
REQUESTS = [
    (
        "Dark mode",
        "A dark theme would be easier on the eyes for late-night work.",
        "ada",
        ["linus", "grace", "alan", "margaret"],
    ),
    (
        "CSV export",
        "Let me export the feature list and vote counts to CSV.",
        "linus",
        ["ada", "grace"],
    ),
    (
        "Slack notifications",
        "Notify a Slack channel when a request crosses a vote threshold.",
        "grace",
        ["ada", "linus", "margaret"],
    ),
    (
        "Mobile app",
        "A native mobile client for voting on the go.",
        "alan",
        ["grace"],
    ),
    (
        "Merge duplicate requests",
        "Admins should be able to merge near-duplicate requests.",
        "margaret",
        ["ada", "linus", "grace", "alan"],
    ),
    (
        "Keyboard shortcuts",
        "Power users want j/k to move and 'v' to vote.",
        "ada",
        [],
    ),
]


async def seed() -> None:
    async with SessionLocal() as session:
        already = await session.scalar(select(func.count()).select_from(FeatureRequest))
        if already:
            print(f"Skipping seed — {already} feature requests already exist.")
            return

        users = {name: User(username=name) for name in USERS}
        session.add_all(users.values())
        await session.flush()  # assign user ids

        for title, description, author, voters in REQUESTS:
            request = FeatureRequest(
                title=title,
                description=description,
                author_id=users[author].id,
                vote_count=len(voters),
            )
            session.add(request)
            await session.flush()  # assign request id
            session.add_all(
                Vote(user_id=users[voter].id, request_id=request.id) for voter in voters
            )

        await session.commit()
        print(f"Seeded {len(USERS)} users and {len(REQUESTS)} feature requests.")


if __name__ == "__main__":
    asyncio.run(seed())
